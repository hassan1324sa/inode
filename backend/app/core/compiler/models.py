from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class CompiledNode(BaseModel):
    id: str
    name: str
    type: str
    data: Dict[str, Any] = Field(default_factory=dict)
