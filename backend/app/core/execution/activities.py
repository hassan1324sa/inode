from temporalio import activity
from datetime import datetime, timezone
from typing import Dict, Any
from app.core.execution.context import ExecutionContext
from app.core.execution.activity_factory import ActivityFactory
from app.models.execution import Execution
from app.models.node_execution import NodeExecution
from app.models.enums import ExecutionStatus
from app.core.database import db_manager
from bson import ObjectId

factory = ActivityFactory()

@activity.defn(name="load_execution_context_activity")
async def load_execution_context_activity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity to load context from MongoDB execution document.
    """
    await factory.ensure_db_connected()
    
    execution_id = input_data["execution_id"]
    execution = await Execution.get(ObjectId(execution_id))
    if not execution:
        raise ValueError(f"Execution {execution_id} not found")

    # Construct the ExecutionContext
    context = ExecutionContext(
        execution_id=execution_id,
        workflow_definition_id=execution.workflow_id,
        workflow_definition_version=1,  # Default version
        tenant_id=execution.organization_id,
        variables={},
        node_outputs={},
        current_node_id=None,
        started_at=execution.started_at or datetime.now(timezone.utc).isoformat()
    )
    
    return context.model_dump()


@activity.defn(name="execute_node_activity")
async def execute_node_activity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity to execute a single node's logic.
    """
    await factory.ensure_db_connected()
    
    node_def = input_data["node_def"]
    context_dict = input_data["context"]
    context = ExecutionContext(**context_dict)
    
    node_id = node_def.get("id", "unknown")
    
    # Observability - Heartbeating & Cancellation Check
    activity.heartbeat("Starting node execution")
    if activity.info().is_cancelled:
        raise activity.CancelledError("Activity cancelled before start")

    node_start = datetime.now(timezone.utc)
    
    # 1. Log Start Event & Insert Node Execution
    node_exec = NodeExecution(
        execution_id=context.execution_id,
        node_id=node_id,
        status=ExecutionStatus.RUNNING,
        started_at=node_start.isoformat(),
        input=node_def
    )
    await node_exec.insert()

    # Record start event in execution events
    event_log = {
        "execution_id": context.execution_id,
        "event": "node_started",
        "node_id": node_id,
        "timestamp": node_start.isoformat()
    }
    await db_manager.db["execution_events"].insert_one(event_log)

    try:
        # 2. Run Engine Execution
        context = await factory.execute_node(node_def, context)
        
        node_end = datetime.now(timezone.utc)
        duration = (node_end - node_start).total_seconds()
        
        # 3. Checkpoint & Node Complete DB Updates
        node_exec.status = ExecutionStatus.COMPLETED
        node_exec.finished_at = node_end.isoformat()
        node_exec.duration = duration
        node_exec.output = context.node_outputs.get(node_id, {})
        await node_exec.save()

        # Update parent execution state checkpoint
        execution = await Execution.get(ObjectId(context.execution_id))
        if execution:
            execution.status = ExecutionStatus.RUNNING
            # Store variables and outputs
            execution.nodes_snapshot.append({
                "node_id": node_id,
                "status": ExecutionStatus.COMPLETED.value,
                "finished_at": node_end.isoformat()
            })
            await execution.save()

        # Log completion event
        await db_manager.db["execution_events"].insert_one({
            "execution_id": context.execution_id,
            "event": "node_completed",
            "node_id": node_id,
            "duration": duration,
            "timestamp": node_end.isoformat()
        })

        return context.model_dump()

    except Exception as e:
        node_end = datetime.now(timezone.utc)
        duration = (node_end - node_start).total_seconds()
        
        # Checkpoint FAILED status on node and parent execution
        node_exec.status = ExecutionStatus.FAILED
        node_exec.finished_at = node_end.isoformat()
        node_exec.duration = duration
        node_exec.error = str(e)
        await node_exec.save()

        execution = await Execution.get(ObjectId(context.execution_id))
        if execution:
            execution.status = ExecutionStatus.FAILED
            execution.error = str(e)
            await execution.save()

        # Log error event
        await db_manager.db["execution_events"].insert_one({
            "execution_id": context.execution_id,
            "event": "node_failed",
            "node_id": node_id,
            "error": str(e),
            "timestamp": node_end.isoformat()
        })

        raise e
