from app.models.base import BaseDocument
from typing import Dict, Any

class Organization(BaseDocument):
    name: str
    slug: str
    owner_id: str
    plan: str = "free"
    settings: Dict[str, Any] = {}
    limits: Dict[str, int] = {
        "max_workflows": 10,
        "max_executions_daily": 1000
    }
    
    class Settings:
        name = "organizations"
