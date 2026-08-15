from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from typing import Dict, Any, List

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
        Signal to resume the workflow execution.
        """
        self._paused = False

    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        execution_id = input_data["execution_id"]
        try:
            nodes = input_data.get("nodes", [])

            # Load initial ExecutionContext via Activity
            context_dict = await workflow.execute_activity(
                "load_execution_context_activity",
                input_data,
                start_to_close_timeout=timedelta(seconds=15),
                task_queue="fluxa-core"
            )
            context = ExecutionContext(**context_dict)

            # Resolve mapping of node IDs for fast lookup
            node_map = {n.get("id"): n for n in nodes}
            edges = input_data.get("edges", [])

            # Build adjacency mapping supporting fan-out:
            # source_node_id -> source_handle -> list of Edge dicts (target, target_handle)
            adjacency: Dict[str, Dict[str, List[Dict[str, str]]]] = {}
            for edge in edges:
                src = edge.get("source")
                tgt = edge.get("target")
                src_h = edge.get("sourceHandle") or "default"
                tgt_h = edge.get("targetHandle") or "default"
                if not src or not tgt:
                    continue
                if src not in adjacency:
                    adjacency[src] = {}
                if src_h not in adjacency[src]:
                    adjacency[src][src_h] = []
                adjacency[src][src_h].append({
                    "target": tgt,
                    "targetHandle": tgt_h
                })

            # Determine starting node (trigger) dynamically without importing database-related registries
            KNOWN_TRIGGERS = {"manual_trigger", "telegram_trigger", "schedule_trigger", "schedule"}
            trigger_node = None
            for n in nodes:
                if n.get("type") in KNOWN_TRIGGERS:
                    trigger_node = n
                    break

            start_node_id = trigger_node.get("id") if trigger_node else (nodes[0].get("id") if nodes else None)
            
            # Traverse strictly using adjacency queue
            queue = [start_node_id] if start_node_id else []
            visited = set()

            # Retry policy for node activities
            retry_policy = RetryPolicy(
                initial_interval=timedelta(seconds=1),
                backoff_coefficient=2.0,
                maximum_attempts=3
            )

            while queue:
                # Wait if paused
                await workflow.wait_condition(lambda: not self._paused)
                
                current_node_id = queue.pop(0)
                if current_node_id in visited:
                    # Prevent infinite loops in cycle execution trace
                    continue
                visited.add(current_node_id)

                node_def = node_map.get(current_node_id)
                if not node_def:
                    continue

                node_id = node_def.get("id", "unknown")
                node_type = node_def.get("type", "core")
                
                # Select task queue based on node type
                if node_type == "ai":
                    task_queue = "fluxa-ai"
                elif node_type == "http":
                    task_queue = "fluxa-http"
                else:
                    task_queue = "fluxa-core"

                if node_type == "loop":
                    # P2.2: Resolve items in a lightweight, pure activity
                    items = await workflow.execute_activity(
                        "resolve_loop_items_activity",
                        {
                            "node_def": node_def,
                            "context": context.model_dump()
                        },
                        start_to_close_timeout=timedelta(minutes=5),
                        task_queue=task_queue
                    )
                    
                    # Enforce MAX_ITERATIONS count validation
                    if len(items) > 100:
                        raise ValueError(f"Loop iteration count {len(items)} exceeds safety threshold of 100.")
                    
                    loop_nodes = node_def.get("loop_nodes", [])
                    for idx, item in enumerate(items):
                        # Inject variables for this iteration
                        context.variables["current_row"] = item
                        context.variables["loop_index"] = idx
                        context.variables["last_condition_result"] = True
                        
                        # Execute each sub-node in the loop list
                        for sub_node in loop_nodes:
                            # Wait if paused
                            await workflow.wait_condition(lambda: not self._paused)
                            
                            # Respect skip checks (if_condition)
                            if_cond = sub_node.get("if_condition")
                            if if_cond == "variables.last_condition_result":
                                if not context.variables.get("last_condition_result", True):
                                    continue
                                    
                            sub_node_id = sub_node.get("id", "unknown")
                            sub_node_type = sub_node.get("type", "core")
                            
                            sub_queue = "fluxa-core"
                            if sub_node_type == "ai":
                                sub_queue = "fluxa-ai"
                            elif sub_node_type == "http":
                                sub_queue = "fluxa-http"
                                
                            # Run the child node as a real Temporal Activity with explicit RetryPolicy
                            context_dict = await workflow.execute_activity(
                                "execute_node_activity",
                                {
                                    "node_def": sub_node,
                                    "context": context.model_dump()
                                },
                                start_to_close_timeout=timedelta(minutes=5),
                                task_queue=sub_queue,
                                retry_policy=retry_policy
                            )
                            context = ExecutionContext(**context_dict)
                            
                            # Record execution trace
                            trace = context.variables.get("execution_trace", [])
                            trace.append(sub_node_id)
                            context.variables["execution_trace"] = trace
                else:
                    # Execute node activity
                    context_dict = await workflow.execute_activity(
                        "execute_node_activity",
                        {
                            "node_def": node_def,
                            "context": context.model_dump()
                        },
                        start_to_close_timeout=timedelta(minutes=5),
                        task_queue=task_queue,
                        retry_policy=retry_policy
                    )
                    context = ExecutionContext(**context_dict)
                    
                    # Record execution trace
                    trace = context.variables.get("execution_trace", [])
                    trace.append(node_id)
                    context.variables["execution_trace"] = trace

                # Determine the next node(s) using Adjacency Map
                last_output = context.node_outputs.get(node_id, {})
                output_handle = last_output.get("output_handle") or last_output.get("branch") or "default"
                
                next_edges = adjacency.get(node_id, {}).get(output_handle, [])
                for edge in next_edges:
                    target_id = edge["target"]
                    queue.append(target_id)

            await workflow.execute_activity(
                "complete_execution_activity",
                {"execution_id": execution_id, "status": "completed"},
                start_to_close_timeout=timedelta(seconds=15),
                task_queue="fluxa-core"
            )
            return context.model_dump()
        except Exception as exc:
            await workflow.execute_activity(
                "complete_execution_activity",
                {"execution_id": execution_id, "status": "failed", "error": str(exc)},
                start_to_close_timeout=timedelta(seconds=15),
                task_queue="fluxa-core"
            )
            raise exc
