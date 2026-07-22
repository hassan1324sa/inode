from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class ExecutionContext(BaseModel):
    """
    Context passed during workflow execution.
    Tracks state, variables, and identifiers.
    """
    execution_id: str
    workflow_definition_id: str
    workflow_definition_version: int
    engine_version: int = 1
    schema_version: int = 1
    tenant_id: str
    variables: Dict[str, Any] = Field(default_factory=dict)
    node_outputs: Dict[str, Any] = Field(default_factory=dict)
    current_node_id: Optional[str] = None
    started_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_variable(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def set_variable(self, key: str, value: Any):
        self.variables[key] = value

    def set_node_output(self, node_id: str, output: Any):
        self.node_outputs[node_id] = output
