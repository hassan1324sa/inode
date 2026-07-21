import datetime
from bson import ObjectId
from app.models.execution import Execution
from app.models.workflow_version import WorkflowVersion
from app.models.node_execution import NodeExecution
from app.models.enums import ExecutionStatus
from app.core.nodes.base import NodeContext
from app.core.nodes.factory import NodeFactory
import logging
from typing import Any

logger = logging.getLogger(__name__)

async def run_workflow(execution_id: str, memory_cache: Any):
    logger.info(f"Engine starting execution {execution_id}")
    try:
        exec_oid = ObjectId(execution_id)
    except Exception:
        logger.error(f"Invalid execution_id format: {execution_id}")
        return

    execution = await Execution.get(exec_oid)
    if not execution:
        logger.error(f"Execution {execution_id} not found in DB")
        return

    execution.status = ExecutionStatus.RUNNING
    execution.started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    await execution.save()
    
    await memory_cache.delete(f"execution:{execution_id}")
    await memory_cache.delete(f"workflow_executions:{execution.workflow_id}")

    try:
        wf_version = await WorkflowVersion.find_one(
            WorkflowVersion.workflow_id == execution.workflow_id,
            WorkflowVersion.version == execution.workflow_version_id
        )
        if not wf_version:
            raise ValueError(f"WorkflowVersion not found for {execution.workflow_id} @ {execution.workflow_version_id}")

        context = NodeContext(
            execution_id=execution_id,
            workflow_id=execution.workflow_id,
            current_node_id=None
        )

        # NodeFactory will need the registry to be populated, make sure implementations are imported in main.py or __init__
        import app.core.nodes.implementations  # Ensure implementations are registered

        for node_def in wf_version.nodes:
            node = NodeFactory.create_node(node_def)
            context.current_node_id = node.id
            node_start = datetime.datetime.now(datetime.timezone.utc)
            
            node_exec = NodeExecution(
                execution_id=execution_id,
                node_id=node.id,
                status=ExecutionStatus.RUNNING,
                started_at=node_start.isoformat(),
                input=node_def
            )
            await node_exec.insert()
            
            try:
                context = await node.execute(context)
                node_exec.status = ExecutionStatus.COMPLETED
                node_exec.output = {"variables": context.variables}
            except Exception as e:
                node_exec.status = ExecutionStatus.FAILED
                node_exec.error = str(e)
                context.errors.append(str(e))
                raise e
            finally:
                node_end = datetime.datetime.now(datetime.timezone.utc)
                node_exec.finished_at = node_end.isoformat()
                node_exec.duration = (node_end - node_start).total_seconds()
                await node_exec.save()

        execution.status = ExecutionStatus.COMPLETED
        execution.finished_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if execution.started_at:
            start_dt = datetime.datetime.fromisoformat(execution.started_at)
            execution.duration = (datetime.datetime.now(datetime.timezone.utc) - start_dt).total_seconds()
        await execution.save()

    except Exception as exc:
        logger.error(f"Execution {execution_id} failed: {exc}")
        execution.status = ExecutionStatus.FAILED
        execution.error = str(exc)
        execution.finished_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if execution.started_at:
            start_dt = datetime.datetime.fromisoformat(execution.started_at)
            execution.duration = (datetime.datetime.now(datetime.timezone.utc) - start_dt).total_seconds()
        await execution.save()
    finally:
        await memory_cache.delete(f"execution:{execution_id}")
        await memory_cache.delete(f"workflow_executions:{execution.workflow_id}")
