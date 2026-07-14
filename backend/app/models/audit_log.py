from app.models.base import BaseDocument
from typing import Dict, Any

class AuditLog(BaseDocument):
    user_id: str
    organization_id: str
    action: str
    details: Dict[str, Any] = {}

    class Settings:
        name = "audit_logs"
