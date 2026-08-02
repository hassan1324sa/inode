from abc import ABC, abstractmethod
from typing import Dict, Any

class Credential(ABC):
    """
    Abstract base class for SDK credentials.
    Allows extensible authentication mechanisms without modifying core client logic.
    """
    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """Return HTTP headers required for authentication."""
        pass


class ApiKeyCredential(Credential):
    """
    Authentication using an API Key header (e.g. X-API-Key).
    """
    def __init__(self, api_key: str, header_name: str = "X-API-Key"):
        if not api_key:
            raise ValueError("API key must not be empty")
        self.api_key = api_key
        self.header_name = header_name

    def get_headers(self) -> Dict[str, str]:
        return {self.header_name: self.api_key}


class BearerTokenCredential(Credential):
    """
    Authentication using an Authorization Bearer token header.
    """
    def __init__(self, token: str):
        if not token:
            raise ValueError("Bearer token must not be empty")
        self.token = token

    def get_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


class CustomCredential(Credential):
    """
    Custom credential provider that injects arbitrary headers.
    """
    def __init__(self, headers: Dict[str, str]):
        if not headers:
            raise ValueError("Custom headers dict must not be empty")
        self.headers = headers

    def get_headers(self) -> Dict[str, str]:
        return self.headers.copy()
