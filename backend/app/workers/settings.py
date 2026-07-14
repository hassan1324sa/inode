import asyncio
from datetime import datetime
from bson import ObjectId
from arq.connections import RedisSettings
from app.core.settings import settings
from app.core.database import db_manager
from app.models.execution import Execution
from app.models.node_execution import NodeExecution
from app.core.nodes.base import NodeContext
from app.core.nodes.factory import NodeFactory

# We will need the node registry to be loaded
import app.core.nodes.implementations

from app.models.workflow_version import WorkflowVersion
from app.models.enums import ExecutionStatus

async def run_workflow(ctx, execution_id: str):
    """
    ARQ task to run a workflow execution.
    """
    print(f"Starting execution: {execution_id}")
    
    # Fetch execution from DB
    execution = await Execution.get(ObjectId(execution_id))
    if not execution:
        print(f"Execution {execution_id} not found.")
        return
        
    execution.status = ExecutionStatus.RUNNING
    await execution.save()
    
    context = NodeContext(
        execution_id=execution_id,
        workflow_id=execution.workflow_id
    )
    
    # Fetch WorkflowVersion
    # Wait, the workflow_version_id could be a version string like 'v1' or an ObjectId.
    # The models in api endpoint used MOCK_DB["workflows"][wf_id]["current_version"] which is "v1" or "v2".
    # For a real DB, it should be fetching by workflow_id and version string, or direct ObjectId.
    # Since endpoints.py sets it to string like "v1", let's query by workflow_id and version.
    workflow_version = await WorkflowVersion.find_one(
        WorkflowVersion.workflow_id == execution.workflow_id,
        WorkflowVersion.version == execution.workflow_version_id
    )
    
    nodes = []
    if workflow_version and workflow_version.nodes:
        nodes = workflow_version.nodes
    else:
        print(f"WorkflowVersion {execution.workflow_version_id} not found or has no nodes. Falling back to default node.")
        nodes = [{
            "id": "node-1",
            "name": "Set Test Var",
            "type": "set_variable",
            "variable_name": "test_var",
            "variable_value": 42
        }]
    
    for node_data in nodes:
        context.current_node_id = node_data.get("id", "unknown")
        start_time = datetime.utcnow()
        node_status = ExecutionStatus.COMPLETED
        node_error = None
        
        try:
            node = NodeFactory.create_node(node_data)
            context = await node.execute(context)
            print(f"Node context after execution: {context.variables}")
        except Exception as e:
            print(f"Error executing node: {e}")
            node_status = ExecutionStatus.FAILED
            node_error = str(e)
            context.errors.append(node_error)
            execution.status = ExecutionStatus.FAILED
            
        # Record node execution
        node_exec = NodeExecution(
            execution_id=execution_id,
            node_id=context.current_node_id,
            status=node_status,
            started_at=start_time.isoformat(),
            finished_at=datetime.utcnow().isoformat(),
            duration=(datetime.utcnow() - start_time).total_seconds(),
            input=node_data,
            output={"variables": context.variables},
            error=node_error,
            logs=[f"Node executed with status {node_status}"]
        )
        await node_exec.insert()
        
        if execution.status == ExecutionStatus.FAILED:
            break
    
    if execution.status != ExecutionStatus.FAILED:
        execution.status = ExecutionStatus.COMPLETED
        
    execution.finished_at = datetime.utcnow().isoformat()
    # Simple duration calc
    if execution.started_at:
        started = datetime.fromisoformat(execution.started_at)
        execution.duration = (datetime.utcnow() - started).total_seconds()
    await execution.save()
    print(f"Execution {execution_id} finished with status {execution.status}")

async def startup(ctx):
    print("Worker starting up... connecting to DB")
    await db_manager.connect_db(document_models=[])

async def shutdown(ctx):
    print("Worker shutting down... closing DB")
    await db_manager.close_db()

class WorkerSettings:
    functions = [run_workflow]
    redis_settings = RedisSettings.from_dsn(settings.db.redis_url)
    on_startup = startup
    on_shutdown = shutdown
