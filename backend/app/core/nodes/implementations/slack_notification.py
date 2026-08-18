import logging
import httpx
from typing import Dict, Any
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext

logger = logging.getLogger("fluxa.slack_notification")

@NodeExecutorRegistry.register("slack_notification")
class SlackNotificationExecutor(BaseNodeExecutor):
    """
    Sends a message to a Slack channel using a webhook URL.
    """
    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        node_id = context.current_node
        node_config = context.workflow.get_node(node_id)
        if not node_config:
            raise ValueError(f"Node {node_id} not found in workflow")

        data = node_config.data
        channel = data.get("channel", "")
        message = data.get("message", "")

        # Optional: they might use webhook URL via credentials
        # We will assume there is a webhook_url in variables for simplicity or they provide it.
        webhook_url = context.variables.get("slack_webhook_url")
        if not webhook_url:
            raise ValueError("slack_webhook_url is missing from execution context/variables.")

        if not message:
            raise ValueError("Message body is required for Slack notification.")

        payload = {
            "text": message
        }
        if channel:
            payload["channel"] = channel

        logger.info(f"Sending Slack notification to {channel}")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
                
            context.node_outputs[node_id] = {
                "status": "success",
                "delivered": True,
                "channel": channel
            }
        except httpx.HTTPError as e:
            logger.error(f"Slack API error: {e}")
            raise RuntimeError(f"Failed to send Slack notification: {e}")

        return context
