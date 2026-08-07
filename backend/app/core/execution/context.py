from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from enum import Enum

class ExecutionStatus(str, Enum):
    COMPLETED = "Completed"
    FAILED = "Failed"
    RUNNING = "Running"
    PENDING = "Pending"

class ExecutionState(BaseModel):
    status: ExecutionStatus = ExecutionStatus.RUNNING
    step_index: int = 0
    history: List[Dict[str, Any]] = Field(default_factory=list)

class NodeExecutionResult(BaseModel):
    status: ExecutionStatus = ExecutionStatus.COMPLETED
    outputs: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

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
    correlation_id: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    node_outputs: Dict[str, Any] = Field(default_factory=dict)
    current_node_id: Optional[str] = None
    started_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    permissions: List[str] = Field(default_factory=list)

    def get_variable(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def set_variable(self, key: str, value: Any):
        self.variables[key] = value

    def set_node_output(self, node_id: str, output: Any):
        self.node_outputs[node_id] = output

