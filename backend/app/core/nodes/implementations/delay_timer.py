import logging
import asyncio
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext

logger = logging.getLogger("fluxa.delay_timer")

@NodeExecutorRegistry.register("delay_timer")
class DelayTimerExecutor(BaseNodeExecutor):
    """
    Pauses workflow execution for a specified duration.
    """
    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        node_id = context.current_node
        node_config = context.workflow.get_node(node_id)
        if not node_config:
            raise ValueError(f"Node {node_id} not found in workflow")

        data = node_config.data
        try:
            duration_seconds = float(data.get("durationSeconds", 0))
        except ValueError:
            raise ValueError("durationSeconds must be a valid number.")

        if duration_seconds < 0:
            raise ValueError("durationSeconds cannot be negative.")

        logger.info(f"Delaying execution for {duration_seconds} seconds...")
        await asyncio.sleep(duration_seconds)

        context.node_outputs[node_id] = {
            "status": "success",
            "delayed_seconds": duration_seconds
        }
        return context
