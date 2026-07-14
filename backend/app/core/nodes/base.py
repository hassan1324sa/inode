from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class NodeContext(BaseModel):
    """
    Context passed between nodes during execution.
    Stores variables and state.
    """
    variables: Dict[str, Any] = Field(default_factory=dict)
    execution_id: str
    workflow_id: str
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)
        
    def set(self, key: str, value: Any):
        self.variables[key] = value

class BaseNode(BaseModel, ABC):
    """
    Abstract base class for all workflow nodes.
    """
    id: str
    name: str
    type: str
    
    @abstractmethod
    async def execute(self, context: NodeContext) -> NodeContext:
        """
        Execute the node logic. Must be implemented by subclasses.
        Returns the updated NodeContext.
        """
        pass
