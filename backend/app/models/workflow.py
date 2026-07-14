from app.models.base import BaseDocument
from typing import Optional

class Workflow(BaseDocument):
    organization_id: str
    name: str
    description: Optional[str] = None
    current_version: str = "v1"
    published_version: Optional[str] = None
    status: str = "Draft" # Draft, Published, Archived

    class Settings:
        name = "workflows"
