from app.models.base import BaseDocument
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

class RefreshTokenRecord(BaseModel):
    jti: str
    token_hash: str
    created_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime] = None

class User(BaseDocument):
    email: str
    password_hash: str
    name: str
    is_verified: bool = False
    refresh_token_records: List[RefreshTokenRecord] = []

    class Settings:
        name = "users"
