import logging
from app.core.execution.temporal_client import TemporalClientWrapper
from app.core.execution.workflows import WorkflowOrchestrator
from typing import List, Dict, Any

logger = logging.getLogger("fluxa.execution_service")

class ExecutionService:
    """
    Service layer to abstract Temporal workflow orchestrations.
    """

    def __init__(self):
        self.client_wrapper = TemporalClientWrapper()

    async def start_execution(
        self,
        execution_id: str,
        workflow_definition_id: str,
        tenant_id: str,
        nodes: List[Dict[str, Any]]
    ) -> str:
        client = await self.client_wrapper.get_client()
        
        # Prepare inputs
        input_data = {
            "execution_id": execution_id,
            "workflow_definition_id": workflow_definition_id,
            "tenant_id": tenant_id,
            "nodes": nodes
        }
        
        # Search Attributes can be set if defined in Temporal cluster.
        # For MVP, we will start the workflow under execution_id as temporal_workflow_id.
        logger.info(f"Triggering Temporal workflow for execution: {execution_id}")
        handle = await client.start_workflow(
            WorkflowOrchestrator.run,
            input_data,
            id=execution_id,
            task_queue="fluxa-core"
        )
        return handle.run_id

    async def pause_execution(self, execution_id: str):
        client = await self.client_wrapper.get_client()
        logger.info(f"Sending pause signal to execution: {execution_id}")
        handle = client.get_workflow_handle(execution_id)
        await handle.signal(WorkflowOrchestrator.pause_workflow)

    async def resume_execution(self, execution_id: str):
        client = await self.client_wrapper.get_client()
        logger.info(f"Sending resume signal to execution: {execution_id}")
        handle = client.get_workflow_handle(execution_id)
        await handle.signal(WorkflowOrchestrator.resume_workflow)

    async def cancel_execution(self, execution_id: str):
        client = await self.client_wrapper.get_client()
        logger.info(f"Cancelling execution: {execution_id}")
        handle = client.get_workflow_handle(execution_id)
        await handle.cancel()

    async def terminate_execution(self, execution_id: str, reason: str = "Terminated by user"):
        client = await self.client_wrapper.get_client()
        logger.info(f"Terminating execution: {execution_id} due to: {reason}")
        handle = client.get_workflow_handle(execution_id)
        await handle.terminate(reason=reason)
