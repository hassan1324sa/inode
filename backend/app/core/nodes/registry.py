from typing import Dict, Type, Optional, List
from pydantic import BaseModel
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


class NodeContract(BaseModel):
    node_type: str
    input_handles: List[str] = ["default"]
    output_handles: List[str] = ["default"]
    is_trigger: bool = False


class TriggerRegistry:
    """
    Registry for valid trigger types.
    """
    _triggers: List[str] = []

    @classmethod
    def register_trigger(cls, node_type: str):
        if node_type not in cls._triggers:
            cls._triggers.append(node_type)

    @classmethod
    def list_triggers(cls) -> List[str]:
        return list(cls._triggers)

    @classmethod
    def is_trigger(cls, node_type: str) -> bool:
        return node_type in cls._triggers


class NodeContractRegistry:
    """
    The Single Source of Truth for valid inputs/outputs and trigger status.
    """
    _contracts: Dict[str, NodeContract] = {}

    @classmethod
    def register_contract(cls, contract: NodeContract):
        cls._contracts[contract.node_type] = contract
        if contract.is_trigger:
            TriggerRegistry.register_trigger(contract.node_type)

    @classmethod
    def get_contract(cls, node_type: str) -> Optional[NodeContract]:
        return cls._contracts.get(node_type)

    @classmethod
    def is_registered(cls, node_type: str) -> bool:
        return node_type in cls._contracts


# Initialize default Node Contracts
NodeContractRegistry.register_contract(NodeContract(node_type="manual_trigger", input_handles=[], output_handles=["default"], is_trigger=True))
NodeContractRegistry.register_contract(NodeContract(node_type="conditional", input_handles=["default"], output_handles=["true", "false"]))
NodeContractRegistry.register_contract(NodeContract(node_type="ai_agent", input_handles=["default"], output_handles=["default"]))
NodeContractRegistry.register_contract(NodeContract(node_type="file_storage", input_handles=["default"], output_handles=["default"]))
NodeContractRegistry.register_contract(NodeContract(node_type="google_sheets", input_handles=["default"], output_handles=["default"]))
NodeContractRegistry.register_contract(NodeContract(node_type="http_request", input_handles=["default"], output_handles=["default"]))
NodeContractRegistry.register_contract(NodeContract(node_type="loop", input_handles=["default"], output_handles=["default"]))
NodeContractRegistry.register_contract(NodeContract(node_type="set_variable", input_handles=["default"], output_handles=["default"]))
NodeContractRegistry.register_contract(NodeContract(node_type="telegram_trigger", input_handles=[], output_handles=["default"], is_trigger=True))
NodeContractRegistry.register_contract(NodeContract(node_type="telegram_send", input_handles=["default"], output_handles=["default"]))

# Canonical snake_case names
NodeContractRegistry.register_contract(NodeContract(node_type="send_email", input_handles=["default"], output_handles=["default"]))
NodeContractRegistry.register_contract(NodeContract(node_type="read_excel", input_handles=["default"], output_handles=["default"]))
NodeContractRegistry.register_contract(NodeContract(node_type="read_email_imap", input_handles=["default"], output_handles=["default"]))

# Legacy aliases for backward compatibility with existing saved workflows
NodeContractRegistry.register_contract(NodeContract(node_type="send-email", input_handles=["default"], output_handles=["default"]))
NodeContractRegistry.register_contract(NodeContract(node_type="read-excel", input_handles=["default"], output_handles=["default"]))
NodeContractRegistry.register_contract(NodeContract(node_type="read-email-imap", input_handles=["default"], output_handles=["default"]))
NodeContractRegistry.register_contract(NodeContract(node_type="if_condition", input_handles=["default"], output_handles=["true", "false"]))

# Missing nodes
NodeContractRegistry.register_contract(NodeContract(node_type="custom_package_node", input_handles=["default"], output_handles=["default"]))
NodeContractRegistry.register_contract(NodeContract(node_type="webhook_trigger", input_handles=[], output_handles=["default"], is_trigger=True))
NodeContractRegistry.register_contract(NodeContract(node_type="schedule_trigger", input_handles=[], output_handles=["default"], is_trigger=True))
NodeContractRegistry.register_contract(NodeContract(node_type="slack_notification", input_handles=["default"], output_handles=["default"]))
NodeContractRegistry.register_contract(NodeContract(node_type="transform_json", input_handles=["default"], output_handles=["default"]))
NodeContractRegistry.register_contract(NodeContract(node_type="delay_timer", input_handles=["default"], output_handles=["default"]))
