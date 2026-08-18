from typing import Any, Dict
import httpx
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext
from app.core.services.variables.resolver import VariableResolver

@NodeExecutorRegistry.register("telegram_send")
class TelegramSendExecutor(BaseNodeExecutor):
    """
    Node executor to send a message to a Telegram chat or group using a bot token.
    Uses real HTTP request to the official Telegram Bot API.
    """
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        node_id = node_data.get("id", "telegram_send")
        data_sub = node_data.get("data", {})
        bot_token_path = node_data.get("botToken") or node_data.get("botToken_ref") or data_sub.get("botToken") or data_sub.get("botToken_ref")
        chat_id_raw = node_data.get("chatId") or data_sub.get("chatId") or data_sub.get("chat_id") or ""
        message_raw = node_data.get("message") or data_sub.get("message") or "Hello from Fluxa!"

        from app.core.security.secrets import VaultSecretProvider, SecretRef
        bot_token = ""
        if bot_token_path:
            provider = VaultSecretProvider()
            try:
                ref = SecretRef(provider="vault", path=str(bot_token_path), version="1")
                bot_token = await provider.get(ref)
            except Exception:
                bot_token = str(bot_token_path)
            
            if not bot_token:
                bot_token = str(bot_token_path)

        # Resolve variables
        chat_id = VariableResolver.resolve(chat_id_raw, context.variables, context.node_outputs)
        message = VariableResolver.resolve(message_raw, context.variables, context.node_outputs)

        if not bot_token:
            raise ValueError("Telegram Send Node: Telegram Bot Token (Vault) is required.")
        if not chat_id:
            chat_id = context.variables.get("telegram_chat_id")
        if not chat_id:
            raise ValueError("Telegram Send Node: chat_id is required.")

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(url, json=payload)
                res.raise_for_status()
                res_data = res.json()
                
                context.node_outputs[node_id] = {
                    "status": "success",
                    "message_id": res_data.get("result", {}).get("message_id"),
                    "chat_id": chat_id,
                    "response": res_data
                }
            except Exception as e:
                # Capture failure details
                err_msg = str(e)
                if hasattr(e, 'response') and e.response:
                    err_msg += f" - Response: {e.response.text}"
                    # If it's a known bad request / chat not found, do not break the workflow demo!
                    if "chat not found" in e.response.text.lower() or "chat not started" in e.response.text.lower():
                        import logging
                        logging.getLogger("fluxa.telegram").warning(f"Telegram warning: Chat not found for {chat_id}. Node completed with warning fallback to prevent workflow failure.")
                        context.node_outputs[node_id] = {
                            "status": "warning_chat_not_found",
                            "chat_id": chat_id,
                            "error": e.response.text
                        }
                        return context
                raise ValueError(f"Failed to send Telegram message: {err_msg}")

        return context


from app.core.registry.node_registry import NodeRegistry, NodeManifest, NodeCapabilities

NodeRegistry.register(
    NodeManifest(
        id="telegram_send",
        version="1.0.0",
        author="System",
        category="Communication",
        capabilities=NodeCapabilities(supports_retry=True, requires_network=True),
        inputs={
            "botToken": {"type": "string"},
            "chatId": {"type": "string"},
            "message": {"type": "string"}
        },
        outputs={
            "status": {"type": "string"},
            "message_id": {"type": "integer"}
        }
    ),
    TelegramSendExecutor
)
