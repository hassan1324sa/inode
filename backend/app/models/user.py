from app.models.base import BaseDocument
from typing import Optional, List

class User(BaseDocument):
    email: str
    password_hash: str
    name: str
    is_verified: bool = False
    refresh_tokens: List[str] = []

    class Settings:
        name = "users"
