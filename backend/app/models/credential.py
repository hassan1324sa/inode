from app.models.base import BaseDocument

class Credential(BaseDocument):
    organization_id: str
    provider: str
    encrypted_data: str

    class Settings:
        name = "credentials"
