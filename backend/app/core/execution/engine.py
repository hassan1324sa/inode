import logging
from typing import Dict, Any
from app.core.execution.context import ExecutionContext
from app.core.nodes.node_executor import NodeExecutorRegistry
import json

# Force registration of node executors
import app.core.nodes.implementations  # noqa: F401

logger = logging.getLogger("fluxa.execution_engine")

class ExecutionEngine:
    """
    A stateless engine to route and execute workflow nodes.
    """

    async def execute_node(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        node_id = node_data.get("id", "unknown")
        node_type = node_data.get("type", "unknown")
        
        # Structured Logging with Correlation IDs
        log_extra = {
            "execution_id": context.execution_id,
            "workflow_definition_id": context.workflow_definition_id,
            "workflow_definition_version": context.workflow_definition_version,
            "tenant_id": context.tenant_id,
            "node_id": node_id,
            "node_type": node_type
        }
        
        logger.info(
            f"Executing node: {node_id} of type: {node_type}",
            extra={"structured_log": log_extra}
        )

        executor = NodeExecutorRegistry.get_executor(node_type)
        if not executor:
            err_msg = f"No executor registered for node type: {node_type}"
            logger.error(err_msg, extra={"structured_log": log_extra})
            raise ValueError(err_msg)

        try:
            context.current_node_id = node_id
            context = await executor.execute(node_data, context)
            
            logger.info(
                f"Successfully completed node: {node_id}",
                extra={"structured_log": {**log_extra, "status": "completed"}}
            )
            return context
            
        except Exception as e:
            logger.error(
                f"Failed to execute node {node_id}: {str(e)}",
                exc_info=True,
                extra={"structured_log": {**log_extra, "status": "failed", "error": str(e)}}
            )
            raise e
