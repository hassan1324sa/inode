import time
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.core.security.secrets import SecretRedactor

class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=time.time)
    actor: str
    tenant_id: str
    workspace_id: str
    action: str
    resource: str
    decision: str  # ALLOW, DENY, REQUIRE_APPROVAL
    policy_id: Optional[str] = "default"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SecurityAuditLogger:
    _logs: List[AuditEvent] = []

    @classmethod
    def log_event(cls, event: AuditEvent):
        # Apply strict secret redaction to metadata values
        event.metadata = SecretRedactor.redact(event.metadata)
        cls._logs.append(event)

    @classmethod
    def get_logs(cls) -> List[AuditEvent]:
        return cls._logs

    @classmethod
    def clear(cls):
        cls._logs.clear()
