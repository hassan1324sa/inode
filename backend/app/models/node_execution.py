from app.models.base import BaseDocument
from typing import Dict, Any, Optional

class NodeExecution(BaseDocument):
    execution_id: str
    node_id: str
    status: str = "Completed" # Running, Completed, Failed
    input: Dict[str, Any] = {}
    output: Dict[str, Any] = {}
    error: Optional[str] = None
    duration: float = 0.0

    class Settings:
        name = "node_executions"
