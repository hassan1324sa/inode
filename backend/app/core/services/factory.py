from pydantic import BaseModel, Field
from typing import Dict, Any

class ExecutionServices(BaseModel):
    services: Dict[str, Any] = Field(default_factory=dict)

class ExecutionServicesFactory:
    @classmethod
    def create_services(cls) -> ExecutionServices:
        return ExecutionServices()
