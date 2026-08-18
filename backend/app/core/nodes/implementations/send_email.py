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

@NodeExecutorRegistry.register("send_email")
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
        
        data_sub = node_data.get("data", {})
        smtp_host = node_data.get("smtp_host") or data_sub.get("smtp_host") or "localhost"
        smtp_port = int(node_data.get("smtp_port") or data_sub.get("smtp_port") or 1025)
        username = node_data.get("username") or data_sub.get("username")
        if not username:
            raise ValueError("Send Email Node: username (sender) is required.")
        
        recipient_raw = node_data.get("recipient") or data_sub.get("recipient")
        # Resolve recipient dynamically if template-based, e.g. "{{current_row.email}}"
        recipient = VariableResolver.resolve(recipient_raw, context.variables, context.node_outputs)
        
        # Support fallback legacy direct reference
        if (recipient is None or recipient == recipient_raw) and recipient_raw == "current_row.email":
            row = context.variables.get("current_row", {})
            recipient = row.get("email")
            
        if not recipient:
            raise ValueError("Send Email Node: recipient is required.")
        subject_raw = node_data.get("subject") or data_sub.get("subject") or "Notification"
        subject = VariableResolver.resolve(subject_raw, context.variables, context.node_outputs)
        
        body_raw = node_data.get("body") or data_sub.get("body") or ""
        # Resolve templates like "Hello {{current_row.name}}" or legacy format
        body = VariableResolver.resolve(body_raw, context.variables, context.node_outputs) or ""
        
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
        password_ref_raw = node_data.get("password_ref") or data_sub.get("password_ref") or node_data.get("password") or data_sub.get("password")
        if password_ref_raw:
            provider = VaultSecretProvider()
            if isinstance(password_ref_raw, dict):
                try:
                    ref = SecretRef(**password_ref_raw)
                    password = await provider.get(ref)
                except Exception:
                    password = ""
            else:
                try:
                    ref = SecretRef(provider="vault", path=str(password_ref_raw), version="1")
                    password = await provider.get(ref)
                except Exception:
                    password = str(password_ref_raw)
                if not password:
                    password = str(password_ref_raw)
            
        # 3. Construct Email Message
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = username
        msg['To'] = recipient
        
        # 4. Perform Actual SMTP Action
        try:
            # Connect to SMTP server (supports SSL on 465, STARTTLS on 587/others)
            if smtp_port == 465:
                s = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
            else:
                s = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                try:
                    s.ehlo()
                    # Explicitly issue STARTTLS for port 587 or if advertised
                    if smtp_port == 587 or s.has_ext("STARTTLS"):
                        s.starttls()
                        s.ehlo()
                except Exception as tls_err:
                    logger.warning(f"Failed to establish STARTTLS connection: {tls_err}")

            if password:
                try:
                    s.login(username, password)
                except smtplib.SMTPNotSupportedError:
                    logger.info("SMTP server does not support EHLO/AUTH extension. Skipping login.")
                except Exception as auth_err:
                    logger.warning(f"SMTP auth failed, attempting to proceed without auth: {auth_err}")
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


from app.core.registry.node_registry import NodeRegistry, NodeManifest, NodeCapabilities

NodeRegistry.register(
    NodeManifest(
        id="send-email",
        version="1.0.0",
        author="System",
        category="Communication",
        capabilities=NodeCapabilities(supports_retry=True, requires_network=True),
        inputs={
            "smtp_host": {"type": "string"},
            "smtp_port": {"type": "integer"},
            "username": {"type": "string"},
            "recipient": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "password_ref": {"type": "object"}
        },
        outputs={
            "status": {"type": "string"},
            "recipient": {"type": "string"}
        }
    ),
    SendEmailNodeExecutor
)
