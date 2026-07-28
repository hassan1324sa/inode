from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Dict, Any, List

class TriggerRequest(BaseModel):
    trigger_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)
    params: Dict[str, Any] = Field(default_factory=dict)

class ExecutionRequest(BaseModel):
    workflow_id: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    permissions: List[str] = Field(default_factory=list)

class BaseTrigger(ABC):
    id: str

    @abstractmethod
    async def validate(self, request: TriggerRequest) -> None:
        """
        Validates incoming trigger request. Raises ValueError if invalid.
        """
        pass

    @abstractmethod
    async def create_execution(self, request: TriggerRequest) -> ExecutionRequest:
        """
        Processes trigger request and creates a structured ExecutionRequest.
        """
        pass
