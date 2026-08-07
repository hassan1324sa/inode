from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.core.providers.mcp import MCPProviderManager
from app.core.execution.permissions import PolicyEngine

class ToolMetadata(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    category: str = "custom"
    cost_estimate: float = 0.0
    latency_ms: int = 100
    supports_parallel: bool = True
    permissions: List[str] = Field(default_factory=list)

class BaseTool(ABC):
    def __init__(self, metadata: ToolMetadata):
        self.metadata = metadata

    @abstractmethod
    async def execute(self, args: Dict[str, Any], context: Any) -> Any:
        pass

class NativeTool(BaseTool):
    """
    Direct Python code tools.
    """
    def __init__(self, metadata: ToolMetadata, handler: Any):
        super().__init__(metadata)
        self.handler = handler

    async def execute(self, args: Dict[str, Any], context: Any) -> Any:
        if self.handler:
            return await self.handler(args, context)
        return None

class NodeBackedTool(BaseTool):
    """
    Wraps existing NodeRegistry nodes as tools.
    """
    def __init__(self, node_type: str):
        from app.core.registry.node_registry import NodeRegistry
        manifest = NodeRegistry.get_manifest(node_type)
        if not manifest:
            raise ValueError(f"Node type {node_type} not registered in NodeRegistry.")
        
        metadata = ToolMetadata(
            name=manifest.id,
            description=f"Node-backed tool: {manifest.id}",
            input_schema=manifest.inputs,
            output_schema=manifest.outputs,
            category="node-backed",
            permissions=manifest.permissions
        )
        super().__init__(metadata)
        self.node_type = node_type

    async def execute(self, args: Dict[str, Any], context: Any) -> Any:
        executor_cls = NodeRegistry.get_executor(self.node_type)
        if not executor_cls:
            raise ValueError(f"No executor found for node type {self.node_type}")
        
        # Instantiate and execute using node execution flow
        executor = executor_cls()
        # Mocking context, state, services as expected by BaseNodeExecutor subclass
        from app.core.execution.context import ExecutionState
        from app.core.services.factory import ExecutionServicesFactory
        state = ExecutionState()
        services = ExecutionServicesFactory.create_services()
        
        result = await executor.execute(args, context, state, services)
        return result.output_data

class MCPTool(BaseTool):
    """
    Model Context Protocol tools retrieved from MCP Provider Registry.
    """
    def __init__(self, server_name: str, tool_name: str):
        driver = MCPProviderManager.get_mcp_driver(server_name)
        if not driver:
            raise ValueError(f"MCP server {server_name} not found.")
        
        mcp_tool = None
        for t in driver.list_tools():
            if t.name == tool_name:
                mcp_tool = t
                break
        
        if not mcp_tool:
            raise ValueError(f"Tool {tool_name} not found on MCP server {server_name}")
            
        metadata = ToolMetadata(
            name=f"{server_name}:{tool_name}",
            description=mcp_tool.description,
            input_schema=mcp_tool.input_schema,
            category="mcp"
        )
        super().__init__(metadata)
        self.server_name = server_name
        self.tool_name = tool_name

    async def execute(self, args: Dict[str, Any], context: Any) -> Any:
        from app.core.security.context import SecurityContextHolder, SecurityException
        ctx = SecurityContextHolder._context_var.get()
        if not ctx or not ctx.organization_id:
            raise SecurityException("Access Denied: Missing organization context during tool execution (Fail Closed).")

        driver = MCPProviderManager.get_mcp_driver(self.server_name)
        if not driver:
            raise SecurityException(f"Access Denied: MCP server '{self.server_name}' is not registered or not authorized for this organization.")
        return await driver.call_tool(self.tool_name, args)

class RemoteTool(BaseTool):
    """
    HTTP REST / API endpoints.
    """
    def __init__(self, metadata: ToolMetadata, endpoint_url: str):
        super().__init__(metadata)
        self.endpoint_url = endpoint_url

    async def execute(self, args: Dict[str, Any], context: Any) -> Any:
        import httpx
        async with httpx.AsyncClient() as client:
            res = await client.post(self.endpoint_url, json=args)
            res.raise_for_status()
            return res.json()


class ToolRegistry:
    _custom_tools: Dict[str, BaseTool] = {}

    @classmethod
    def register_tool(cls, tool: BaseTool):
        cls._custom_tools[tool.metadata.name] = tool

    @classmethod
    def get_tool(cls, name: str) -> Optional[BaseTool]:
        # 1. Check custom registered tools
        if name in cls._custom_tools:
            return cls._custom_tools[name]
        
        # 2. Check NodeRegistry
        if NodeRegistry.get_manifest(name):
            return NodeBackedTool(name)

        # 3. Check MCP (name format: "server_name:tool_name")
        if ":" in name:
            server_name, tool_name = name.split(":", 1)
            try:
                return MCPTool(server_name, tool_name)
            except Exception:
                pass

        return None

    @classmethod
    def list_tools(cls) -> List[ToolMetadata]:
        all_tools = [t.metadata for t in cls._custom_tools.values()]
        
        # Add Node registry manifests
        from app.core.registry.node_registry import NodeRegistry
        for manifest in NodeRegistry.list_manifests():
            all_tools.append(
                ToolMetadata(
                    name=manifest.id,
                    description=f"Node: {manifest.id}",
                    input_schema=manifest.inputs,
                    output_schema=manifest.outputs,
                    category="node-backed",
                    permissions=manifest.permissions
                )
            )
        
        return all_tools

    @classmethod
    def clear(cls):
        cls._custom_tools.clear()


class ToolExecutor:
    """
    Executes tools utilizing capability negotiation: Discover, Validate, Negotiate, Execute.
    """
    async def execute_tool(self, tool_name: str, args: Dict[str, Any], context: Any) -> Any:
        import logging
        logger = logging.getLogger("fluxa.tool_executor")

        # 1. Discover
        tool = ToolRegistry.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not discovered/registered.")

        # 2. Validate Authorization & Tenant Scope
        tenant_id = getattr(context, "tenant_id", None)
        if not tenant_id:
            raise PermissionError("Access Denied: Missing tenant scope context during tool execution (Fail Closed).")

        # Check permissions
        if tool.metadata.permissions:
            context_permissions = getattr(context, "permissions", [])
            if not PolicyEngine.is_allowed(tool.metadata.permissions, context_permissions):
                raise PermissionError(f"Execution of tool {tool_name} denied: insufficient permissions.")

        # Validate input schema keys
        for req_key in tool.metadata.input_schema.get("required", []):
            if req_key not in args:
                raise ValueError(f"Missing required parameter '{req_key}' for tool {tool_name}")

        # 3. Negotiate (cost limits and user approval policy check)
        max_cost = getattr(context, "max_cost", 10.0)
        if tool.metadata.cost_estimate > max_cost:
            raise PermissionError(f"Tool execution denied: cost estimate {tool.metadata.cost_estimate} exceeds max cost policy limit {max_cost}")

        if getattr(context, "require_approval", False) and tool_name in getattr(context, "sensitive_tools", []):
            approved = args.get("_approved", False)
            if not approved:
                raise PermissionError(f"Tool {tool_name} requires explicit user approval.")

        # 4. Check for Deterministic Replay / Effect cache (both original retry runs and replays)
        import json
        import hashlib
        arg_str = json.dumps(args, sort_keys=True)
        request_hash = hashlib.sha256((tool_name + arg_str).encode("utf-8")).hexdigest()

        execution_id = getattr(context, "session_id", None) or getattr(context, "execution_id", None)
        if execution_id:
            from app.core.execution.durable_store import MongoDBEventStore
            lookup_id = str(execution_id).replace("replay-", "")
            effect = await MongoDBEventStore.get_effect(lookup_id, tool_name, request_hash)
            if effect:
                logger.info(f"Matching effect found for tool {tool_name} (Deduplicated retry/replay). Skipping execution.")
                return effect.response.get("output")

        # 5. Execute
        result = await tool.execute(args, context)

        # Save effect if execution_id is available
        if execution_id:
            from app.core.execution.durable_store import MongoDBEventStore, ExecutionEffect
            effect = ExecutionEffect(
                execution_id=str(execution_id),
                node_id=tool_name,
                effect_type="tool",
                provider=tool.metadata.category,
                request_hash=request_hash,
                response={"output": result}
            )
            await MongoDBEventStore.save_effect(effect)

        return result
