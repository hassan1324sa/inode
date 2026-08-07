from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from app.core.agents.tools import ToolMetadata

class SkillManifest(BaseModel):
    name: str
    version: str
    description: str
    author: str
    tools: List[ToolMetadata] = Field(default_factory=list)
    system_prompts: Dict[str, str] = Field(default_factory=dict)
    memory_rules: List[str] = Field(default_factory=list)


class SkillPackage(BaseModel):
    manifest: SkillManifest
    templates: Dict[str, str] = Field(default_factory=dict)

    def get_prompt_template(self, name: str) -> Optional[str]:
        return self.templates.get(name)

    def list_capabilities(self) -> List[str]:
        caps = [f"skill:{self.manifest.name}"]
        for tool in self.manifest.tools:
            caps.append(f"tool:{tool.name}")
        return caps
