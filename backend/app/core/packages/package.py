import hashlib
import json
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class PackageManifest(BaseModel):
    """
    Metadata representation of a Fluxa dynamic extension package.
    """
    name: str
    version: str
    description: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    engines: Dict[str, str] = Field(default_factory=dict)  # e.g. {"fluxa": ">=1.0", "python": ">=3.10"}
    nodes: List[str] = Field(default_factory=list)
    providers: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)  # e.g. ["fluxa-llm>=1.0.0"]
    hash: Optional[str] = None
    signature: Optional[str] = None

    def compute_hash(self) -> str:
        """
        Compute a SHA-256 hash of the canonical manifest payload (excluding signature and hash fields).
        """
        payload = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "publisher": self.publisher,
            "engines": self.engines,
            "nodes": sorted(self.nodes),
            "providers": sorted(self.providers),
            "tools": sorted(self.tools),
            "skills": sorted(self.skills),
            "dependencies": sorted(self.dependencies),
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def set_hash(self):
        self.hash = self.compute_hash()
