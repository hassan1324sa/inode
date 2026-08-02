import asyncio
from typing import Dict, Any, List, Optional, Callable, Coroutine
from pydantic import BaseModel, Field
from app.core.registry.provider_registry import ProviderRegistry, ProviderMetadata

class MCPToolSchema(BaseModel):
    """
    Schema representation of a tool exposed by an MCP server.
    """
    name: str
    description: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)

class MCPClientDriver:
    """
    Driver for interacting with an MCP (Model Context Protocol) server.
    Can be registered inside ProviderRegistry with type='mcp'.
    """
    def __init__(
        self,
        server_url: str,
        transport: str = "stdio",
        tools: Optional[List[MCPToolSchema]] = None,
        tool_handler: Optional[Callable[[str, Dict[str, Any]], Coroutine[Any, Any, Any]]] = None
    ):
        self.server_url = server_url
        self.transport = transport
        self._tools: Dict[str, MCPToolSchema] = {}
        if tools:
            for t in tools:
                self._tools[t.name] = t
        self._tool_handler = tool_handler

    def list_tools(self) -> List[MCPToolSchema]:
        return list(self._tools.values())

    def get_tool(self, tool_name: str) -> Optional[MCPToolSchema]:
        return self._tools.get(tool_name)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        if tool_name not in self._tools:
            raise ValueError(f"MCP tool '{tool_name}' not found on server {self.server_url}")
        
        if self._tool_handler:
            return await self._tool_handler(tool_name, arguments)
        
        # Default mock execution if no handler provided
        return {
            "status": "success",
            "server": self.server_url,
            "tool": tool_name,
            "arguments": arguments
        }

class MCPProviderManager:
    """
    Manages registration and lifecycle of MCP client drivers in ProviderRegistry.
    """
    @classmethod
    def register_mcp_server(
        cls,
        name: str,
        server_url: str,
        tools: List[MCPToolSchema],
        transport: str = "stdio",
        tool_handler: Optional[Callable[[str, Dict[str, Any]], Coroutine[Any, Any, Any]]] = None
    ) -> MCPClientDriver:
        metadata = ProviderMetadata(
            name=name,
            type="mcp",
            version="1.0",
            capabilities=[f"tool:{t.name}" for t in tools]
        )
        driver = MCPClientDriver(
            server_url=server_url,
            transport=transport,
            tools=tools,
            tool_handler=tool_handler
        )
        ProviderRegistry.register(metadata, driver)
        return driver

    @classmethod
    def get_mcp_driver(cls, name: str) -> Optional[MCPClientDriver]:
        return ProviderRegistry.get("mcp", name)

    @classmethod
    def list_mcp_drivers(cls) -> List[ProviderMetadata]:
        return ProviderRegistry.list_providers(type="mcp")
