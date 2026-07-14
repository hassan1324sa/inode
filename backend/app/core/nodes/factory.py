from typing import Any, Dict
from app.core.nodes.base import BaseNode
from app.core.nodes.registry import NodeRegistry

class NodeFactory:
    """
    Factory to instantiate nodes based on their type.
    """
    @staticmethod
    def create_node(node_data: Dict[str, Any]) -> BaseNode:
        """
        Creates a node instance from a dictionary.
        """
        if "type" not in node_data:
            raise ValueError("Node data must contain a 'type' field.")
            
        node_type = node_data["type"]
        node_class = NodeRegistry.get_node_class(node_type)
        
        if not node_class:
            raise ValueError(f"Unknown node type: {node_type}")
            
        # Pydantic will handle validation and instantiation
        return node_class(**node_data)
