import smtplib
import logging
import hashlib
import json
from email.mime.text import MIMEText
from typing import Dict, Any
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext
from app.core.security.secrets import VaultSecretProvider, SecretRef
from app.core.execution.durable_store import MongoDBEventStore, ExecutionEffect

logger = logging.getLogger("fluxa.send_email_node")

@NodeExecutorRegistry.register("send-email")
class SendEmailNodeExecutor(BaseNodeExecutor):
    """
    Sends email via SMTP. Integrates with VaultSecretProvider for password credentials
    and supports deterministic replay caching via ExecutionEffect.
    """
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        from app.core.services.variables.resolver import VariableResolver

        # Check for Replay & Effect Cache
        execution_id = context.execution_id
        is_replay = execution_id and str(execution_id).startswith("replay-")
        
        smtp_host = node_data.get("smtp_host", "localhost")
        smtp_port = int(node_data.get("smtp_port", 1025))
        username = node_data.get("username", "sender@example.com")
        
        recipient_raw = node_data.get("recipient")
        # Resolve recipient dynamically if template-based, e.g. "{{current_row.email}}"
        recipient = VariableResolver.resolve(recipient_raw, context.variables, context.node_outputs)
        
        # Support fallback legacy direct reference
        if (recipient is None or recipient == recipient_raw) and recipient_raw == "current_row.email":
            row = context.variables.get("current_row", {})
            recipient = row.get("email")
            
        subject_raw = node_data.get("subject", "Notification")
        subject = VariableResolver.resolve(subject_raw, context.variables, context.node_outputs)
        
        body_raw = node_data.get("body", "")
        # Resolve templates like "Hello {{current_row.name}}" or legacy format
        body = VariableResolver.resolve(body_raw, context.variables, context.node_outputs)
        
        # Backward compatibility support for legacy curly braces "{current_row.name}"
        if "{current_row.name}" in body:
            row = context.variables.get("current_row", {})
            body = body.replace("{current_row.name}", row.get("name", "Customer"))
        if "{current_row.last_order}" in body:
            row = context.variables.get("current_row", {})
            body = body.replace("{current_row.last_order}", row.get("last_order", ""))

            
        # Calculate request hash for replay determinism
        req_payload = {"recipient": recipient, "subject": subject, "body": body}
        arg_str = json.dumps(req_payload, sort_keys=True)
        request_hash = hashlib.sha256((f"send_email_{recipient}_{subject}" + arg_str).encode("utf-8")).hexdigest()
        
        # 1. Deterministic Replay & Retry check
        node_id = node_data.get("id", "send-email")
        if execution_id:
            lookup_id = str(execution_id).replace("replay-", "")
            effect = await MongoDBEventStore.get_effect(lookup_id, "send-email", request_hash)
            if effect:
                logger.info(f"Matching effect found for SendEmail (Deduplicated retry/replay). Skipping real SMTP connection.")
                context.node_outputs[node_id] = effect.response
                return context
                
        # 2. Resolve Secret Reference for Password dynamically (Fail-Closed Context)
        password = ""
        password_ref_dict = node_data.get("password_ref")
        if password_ref_dict:
            provider = VaultSecretProvider()
            ref = SecretRef(**password_ref_dict)
            password = await provider.get(ref)
            
        # 3. Construct Email Message
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = username
        msg['To'] = recipient
        
        # 4. Perform Actual SMTP Action
        try:
            # Connect to SMTP server (e.g. Mailpit)
            s = smtplib.SMTP(smtp_host, smtp_port, timeout=5)
            if password:
                s.login(username, password)
            s.sendmail(username, [recipient], msg.as_string())
            s.quit()
            logger.info(f"Email sent successfully to {recipient}")
            
            output = {"status": "success", "recipient": recipient}
            context.node_outputs[node_data.get("id", "send-email")] = output
            
            # Save effect for Replay contract
            if execution_id:
                effect = ExecutionEffect(
                    execution_id=str(execution_id),
                    node_id="send-email",
                    effect_type="smtp",
                    provider="smtp_client",
                    request_hash=request_hash,
                    response=output
                )
                await MongoDBEventStore.save_effect(effect)
                
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise e
            
        return context
