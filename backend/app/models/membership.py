from app.models.base import BaseDocument
from beanie import Link
from app.models.user import User
from app.models.organization import Organization
from typing import List

class Membership(BaseDocument):
    organization_id: str
    user_id: str
    role: str # "Owner", "Admin", "Editor", "Viewer"
    permissions: List[str] = []

    class Settings:
        name = "memberships"
