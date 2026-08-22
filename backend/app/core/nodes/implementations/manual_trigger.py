from typing import Dict, Any
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext

from typing import Dict, Any
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext

@NodeExecutorRegistry.register("manual_trigger")
class ManualTriggerNodeExecutor(BaseNodeExecutor):
    """
    Entry point trigger node. Graph traversal starts here.
    Passes execution context directly to the next node.
    """
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        node_id = node_data.get("id", "manual_trigger")
        started_at = context.started_at
        if started_at and not isinstance(started_at, str):
            try:
                started_at = started_at.isoformat()
            except Exception:
                started_at = str(started_at)
        
        # Initialize trigger output
        context.node_outputs[node_id] = {
            "status": "triggered",
            "triggered_at": started_at
        }
        return context
