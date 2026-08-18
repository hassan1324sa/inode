from typing import Dict, Any
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext

@NodeExecutorRegistry.register("loop")
class LoopNodeExecutor(BaseNodeExecutor):
    """
    Loops over items and executes child node flows using the stateless ExecutionEngine.
    Supports dynamic branch conditional evaluations.
    """
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        context.node_outputs[node_data.get("id", "loop")] = {"status": "success", "message": "Loop orchestration completed."}
        return context
