from pydantic import BaseModel, Field
from typing import List, Dict, Any

class AgentContext(BaseModel):
    """
    Static metadata of an agent execution session.
    """
    session_id: str
    agent_id: str
    tenant_id: str
    permissions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
