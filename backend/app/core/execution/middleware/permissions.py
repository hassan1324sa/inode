from typing import Dict, Any, Callable, Coroutine
from app.core.execution.middleware.base import NodeExecutionMiddleware
from app.core.execution.context import ExecutionContext, ExecutionState, NodeExecutionResult
from app.core.services.factory import ExecutionServices
from app.core.compiler.models import CompiledNode
from app.core.registry.node_registry import NodeRegistry
from app.core.execution.permissions import PolicyEngine
from app.core.execution.errors import PermanentError

class PermissionMiddleware(NodeExecutionMiddleware):
    """
    Middleware that enforces security policies by validating node required permissions.
    """
    async def execute(
        self,
        node: CompiledNode,
        context: ExecutionContext,
        state: ExecutionState,
        services: ExecutionServices,
        next_call: Callable[[], Coroutine[Any, Any, NodeExecutionResult]]
    ) -> NodeExecutionResult:
        # Check node manifest if registered
        manifest = NodeRegistry.get_manifest(node.type)
        if manifest and manifest.permissions:
            allowed = PolicyEngine.is_allowed(manifest.permissions, context.permissions)
            if not allowed:
                raise PermanentError(
                    f"Node {node.id} execution denied. Required permissions: {manifest.permissions}, "
                    f"granted: {context.permissions}"
                )
        
        return await next_call()
