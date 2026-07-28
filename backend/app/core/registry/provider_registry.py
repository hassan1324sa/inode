from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class ProviderMetadata(BaseModel):
    name: str
    type: str  # e.g., 'llm', 'storage', 'secrets'
    version: str = "1.0"
    capabilities: List[str] = Field(default_factory=list)

class ProviderRegistry:
    """
    Registry for managing plugin drivers/providers.
    """
    _metadata: Dict[str, ProviderMetadata] = {}
    _providers: Dict[str, Any] = {}

    @classmethod
    def register(cls, metadata: ProviderMetadata, provider_instance: Any):
        key = f"{metadata.type}:{metadata.name}"
        if key in cls._metadata:
            raise ValueError(f"Provider already registered: {key}")
        cls._metadata[key] = metadata
        cls._providers[key] = provider_instance

    @classmethod
    def get(cls, type: str, name: str) -> Optional[Any]:
        return cls._providers.get(f"{type}:{name}")

    @classmethod
    def get_metadata(cls, type: str, name: str) -> Optional[ProviderMetadata]:
        return cls._metadata.get(f"{type}:{name}")

    @classmethod
    def list_providers(cls, type: Optional[str] = None) -> List[ProviderMetadata]:
        if type:
            return [m for m in cls._metadata.values() if m.type == type]
        return list(cls._metadata.values())

    @classmethod
    def clear(cls):
        cls._metadata.clear()
        cls._providers.clear()
