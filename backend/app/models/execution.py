from app.models.base import BaseDocument
from typing import Optional, List, Dict, Any
from app.models.enums import ExecutionStatus

class Execution(BaseDocument):
    workflow_id: str
    workflow_version_id: str
    organization_id: str
    status: ExecutionStatus = ExecutionStatus.QUEUED
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration: Optional[float] = None
    trigger_type: str = "Manual"
    retry_count: int = 0
    nodes_snapshot: List[Dict[str, Any]] = []
    edges_snapshot: List[Dict[str, Any]] = []

    class Settings:
        name = "executions"
