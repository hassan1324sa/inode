from pydantic import BaseModel, Field
from typing import Dict, Any, List, Type, Optional
from app.core.nodes.node_executor import BaseNodeExecutor

class NodeCapabilities(BaseModel):
    supports_retry: bool = False
    supports_timeout: bool = False
    supports_streaming: bool = False
    deterministic: bool = False
    requires_network: bool = False

class NodeManifest(BaseModel):
    id: str
    version: str
    author: str
    category: str
    capabilities: NodeCapabilities
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    permissions: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)

class NodeRegistry:
    """
    Platform Node Registry managing registration and lookup of NodeManifest schemas and their executors.
    """
    _manifests: Dict[str, NodeManifest] = {}
    _executors: Dict[str, Type[BaseNodeExecutor]] = {}

    @classmethod
    def register(cls, manifest: NodeManifest, executor_cls: Type[BaseNodeExecutor]):
        if manifest.id in cls._manifests:
            # Check if registering the exact same version and class is okay
            existing = cls._manifests[manifest.id]
            if existing.version == manifest.version:
                raise ValueError(f"Duplicate node registration detected: {manifest.id} v{manifest.version}")
        
        cls._manifests[manifest.id] = manifest
        cls._executors[manifest.id] = executor_cls

    @classmethod
    def get_manifest(cls, node_type: str) -> Optional[NodeManifest]:
        return cls._manifests.get(node_type)

    @classmethod
    def get_executor(cls, node_type: str) -> Optional[Type[BaseNodeExecutor]]:
        return cls._executors.get(node_type)

    @classmethod
    def list_manifests(cls, category: Optional[str] = None) -> List[NodeManifest]:
        if category:
            return [m for m in cls._manifests.values() if m.category == category]
        return list(cls._manifests.values())

    @classmethod
    def clear(cls):
        cls._manifests.clear()
        cls._executors.clear()
