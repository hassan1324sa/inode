from typing import Any, Dict, List
import imaplib
import email
from email.header import decode_header
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext
from app.core.services.variables.resolver import VariableResolver

@NodeExecutorRegistry.register("read-email-imap")
class ReadEmailImapExecutor(BaseNodeExecutor):
    """
    Node executor to connect to an IMAP server and fetch recent emails.
    Performs actual connection and parses headers/bodies.
    """
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        node_id = node_data.get("id", "read-email-imap")
        
        data_sub = node_data.get("data", {})
        host_raw = node_data.get("imapHost") or data_sub.get("imapHost") or "imap.gmail.com"
        port_raw = node_data.get("imapPort") or data_sub.get("imapPort") or "993"
        username_raw = node_data.get("username") or data_sub.get("username") or ""
        password_ref = node_data.get("password_ref") or data_sub.get("password_ref")
        folder_raw = node_data.get("folder") or data_sub.get("folder") or "INBOX"
        max_emails_raw = node_data.get("maxEmails") or data_sub.get("maxEmails") or "5"

        from app.core.security.secrets import VaultSecretProvider, SecretRef
        password = ""
        if password_ref:
            provider = VaultSecretProvider()
            if isinstance(password_ref, dict):
                try:
                    ref = SecretRef(**password_ref)
                    password = await provider.get(ref)
                except Exception:
                    password = ""
            else:
                try:
                    ref = SecretRef(provider="vault", path=str(password_ref), version="1")
                    password = await provider.get(ref)
                except Exception:
                    password = str(password_ref)
                if not password:
                    password = str(password_ref)

        # Resolve variables
        host = VariableResolver.resolve(host_raw, context.variables, context.node_outputs)
        port = int(VariableResolver.resolve(str(port_raw), context.variables, context.node_outputs))
        username = VariableResolver.resolve(username_raw, context.variables, context.node_outputs)
        folder = VariableResolver.resolve(folder_raw, context.variables, context.node_outputs)
        max_emails = int(VariableResolver.resolve(str(max_emails_raw), context.variables, context.node_outputs))

        if not username or not password:
            raise ValueError("IMAP Read Email Node: Username and password (Vault) are required.")

        fetched_emails: List[Dict[str, Any]] = []

        try:
            # 1. Establish SSL connection
            mail = imaplib.IMAP4_SSL(host, port)
            mail.login(username, password)
            
            # 2. Select folder
            mail.select(folder)
            
            # 3. Search for all emails
            status, messages = mail.search(None, "ALL")
            if status == "OK" and messages[0]:
                # Get the list of email IDs
                mail_ids = messages[0].split()
                # Get the N most recent email IDs
                recent_ids = mail_ids[-max_emails:]
                recent_ids.reverse()  # Order from newest to oldest

                for mail_id in recent_ids:
                    # Fetch email headers and content
                    res_status, msg_data = mail.fetch(mail_id, "(RFC822)")
                    if res_status != "OK":
                        continue
                        
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            # Decode subject
                            subject, encoding = decode_header(msg["Subject"] or "")[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding or "utf-8", errors="ignore")
                                
                            # Decode sender
                            sender, encoding = decode_header(msg["From"] or "")[0]
                            if isinstance(sender, bytes):
                                sender = sender.decode(encoding or "utf-8", errors="ignore")
                                
                            # Extract body snippet
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_type = part.get_content_type()
                                    content_disposition = str(part.get("Content-Disposition"))
                                    if content_type == "text/plain" and "attachment" not in content_disposition:
                                        payload = part.get_payload(decode=True)
                                        if payload:
                                            body = payload.decode(errors="ignore")
                                            break
                            else:
                                payload = msg.get_payload(decode=True)
                                if payload:
                                    body = payload.decode(errors="ignore")

                            # Store email summary
                            fetched_emails.append({
                                "id": mail_id.decode(),
                                "from": sender,
                                "subject": subject,
                                "date": msg["Date"],
                                "body_snippet": body[:500]  # First 500 characters
                            })

            mail.close()
            mail.logout()

            context.node_outputs[node_id] = {
                "status": "success",
                "emails": fetched_emails,
                "count": len(fetched_emails)
            }

        except Exception as e:
            import logging
            logger = logging.getLogger("fluxa.read_email_imap")
            logger.warning(f"IMAP connection or read failed: {str(e)}. Proceeding with empty emails list fallback to prevent workflow hang.")
            context.node_outputs[node_id] = {
                "status": "warning",
                "emails": [],
                "count": 0
            }

        return context


from app.core.registry.node_registry import NodeRegistry, NodeManifest, NodeCapabilities

NodeRegistry.register(
    NodeManifest(
        id="read-email-imap",
        version="1.0.0",
        author="System",
        category="Communication",
        capabilities=NodeCapabilities(supports_retry=True, requires_network=True),
        inputs={
            "imapHost": {"type": "string"},
            "imapPort": {"type": "string"},
            "username": {"type": "string"},
            "password": {"type": "string"},
            "folder": {"type": "string"},
            "maxEmails": {"type": "string"}
        },
        outputs={
            "status": {"type": "string"},
            "emails": {"type": "array"},
            "count": {"type": "integer"}
        }
    ),
    ReadEmailImapExecutor
)
