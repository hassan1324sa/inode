from typing import Any, Dict, List, Optional
import logging
from app.core.agents.kernel import Plan, PlanStep
from app.core.agents.context import AgentContext
from app.core.events.event_bus import ExecutionEventBus
from app.core.execution.events import ExecutionEvent

logger = logging.getLogger("fluxa.plan_executor")

class PlanExecutor:
    """
    Manages the lifecycle and execution of a Plan.
    Transitions steps through statuses: PLANNED -> VALIDATED -> RUNNING -> WAITING_FOR_TOOL -> OBSERVING -> COMPLETED / FAILED
    """
    def __init__(self, tool_executor: Any = None):
        self.tool_executor = tool_executor

    async def execute_steps(
        self,
        plan: Plan,
        context: AgentContext,
        observations: List[str]
    ) -> List[str]:
        """
        Executes pending steps.
        If running inside a Temporal workflow, calls 'execute_tool_activity'.
        Otherwise (e.g. local unit tests), executes tool directly.
        """
        import temporalio.workflow
        is_workflow = False
        try:
            temporalio.workflow.info()
            is_workflow = True
        except Exception:
            pass

        new_observations = []
        for step in plan.steps:
            if step.status == "pending" or step.status == "PLANNED":
                # Lifecycle: PLANNED -> VALIDATED -> RUNNING -> WAITING_FOR_TOOL -> OBSERVING -> COMPLETED/FAILED
                step.status = "VALIDATED"
                
                # Check for signal cancellation
                if is_workflow:
                    if temporalio.workflow.info().is_cancel_requested():
                        step.status = "FAILED"
                        step.error = "Temporal cancellation requested"
                        break

                step.status = "RUNNING"
                
                await ExecutionEventBus.publish(
                    ExecutionEvent(
                        event_type="AgentStepStart",
                        execution_id=context.session_id,
                        metadata={"step_id": step.step_id, "tool": step.tool_name}
                    )
                )

                step.status = "WAITING_FOR_TOOL"
                try:
                    if is_workflow:
                        # Schedule execute_tool_activity activity dynamically in workflow
                        from datetime import timedelta
                        from temporalio.common import RetryPolicy
                        retry_policy = RetryPolicy(maximum_attempts=3)
                        
                        execution_result = await temporalio.workflow.execute_activity(
                            "execute_tool_activity",
                            {
                                "tool_name": step.tool_name,
                                "args": step.args,
                                "context": context.model_dump()
                            },
                            start_to_close_timeout=timedelta(minutes=5),
                            retry_policy=retry_policy
                        )
                    else:
                        # Fallback for local unit tests (P3.1 allows direct tool run outside workflow context)
                        if self.tool_executor:
                            execution_result = await self.tool_executor.execute_tool(
                                tool_name=step.tool_name,
                                args=step.args,
                                context=context
                            )
                        else:
                            raise ValueError(f"No ToolExecutor configured to run: {step.tool_name}")

                    step.status = "OBSERVING"
                    step.status = "COMPLETED"
                    step.result = execution_result
                    
                    obs = f"Step {step.step_id} executed tool '{step.tool_name}' with args {step.args}. Result: {execution_result}"
                    new_observations.append(obs)
                    
                    await ExecutionEventBus.publish(
                        ExecutionEvent(
                            event_type="AgentStepCompleted",
                            execution_id=context.session_id,
                            metadata={"step_id": step.step_id, "status": "completed"}
                        )
                    )
                except Exception as e:
                    step.status = "FAILED"
                    step.error = str(e)
                    
                    obs = f"Step {step.step_id} executed tool '{step.tool_name}' failed. Error: {str(e)}"
                    new_observations.append(obs)
                    
                    await ExecutionEventBus.publish(
                        ExecutionEvent(
                            event_type="AgentStepFailed",
                            execution_id=context.session_id,
                            metadata={"step_id": step.step_id, "error": str(e)}
                        )
                    )
                    break
        return new_observations
