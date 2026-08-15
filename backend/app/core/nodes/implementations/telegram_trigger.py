from typing import Dict, Any
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext

@NodeExecutorRegistry.register("telegram_trigger")
class TelegramTriggerNodeExecutor(BaseNodeExecutor):
    """
    Telegram message trigger node. Graph traversal starts here.
    """
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        node_id = node_data.get("id", "telegram_trigger")
        context.node_outputs[node_id] = {
            "status": "triggered",
            "message": context.variables.get("telegram_message", ""),
            "chat_id": context.variables.get("telegram_chat_id", ""),
            "user": context.variables.get("telegram_user", {})
        }
        return context
