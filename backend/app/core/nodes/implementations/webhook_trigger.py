from typing import Dict, Any
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext

@NodeExecutorRegistry.register("webhook_trigger")
class WebhookTriggerNodeExecutor(BaseNodeExecutor):
    """
    Generic webhook trigger node. Graph traversal starts here when a webhook is received.
    """
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        node_id = node_data.get("id", "webhook_trigger")
        
        # In a real execution, the webhook endpoint injects webhook_payload and webhook_headers
        context.node_outputs[node_id] = {
            "status": "triggered",
            "payload": context.variables.get("webhook_payload", {}),
            "headers": context.variables.get("webhook_headers", {}),
            "query_params": context.variables.get("webhook_query", {})
        }
        return context
