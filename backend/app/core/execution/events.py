from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class ExecutionEvent(BaseModel):
    event_type: str
    execution_id: str
    timestamp: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
