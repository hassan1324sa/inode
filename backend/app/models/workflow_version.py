from app.models.base import BaseDocument
from typing import Dict, Any, List

class WorkflowVersion(BaseDocument):
    workflow_id: str
    version: str
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    settings: Dict[str, Any] = {}
    created_by: str

    class Settings:
        name = "workflow_versions"
