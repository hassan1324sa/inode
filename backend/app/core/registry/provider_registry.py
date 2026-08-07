from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from app.core.security.context import SecurityContextHolder, SecurityException

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
    def get_org_prefix(cls) -> str:
        import os
        ctx = SecurityContextHolder._context_var.get()
        if ctx is None:
            if os.environ.get("FLUXA_SYSTEM_BOOTSTRAP") == "true":
                return "global"
            raise SecurityException("Access Denied: Missing security context (Fail Closed).")
        if not ctx.organization_id:
            raise SecurityException("Access Denied: Missing organization ID in security context (Fail Closed).")
        return f"org:{ctx.organization_id}"

    @classmethod
    def register(cls, metadata: ProviderMetadata, provider_instance: Any):
        prefix = cls.get_org_prefix()
        key = f"{prefix}:{metadata.type}:{metadata.name}"
        if key in cls._metadata:
            raise ValueError(f"Provider already registered: {key}")
        cls._metadata[key] = metadata
        cls._providers[key] = provider_instance

    @classmethod
    def register_global(cls, metadata: ProviderMetadata, provider_instance: Any):
        key = f"global:{metadata.type}:{metadata.name}"
        if key in cls._metadata:
            raise ValueError(f"Global provider already registered: {key}")
        cls._metadata[key] = metadata
        cls._providers[key] = provider_instance

    @classmethod
    def get(cls, type: str, name: str) -> Optional[Any]:
        prefix = cls.get_org_prefix()
        org_key = f"{prefix}:{type}:{name}"
        if org_key in cls._providers:
            return cls._providers[org_key]
        global_key = f"global:{type}:{name}"
        return cls._providers.get(global_key)

    @classmethod
    def get_metadata(cls, type: str, name: str) -> Optional[ProviderMetadata]:
        prefix = cls.get_org_prefix()
        org_key = f"{prefix}:{type}:{name}"
        if org_key in cls._metadata:
            return cls._metadata[org_key]
        global_key = f"global:{type}:{name}"
        return cls._metadata.get(global_key)

    @classmethod
    def list_providers(cls, type: Optional[str] = None) -> List[ProviderMetadata]:
        prefix = cls.get_org_prefix()
        result = []
        for key, meta in cls._metadata.items():
            if key.startswith(f"{prefix}:") or key.startswith("global:"):
                if type is None or meta.type == type:
                    result.append(meta)
        return result

    @classmethod
    def clear(cls):
        cls._metadata.clear()
        cls._providers.clear()
