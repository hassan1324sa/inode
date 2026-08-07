from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.core.registry.node_registry import NodeRegistry
from app.core.registry.provider_registry import ProviderRegistry
from app.core.registry.trigger_registry import TriggerRegistry
from app.core.agents.tools import ToolRegistry

class CapabilityMapping(BaseModel):
    source_type: str  # "node", "tool", "provider", "trigger"
    identifier: str
    description: str
    capabilities: List[str] = []

class UnifiedCapabilitySystem:
    """
    Unified capability resolver querying all active registries (Nodes, Tools, Providers, Triggers).
    Allows Planners to query capabilities dynamically.
    """
    @classmethod
    def get_mappings(cls) -> List[CapabilityMapping]:
        mappings = []

        # 1. Gather from NodeRegistry
        for manifest in NodeRegistry.list_manifests():
            # Derive capabilities from manifest category, id, and permissions
            caps = [manifest.category, f"node:{manifest.id}"]
            if manifest.permissions:
                caps.extend(manifest.permissions)
            
            mappings.append(
                CapabilityMapping(
                    source_type="node",
                    identifier=manifest.id,
                    description=f"Node-backed component under category {manifest.category}",
                    capabilities=caps
                )
            )

        # 2. Gather from ToolRegistry
        for tool in ToolRegistry.list_tools():
            caps = [tool.category, f"tool:{tool.name}"]
            if tool.permissions:
                caps.extend(tool.permissions)
            
            # Check if already added via Node backing to avoid duplicates
            if not any(m.identifier == tool.name and m.source_type == "node" for m in mappings):
                mappings.append(
                    CapabilityMapping(
                        source_type="tool",
                        identifier=tool.name,
                        description=tool.description,
                        capabilities=caps
                    )
                )

        # 3. Gather from ProviderRegistry
        # We can dynamically fetch providers from the class registry
        for p_name, metadata in ProviderRegistry._providers.items():
            mappings.append(
                CapabilityMapping(
                    source_type="provider",
                    identifier=p_name,
                    description=f"Provider driver: {metadata.description}",
                    capabilities=[metadata.category, f"provider:{p_name}"]
                )
            )

        # 4. Gather from TriggerRegistry
        for trigger_id, trig in TriggerRegistry._triggers.items():
            mappings.append(
                CapabilityMapping(
                    source_type="trigger",
                    identifier=trigger_id,
                    description=f"Trigger of class {trig.__class__.__name__}",
                    capabilities=["trigger", f"trigger:{trig.__class__.__name__.lower()}"]
                )
            )

        return mappings

    @classmethod
    def find_satisfying_entities(cls, required_capability: str) -> List[CapabilityMapping]:
        mappings = cls.get_mappings()
        results = []
        for m in mappings:
            # Match directly or by wildcard
            matched = False
            for cap in m.capabilities:
                if cap == required_capability:
                    matched = True
                    break
                # Handle simple namespace/wildcard match, e.g. "network:*" matching "network:http"
                if ":" in required_capability and required_capability.endswith("*"):
                    prefix = required_capability.split(":")[0]
                    if cap.startswith(prefix + ":"):
                        matched = True
                        break
            if matched:
                results.append(m)
        return results
