from app.models.base import BaseDocument
from typing import Optional, List, Dict, Any

class Execution(BaseDocument):
    workflow_id: str
    workflow_version_id: str
    organization_id: str
    status: str = "Queued" # Queued, Running, Completed, Failed, Cancelled
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration: Optional[float] = None
    trigger_type: str = "Manual"
    retry_count: int = 0
    nodes_snapshot: List[Dict[str, Any]] = []
    edges_snapshot: List[Dict[str, Any]] = []

    class Settings:
        name = "executions"
