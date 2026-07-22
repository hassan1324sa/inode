from abc import ABC, abstractmethod
from typing import Dict, Type, Optional, Any
from app.core.execution.context import ExecutionContext

class BaseNodeExecutor(ABC):
    """
    Abstract base class for executing a specific node type.
    """
    @abstractmethod
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        """
        Execute node logic and return updated ExecutionContext.
        """
        pass

class NodeExecutorRegistry:
    """
    Registry for dynamic mapping of node types to their executor classes.
    """
    _registry: Dict[str, Type[BaseNodeExecutor]] = {}

    @classmethod
    def register(cls, node_type: str):
        """
        Decorator to register a node executor class under a specific node type.
        """
        def decorator(executor_class: Type[BaseNodeExecutor]):
            cls._registry[node_type] = executor_class
            return executor_class
        return decorator

    @classmethod
    def get_executor(cls, node_type: str) -> Optional[BaseNodeExecutor]:
        """
        Retrieve an instance of the executor class registered under node_type.
        """
        executor_class = cls._registry.get(node_type)
        if executor_class:
            return executor_class()
        return None
