from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
import time
from app.core.agents.context import AgentContext
from app.core.events.event_bus import ExecutionEventBus
from app.core.execution.events import ExecutionEvent

class PlanningPolicy(BaseModel):
    max_iterations: int = 10
    allow_parallel: bool = False
    require_approval: bool = False
    max_cost: float = 5.0
    preferred_tools: List[str] = Field(default_factory=list)

class PlanStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    thought: str
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    error: Optional[str] = None

class Plan(BaseModel):
    steps: List[PlanStep] = Field(default_factory=list)
    is_completed: bool = False
    final_answer: Optional[str] = None

class AgentKernel:
    """
    Coordinates Planner, PlanExecutor, ToolExecutor, Memory, and Knowledge components.
    The execution loop is decoupled from LLM API dependencies.
    """
    def __init__(
        self,
        planner: Any,
        tool_executor: Any,
        memory_layer: Any,
        knowledge_layer: Any,
        policy: Optional[PlanningPolicy] = None
    ):
        self.planner = planner
        self.tool_executor = tool_executor
        self.memory_layer = memory_layer
        self.knowledge_layer = knowledge_layer
        self.policy = policy or PlanningPolicy()
        self.accumulated_cost = 0.0

    async def run(self, goal: str, context: AgentContext) -> Dict[str, Any]:
        from app.core.agents.executor import PlanExecutor
        iterations = 0
        plan = Plan()
        
        # Publish start event
        await ExecutionEventBus.publish(
            ExecutionEvent(event_type="AgentStart", execution_id=context.session_id)
        )

        # Retrieve information from knowledge layer to augment working memory if available
        knowledge_context = ""
        if self.knowledge_layer:
            retrievals = await self.knowledge_layer.retrieve(goal)
            knowledge_context = "\n".join([r.content for r in retrievals])
            await self.memory_layer.working_memory.add_observation(
                f"Retrieved relevant knowledge: {knowledge_context}"
            )

        # Check if running inside a Temporal workflow
        import temporalio.workflow
        is_workflow = False
        try:
            temporalio.workflow.info()
            is_workflow = True
        except Exception:
            pass

        executor = PlanExecutor(tool_executor=self.tool_executor)

        while iterations < self.policy.max_iterations:
            if self.accumulated_cost >= self.policy.max_cost:
                await ExecutionEventBus.publish(
                    ExecutionEvent(event_type="AgentCostLimitExceeded", execution_id=context.session_id)
                )
                return {
                    "status": "failed",
                    "reason": "Cost budget exceeded",
                    "iterations": iterations,
                    "final_answer": None
                }

            iterations += 1
            
            # 1. Ask planner for the next action/step or complete plan (using activity if in workflow)
            if is_workflow:
                from datetime import timedelta
                from temporalio.common import RetryPolicy
                retry_policy = RetryPolicy(maximum_attempts=3)
                
                # Fetch working memory observations to serialize for planner activity
                observations = await self.memory_layer.working_memory.get_observations()
                planner_type = "react"
                planner_class_name = self.planner.__class__.__name__
                if "Sequential" in planner_class_name:
                    planner_type = "sequential"
                elif "Solve" in planner_class_name:
                    planner_type = "plan_and_solve"
                elif "Thought" in planner_class_name:
                    planner_type = "tree_of_thought"

                plan_dict = await temporalio.workflow.execute_activity(
                    "plan_activity",
                    {
                        "goal": goal,
                        "context": context.model_dump(),
                        "policy": self.policy.model_dump(),
                        "plan": plan.model_dump(),
                        "observations": observations,
                        "planner_type": planner_type
                    },
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=retry_policy
                )
                planner_response = Plan(**plan_dict)
            else:
                planner_response = await self.planner.plan(
                    goal=goal,
                    context=context,
                    memory_layer=self.memory_layer,
                    policy=self.policy,
                    current_plan=plan
                )
            
            # Track planner cost if any
            self.accumulated_cost += getattr(planner_response, "cost", 0.0)

            # Update working plan steps structure
            for step in planner_response.steps:
                # Add step if not already present
                if not any(s.step_id == step.step_id for s in plan.steps):
                    plan.steps.append(step)

            # If planner declares final solution
            if planner_response.is_completed or planner_response.final_answer:
                plan.is_completed = True
                plan.final_answer = planner_response.final_answer
                break

            # 2. Execute plan steps using PlanExecutor
            observations = await self.memory_layer.working_memory.get_observations()
            new_obs = await executor.execute_steps(plan, context, observations)
            for obs in new_obs:
                await self.memory_layer.working_memory.add_observation(obs)

            # Check if any step failed and policy does not allow parallel
            if any(s.status == "FAILED" for s in plan.steps):
                if not self.policy.allow_parallel:
                    break

        # Save session episodic memory
        if self.memory_layer:
            await self.memory_layer.save_episode(
                session_id=context.session_id,
                goal=goal,
                plan=plan,
                final_answer=plan.final_answer
            )

        # Publish end event
        await ExecutionEventBus.publish(
            ExecutionEvent(event_type="AgentEnd", execution_id=context.session_id)
        )

        return {
            "status": "completed" if plan.is_completed else "max_iterations",
            "iterations": iterations,
            "cost": self.accumulated_cost,
            "plan": plan.model_dump(),
            "final_answer": plan.final_answer
        }
