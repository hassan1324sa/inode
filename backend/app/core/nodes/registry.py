from typing import Dict, Type, Optional
from app.core.nodes.base import BaseNode

class NodeRegistry:
    """
    Registry for workflow node types.
    Maintains a mapping from node type strings to Node classes.
    """
    _registry: Dict[str, Type[BaseNode]] = {}

    @classmethod
    def register(cls, node_type: str):
        """
        Decorator to register a node class.
        """
        def decorator(node_class: Type[BaseNode]):
            cls._registry[node_type] = node_class
            return node_class
        return decorator

    @classmethod
    def get_node_class(cls, node_type: str) -> Optional[Type[BaseNode]]:
        """
        Retrieve a node class by its type.
        """
        return cls._registry.get(node_type)

    @classmethod
    def list_registered_nodes(cls) -> Dict[str, Type[BaseNode]]:
        """
        Get all registered nodes.
        """
        return dict(cls._registry)
