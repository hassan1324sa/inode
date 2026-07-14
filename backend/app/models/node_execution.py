from app.models.base import BaseDocument
from typing import Dict, Any, Optional, List
from app.models.enums import ExecutionStatus

class NodeExecution(BaseDocument):
    execution_id: str
    node_id: str
    status: ExecutionStatus = ExecutionStatus.QUEUED
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration: float = 0.0
    input: Dict[str, Any] = {}
    output: Dict[str, Any] = {}
    error: Optional[str] = None
    logs: List[str] = []

    class Settings:
        name = "node_executions"
