import asyncio
import logging
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from temporalio import activity
from app.core.execution.workflows import WorkflowOrchestrator
from app.core.execution.context import ExecutionContext
from app.core.execution.activities import load_execution_context_activity, execute_node_activity
from unittest.mock import AsyncMock, patch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_temporal")

# Mock database calls for testing without a running MongoDB
@activity.defn(name="load_execution_context_activity")
async def mock_load_execution_context_activity(input_data: dict) -> dict:
    logger.info(f"[Mock Activity] Loading context for execution {input_data['execution_id']}")
    context = ExecutionContext(
        execution_id=input_data["execution_id"],
        workflow_definition_id=input_data["workflow_definition_id"],
        workflow_definition_version=1,
        tenant_id=input_data["tenant_id"],
        variables={},
        node_outputs={},
        current_node_id=None
    )
    return context.model_dump()

@activity.defn(name="execute_node_activity")
async def mock_execute_node_activity(input_data: dict) -> dict:
    node_def = input_data["node_def"]
    context_dict = input_data["context"]
    context = ExecutionContext(**context_dict)
    
    node_id = node_def.get("id", "unknown")
    node_type = node_def.get("type", "unknown")
    logger.info(f"[Mock Activity] Executing node {node_id} (type: {node_type})")
    
    # Simulate variable set
    if node_type == "set_variable":
        var_name = node_def.get("variable_name")
        var_value = node_def.get("variable_value")
        if var_name:
            context.set_variable(var_name, var_value)
            context.set_node_output(node_id, {"status": "success", "value": var_value})
            
    return context.model_dump()

async def run_test():
    logger.info("Starting Temporal Test Environment (this downloads/starts an ephemeral Temporal server)...")
    
    # Start the local test server
    async with await WorkflowEnvironment.start_local() as env:
        # Start a worker registering WorkflowOrchestrator and our mock activities
        worker = Worker(
            env.client,
            task_queue="fluxa-core",
            workflows=[WorkflowOrchestrator],
            activities=[mock_load_execution_context_activity, mock_execute_node_activity],
            activity_executor=None
        )
        
        async with worker:
            logger.info("Worker started successfully. Running test workflow run...")
            
            # Input data representing our Workflow
            test_workflow_input = {
                "execution_id": "test-execution-123",
                "workflow_definition_id": "test-workflow-def",
                "tenant_id": "org-test-456",
                "nodes": [
                    {
                        "id": "node-1",
                        "name": "Set Test Var",
                        "type": "set_variable",
                        "variable_name": "welcome_message",
                        "variable_value": "Hello from Temporal Workflow Orchestration!"
                    }
                ]
            }
            
            # Run the workflow Orchestrator
            result = await env.client.execute_workflow(
                WorkflowOrchestrator.run,
                test_workflow_input,
                id="test-execution-123",
                task_queue="fluxa-core"
            )
            
            logger.info("Workflow execution completed!")
            logger.info(f"Final Execution State Output: {result}")
            
            # Verify the variable was set correctly in the context
            variables = result.get("variables", {})
            assert variables.get("welcome_message") == "Hello from Temporal Workflow Orchestration!"
            logger.info("SUCCESS: Temporal Workflow Orchestrator ran and executed the mock nodes correctly!")

if __name__ == "__main__":
    asyncio.run(run_test())
