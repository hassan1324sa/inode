from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class PackageManifest(BaseModel):
    """
    Metadata representation of a Fluxa dynamic extension package.
    """
    name: str
    version: str
    description: Optional[str] = None
    nodes: List[str] = Field(default_factory=list)
    providers: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
