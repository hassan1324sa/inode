# Fluxa Agent Core Contracts Specification (Phase 8.1)

This document establishes the architecture, models, and boundaries for the Fluxa Agent Kernel.

---

## 1. Typed Conversation & State Models (`state.py` / `models.py`)
To avoid loose dictionary definitions and prepare for streaming, tool calls, and memory:

```python
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

class Message(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ToolInvocation(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    invocation_id: str

class Observation(BaseModel):
    invocation_id: str
    output: Any
    error: Optional[str] = None

class ConversationTurn(BaseModel):
    user_message: Message
    assistant_thought: Optional[str] = None
    tool_calls: List[ToolInvocation] = Field(default_factory=list)
    observations: List[Observation] = Field(default_factory=list)
    final_response: Optional[Message] = None

class AgentState(BaseModel):
    conversation: List[ConversationTurn] = Field(default_factory=list)
    variables: Dict[str, Any] = Field(default_factory=dict)
    current_step_index: int = 0
```

---

## 2. Plan & Step Execution Contracts (`plans.py` / `executor.py`)
The execution plan represents an abstract sequence of actions.

```python
from enum import Enum

class PlanStepStatus(str, Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    SKIPPED = "Skipped"
    CANCELLED = "Cancelled"

class PlanStep(BaseModel):
    step_id: str
    description: str
    tool_name: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    status: PlanStepStatus = PlanStepStatus.PENDING

class Plan(BaseModel):
    id: str
    planner: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    steps: List[PlanStep] = Field(default_factory=list)

    @property
    def is_completed(self) -> bool:
        return all(s.status == PlanStepStatus.COMPLETED for s in self.steps)
```

### Stateless PlanExecutor
The `PlanExecutor` evaluates single steps, returning updates without mutating context or state directly:

```python
class StepExecutionResult(BaseModel):
    outputs: Dict[str, Any] = Field(default_factory=dict)
    state_updates: Dict[str, Any] = Field(default_factory=dict)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    status: PlanStepStatus
```

---

## 3. Dependency Injection in AgentRuntime
`AgentRuntime` depends strictly on interfaces:

```python
class AgentRuntime(BaseRuntime):
    def __init__(
        self,
        planner: BasePlanner,
        executor: PlanExecutor,
        memory: Optional[BaseMemoryProvider] = None,
        knowledge: Optional[BaseKnowledgeProvider] = None,
        event_bus: Optional[ExecutionEventBus] = None
    ):
        self.planner = planner
        self.executor = executor
        self.memory = memory
        self.knowledge = knowledge
        self.event_bus = event_bus
```

---

## 4. Agent Lifecycle Events (`events.py`)
Events are dispatched through the `ExecutionEventBus` for live updates, tracking, and logs:
* `AgentStarted`
* `PlanningStarted`
* `PlanningCompleted`
* `StepStarted`
* `StepCompleted`
* `AgentCompleted`
* `AgentFailed`
