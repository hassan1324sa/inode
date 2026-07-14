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
        
    execution.status = "Running"
    await execution.save()
    
    # In a real scenario, we'd fetch the WorkflowVersion from DB and iterate nodes.
    # For Phase 3/4 "First Simple Workflow", we'll simulate running a Set Variable node.
    
    context = NodeContext(
        execution_id=execution_id,
        workflow_id=execution.workflow_id
    )
    
    node_data = {
        "id": "node-1",
        "name": "Set Test Var",
        "type": "set_variable",
        "variable_name": "test_var",
        "variable_value": 42
    }
    
    start_time = datetime.utcnow()
    node_status = "Completed"
    
    try:
        node = NodeFactory.create_node(node_data)
        context = await node.execute(context)
        print(f"Node context after execution: {context.variables}")
    except Exception as e:
        print(f"Error executing node: {e}")
        node_status = "Failed"
        execution.status = "Failed"
    
    # Record node execution
    node_exec = NodeExecution(
        execution_id=execution_id,
        node_id="node-1",
        status=node_status,
        started_at=start_time.isoformat(),
        finished_at=datetime.utcnow().isoformat(),
        inputs=node_data,
        outputs={"variables": context.variables}
    )
    await node_exec.insert()
    
    if execution.status != "Failed":
        execution.status = "Completed"
        
    execution.finished_at = datetime.utcnow().isoformat()
    # Simple duration calc
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
