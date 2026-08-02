from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Coroutine
from app.core.execution.context import ExecutionContext, ExecutionState, NodeExecutionResult
from app.core.compiler.models import CompiledNode
from app.core.services.factory import ExecutionServices

class NodeExecutionMiddleware(ABC):
    @abstractmethod
    async def execute(
        self,
        node: CompiledNode,
        context: ExecutionContext,
        state: ExecutionState,
        services: ExecutionServices,
        next_call: Callable[[], Coroutine[Any, Any, NodeExecutionResult]]
    ) -> NodeExecutionResult:
        pass
