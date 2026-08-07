from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import uuid
import time

class ExecutionEventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str
    workflow_id: str = "default_workflow"
    tenant_id: str = "default_tenant"
    correlation_id: Optional[str] = None
    sequence: int = 0
    timestamp: float = Field(default_factory=time.time)
    event_type: str
    node_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data: Any):
        super().__init__(**data)
        from app.core.security.secrets import SecretRedactor
        self.payload = SecretRedactor.redact(self.payload)

# Backward-compatibility alias or subclass
class ExecutionEvent(ExecutionEventEnvelope):
    pass
