from datetime import timedelta
from temporalio import workflow
from typing import Dict, Any

with workflow.unsafe.imports_passed_through():
    from app.core.execution.context import ExecutionContext

@workflow.defn
class WorkflowOrchestrator:
    """
    A Temporal Workflow that orchestrates node execution.
    Contains strictly deterministic orchestration logic.
    """

    def __init__(self):
        self._paused = False

    @workflow.signal
    def pause_workflow(self) -> None:
        """
        Signal to pause the workflow execution.
        """
        self._paused = True

    @workflow.signal
    def resume_workflow(self) -> None:
        """
        Signal to resume workflow execution.
        """
        self._paused = False

    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        execution_id = input_data["execution_id"]
        nodes = input_data.get("nodes", [])

        # Load initial ExecutionContext via Activity
        context_dict = await workflow.execute_activity(
            "load_execution_context_activity",
            input_data,
            start_to_close_timeout=timedelta(seconds=15),
            task_queue="fluxa-core"
        )
        context = ExecutionContext(**context_dict)

        for node_def in nodes:
            # Wait if paused
            await workflow.wait_condition(lambda: not self._paused)

            # Check for cancellation before scheduling the activity
            # (Workflow run cancellation is handled natively by Temporal)
            
            # Select task queue based on node type
            node_type = node_def.get("type", "core")
            if node_type == "ai":
                task_queue = "fluxa-ai"
            elif node_type == "http":
                task_queue = "fluxa-http"
            else:
                task_queue = "fluxa-core"

            # Execute node activity
            context_dict = await workflow.execute_activity(
                "execute_node_activity",
                {
                    "node_def": node_def,
                    "context": context.model_dump()
                },
                start_to_close_timeout=timedelta(minutes=5),
                task_queue=task_queue
            )
            context = ExecutionContext(**context_dict)

        return context.model_dump()
