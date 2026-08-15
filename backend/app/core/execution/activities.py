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
        variables=execution.variables or {},
        node_outputs={},
        current_node_id=None,
        started_at=execution.started_at or datetime.now(timezone.utc).isoformat(),
        metadata=execution.metadata or {},
        permissions=(execution.metadata or {}).get("permissions", [])
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
    if activity.is_cancelled():
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

    # Publish node started event to canonical pipeline
    from app.core.events.event_bus import ExecutionEventBus
    from app.core.execution.events import ExecutionEvent
    await ExecutionEventBus.publish(
        ExecutionEvent(
            execution_id=context.execution_id,
            workflow_id=context.workflow_definition_id,
            tenant_id=context.tenant_id,
            event_type="NodeStarted",
            node_id=node_id,
            payload={"input": node_def}
        )
    )

    from app.core.security.context import SecurityContext, SecurityContextHolder, SecurityException
    if not context.tenant_id:
        raise SecurityException("Access Denied: Missing organization identity in worker task (Fail Closed).")
        
    meta = context.metadata or {}
    ctx = SecurityContext(
        organization_id=context.tenant_id,
        workspace_id=meta.get("workspace_id", "default"),
        environment_id=meta.get("environment_id", "default"),
        project_id=meta.get("project_id", "default"),
        user_id=meta.get("user_id", "system"),
        permissions=context.permissions
    )
    SecurityContextHolder.set_context(ctx)

    try:
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

            # Publish node completed event to canonical pipeline
            from app.core.events.event_bus import ExecutionEventBus
            from app.core.execution.events import ExecutionEvent
            await ExecutionEventBus.publish(
                ExecutionEvent(
                    execution_id=context.execution_id,
                    workflow_id=context.workflow_definition_id,
                    tenant_id=context.tenant_id,
                    correlation_id=context.correlation_id,
                    event_type="NodeCompleted",
                    node_id=node_id,
                    payload={"duration": duration}
                )
            )

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

            # Publish node failed event to canonical pipeline
            from app.core.events.event_bus import ExecutionEventBus
            from app.core.execution.events import ExecutionEvent
            await ExecutionEventBus.publish(
                ExecutionEvent(
                    execution_id=context.execution_id,
                    workflow_id=context.workflow_definition_id,
                    tenant_id=context.tenant_id,
                    event_type="NodeFailed",
                    node_id=node_id,
                    payload={"error": str(e), "duration": duration}
                )
            )

            raise e
    finally:
        SecurityContextHolder.clear_context()


@activity.defn(name="resolve_loop_items_activity")
async def resolve_loop_items_activity(input_data: Dict[str, Any]) -> list:
    """
    Extracts the loop iteration list from context variables safely.
    """
    node_def = input_data["node_def"]
    context_dict = input_data["context"]
    context = ExecutionContext(**context_dict)
    
    items_var = node_def.get("items_var", "rows")
    items = context.variables.get(items_var, [])
    if not isinstance(items, list):
        return []
    return list(items)


@activity.defn(name="plan_activity")
async def plan_activity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the LLM planner inside an activity boundary.
    """
    from app.core.agents.planner import SequentialPlanner, ReActPlanner, PlanAndSolvePlanner, TreeOfThoughtPlanner
    from app.core.agents.governance import ModelRouter
    from app.core.agents.kernel import Plan, PlanningPolicy
    from app.core.agents.context import AgentContext
    from app.core.agents.memory import MemoryLayer, LocalInMemoryMemory
    
    goal = input_data["goal"]
    context_dict = input_data["context"]
    policy_dict = input_data.get("policy", {})
    plan_dict = input_data.get("plan", {})
    planner_type = input_data.get("planner_type", "react")
    
    agent_context = AgentContext(**context_dict)
    policy = PlanningPolicy(**policy_dict)
    plan = Plan(**plan_dict)
    
    # Setup temporary mock router & memory layer for planning step
    # Setup actual router with credentials matching context
    target_model = context_dict.get("default_model") or "google/gemini-2.5-flash"
    router = ModelRouter(default_model=target_model)
    
    # Try to extract the API Key from settings or Vault for the router
    from app.core.security.secrets import VaultSecretProvider, SecretRef
    provider = VaultSecretProvider()
    for default_path in ["openr-router", "openrouter", "openrouter_api_key"]:
        try:
            ref = SecretRef(provider="vault", path=default_path, version="1")
            api_key = await provider.get(ref)
            if api_key:
                router.openrouter_api_key = api_key
                break
        except Exception:
            pass

    if planner_type == "sequential":
        planner = SequentialPlanner(model_router=router)
    elif planner_type == "plan_and_solve":
        planner = PlanAndSolvePlanner(model_router=router)
    elif planner_type == "tree_of_thought":
        planner = TreeOfThoughtPlanner(model_router=router)
    else:
        planner = ReActPlanner(model_router=router)
        
    memory_layer = MemoryLayer(semantic_provider=LocalInMemoryMemory())
    for obs in input_data.get("observations", []):
        await memory_layer.working_memory.add_observation(obs)
        
    result_plan = await planner.plan(
        goal=goal,
        context=agent_context,
        memory_layer=memory_layer,
        policy=policy,
        current_plan=plan
    )
    return result_plan.model_dump()


@activity.defn(name="execute_tool_activity")
async def execute_tool_activity(input_data: Dict[str, Any]) -> Any:
    """
    Executes the capability negotiation and tool run inside a sandboxed activity.
    """
    from app.core.agents.tools import ToolExecutor
    from app.core.agents.context import AgentContext
    
    tool_name = input_data["tool_name"]
    args = input_data["args"]
    context_dict = input_data["context"]
    
    agent_context = AgentContext(**context_dict)
    executor = ToolExecutor()
    return await executor.execute_tool(
        tool_name=tool_name,
        args=args,
        context=agent_context
    )


@activity.defn(name="complete_execution_activity")
async def complete_execution_activity(input_data: Dict[str, Any]) -> None:
    """
    Updates the parent execution document status in MongoDB.
    """
    await factory.ensure_db_connected()
    
    execution_id = input_data["execution_id"]
    status_str = input_data["status"]
    error_msg = input_data.get("error")
    
    execution = await Execution.get(ObjectId(execution_id))
    if execution:
        execution.status = ExecutionStatus.COMPLETED if status_str == "completed" else ExecutionStatus.FAILED
        if error_msg:
            execution.error = error_msg
        execution.finished_at = datetime.now(timezone.utc).isoformat()
        await execution.save()
        
        # Publish final execution state changes
        from app.core.events.event_bus import ExecutionEventBus
        from app.core.execution.events import ExecutionEvent
        await ExecutionEventBus.publish(
            ExecutionEvent(
                execution_id=execution_id,
                workflow_id=execution.workflow_id,
                tenant_id=execution.organization_id,
                event_type="ExecutionCompleted" if status_str == "completed" else "ExecutionFailed",
                payload={"status": execution.status.value, "error": error_msg}
            )
        )

