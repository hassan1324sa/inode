import json
from typing import Dict, Any, List
from app.core.registry.node_registry import NodeRegistry
from app.core.registry.provider_registry import ProviderRegistry
from app.core.registry.trigger_registry import TriggerRegistry


class DocumentationGenerator:
    """
    Generates rich documentation in multiple formats (Markdown, HTML, JSON, OpenAPI summary,
    SDK reference documentation, and Mermaid diagrams) for project registries and workflows.
    """
    @classmethod
    def generate_node_docs_markdown(cls) -> str:
        lines = ["# Fluxa Node Registry Documentation\n", "| Node ID | Category | Version | Author | Supports Retry |", "|---|---|---|---|---|"]
        for manifest in NodeRegistry.list_manifests():
            retry = manifest.capabilities.supports_retry if manifest.capabilities else False
            lines.append(f"| `{manifest.id}` | {manifest.category} | {manifest.version} | {manifest.author} | {retry} |")
        return "\n".join(lines) + "\n"

    @classmethod
    def generate_provider_docs_markdown(cls) -> str:
        lines = ["# Fluxa Provider Registry Documentation\n", "| Provider Type | Description | Version |", "|---|---|---|"]
        for meta in ProviderRegistry.list_providers():
            lines.append(f"| `{meta.type}` | {meta.description} | {meta.version} |")
        return "\n".join(lines) + "\n"

    @classmethod
    def generate_markdown(cls) -> str:
        """Generate unified Markdown documentation."""
        return cls.generate_node_docs_markdown() + "\n" + cls.generate_provider_docs_markdown()

    @classmethod
    def generate_html(cls) -> str:
        """Generate clean HTML documentation."""
        html = ["<html><head><title>Fluxa Documentation</title></head><body>", "<h1>Fluxa Node Registry</h1>", "<table border='1'><tr><th>ID</th><th>Category</th><th>Version</th></tr>"]
        for m in NodeRegistry.list_manifests():
            html.append(f"<tr><td>{m.id}</td><td>{m.category}</td><td>{m.version}</td></tr>")
        html.append("</table></body></html>")
        return "".join(html)

    @classmethod
    def generate_json(cls) -> str:
        """Generate structured JSON representation of all registries."""
        data = {
            "nodes": {m.id: m.model_dump() for m in NodeRegistry.list_manifests()},
            "providers": {f"{m.type}:{m.name}": m.model_dump() for m in ProviderRegistry.list_providers()},
            "triggers": list(TriggerRegistry._triggers.keys())
        }
        return json.dumps(data, indent=2)

    @classmethod
    def generate_openapi_summary(cls) -> str:
        """Generate a summary OpenAPI 3.0 specification for core Fluxa API routes."""
        schema = {
            "openapi": "3.0.0",
            "info": {"title": "Fluxa API", "version": "1.3.0"},
            "paths": {
                "/api/v1/health": {"get": {"summary": "Health Check"}},
                "/api/v1/workflows/run": {"post": {"summary": "Run Workflow"}},
                "/api/v1/packages/install": {"post": {"summary": "Install Package"}},
            }
        }
        return json.dumps(schema, indent=2)

    @classmethod
    def generate_sdk_reference(cls) -> str:
        """Generate Markdown SDK reference documentation for Python and TypeScript."""
        doc = (
            "# Fluxa SDK Reference\n\n"
            "## Python SDK\n"
            "```python\n"
            "from fluxa_sdk import FluxaClient, AsyncFluxaClient, ApiKeyCredential\n"
            "client = FluxaClient(credential=ApiKeyCredential('key'))\n"
            "res = client.workflows.run({'id': 'wf1', 'nodes': [], 'edges': []})\n"
            "```\n\n"
            "## TypeScript SDK\n"
            "```typescript\n"
            "import { FluxaClient } from '@fluxa/sdk';\n"
            "const client = new FluxaClient({ apiKey: 'key' });\n"
            "```\n"
        )
        return doc

    @classmethod
    def generate_mermaid_diagram(cls, workflow_dict: Dict[str, Any]) -> str:
        """
        Generate a Mermaid flowchart diagram (`flowchart TD`) from a workflow dictionary.
        """
        lines = ["flowchart TD"]
        nodes = workflow_dict.get("nodes", [])
        edges = workflow_dict.get("edges", [])
        for node in nodes:
            nid = node.get("id", "node")
            ntype = node.get("type", "default")
            label = f'{nid}["{nid} ({ntype})"]'
            lines.append(f"    {label}")
        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            if src and tgt:
                lines.append(f"    {src} --> {tgt}")
        return "\n".join(lines)
