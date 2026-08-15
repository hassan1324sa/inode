import logging
from app.core.execution.temporal_client import TemporalClientWrapper
from app.core.execution.workflows import WorkflowOrchestrator
from typing import List, Dict, Any

logger = logging.getLogger("fluxa.execution_service")

class ExecutionService:
    """
    Service layer to abstract Temporal workflow orchestrations.
    """

    def __init__(self):
        self.client_wrapper = TemporalClientWrapper()

    async def start_execution(
        self,
        execution_id: str,
        workflow_definition_id: str,
        tenant_id: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]] = None
    ) -> str:
        try:
            client = await self.client_wrapper.get_client()
            
            input_data = {
                "execution_id": execution_id,
                "workflow_definition_id": workflow_definition_id,
                "tenant_id": tenant_id,
                "nodes": nodes,
                "edges": edges or []
            }
            
            logger.info(f"Triggering Temporal workflow for execution: {execution_id}")
            handle = await client.start_workflow(
                WorkflowOrchestrator.run,
                input_data,
                id=execution_id,
                task_queue="fluxa-core"
            )
            return handle.run_id
        except Exception as e:
            logger.warning(f"Temporal client connection failed: {e}. Falling back to local synchronous execution background task.")
            import asyncio
            asyncio.create_task(self._run_local_execution(execution_id, workflow_definition_id, tenant_id, nodes, edges))
            return "local-execution-id"

    async def _run_local_execution(
        self,
        execution_id: str,
        workflow_definition_id: str,
        tenant_id: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ):
        from app.models.execution import Execution
        from app.models.enums import ExecutionStatus
        from app.core.execution.activities import load_execution_context_activity, execute_node_activity
        from datetime import datetime, timezone
        from bson import ObjectId

        # 1. Update execution status to RUNNING
        exec_obj = await Execution.get(ObjectId(execution_id))
        if exec_obj:
            exec_obj.status = ExecutionStatus.RUNNING
            exec_obj.started_at = datetime.now(timezone.utc).isoformat()
            await exec_obj.save()

        try:
            # 2. Load context
            input_data = {
                "execution_id": execution_id,
                "workflow_definition_id": workflow_definition_id,
                "tenant_id": tenant_id,
                "nodes": nodes,
                "edges": edges or []
            }
            context_dict = await load_execution_context_activity(input_data)
            
            # Resolve trigger node and build adjacency
            node_map = {n.get("id"): n for n in nodes}
            adjacency = {}
            for edge in (edges or []):
                src = edge.get("source")
                tgt = edge.get("target")
                src_h = edge.get("sourceHandle") or "default"
                if src and tgt:
                    if src not in adjacency:
                        adjacency[src] = {}
                    if src_h not in adjacency[src]:
                        adjacency[src][src_h] = []
                    adjacency[src][src_h].append(tgt)

            from app.core.nodes.registry import TriggerRegistry
            trigger_node = None
            for n in nodes:
                if TriggerRegistry.is_trigger(n.get("type")):
                    trigger_node = n
                    break
            
            start_node_id = trigger_node.get("id") if trigger_node else (nodes[0].get("id") if nodes else None)
            queue = [start_node_id] if start_node_id else []
            visited = set()

            while queue:
                current_node_id = queue.pop(0)
                if current_node_id in visited:
                    continue
                visited.add(current_node_id)

                node_def = node_map.get(current_node_id)
                if not node_def:
                    continue

                # Run execute node activity
                act_input = {
                    "node_def": node_def,
                    "context": context_dict
                }
                
                result_dict = await execute_node_activity(act_input)
                
                # Merge outputs into context variables/outputs
                node_outputs = result_dict.get("node_outputs", {})
                context_dict["node_outputs"].update(node_outputs)
                
                if current_node_id in node_outputs:
                    context_dict["variables"].update(node_outputs[current_node_id])

                # Get downstream targets
                targets = []
                if current_node_id in adjacency:
                    for handle, tgt_list in adjacency[current_node_id].items():
                        targets.extend(tgt_list)
                
                for tgt in targets:
                    if tgt not in visited:
                        queue.append(tgt)

            # 3. Update execution status to COMPLETED
            exec_obj = await Execution.get(ObjectId(execution_id))
            if exec_obj:
                exec_obj.status = ExecutionStatus.COMPLETED
                exec_obj.completed_at = datetime.now(timezone.utc).isoformat()
                await exec_obj.save()

        except Exception as e:
            logger.error(f"Local workflow execution failed: {e}", exc_info=True)
            exec_obj = await Execution.get(ObjectId(execution_id))
            if exec_obj:
                exec_obj.status = ExecutionStatus.FAILED
                exec_obj.error = str(e)
                await exec_obj.save()

    async def pause_execution(self, execution_id: str):
        client = await self.client_wrapper.get_client()
        logger.info(f"Sending pause signal to execution: {execution_id}")
        handle = client.get_workflow_handle(execution_id)
        await handle.signal(WorkflowOrchestrator.pause_workflow)

    async def resume_execution(self, execution_id: str):
        client = await self.client_wrapper.get_client()
        logger.info(f"Sending resume signal to execution: {execution_id}")
        handle = client.get_workflow_handle(execution_id)
        await handle.signal(WorkflowOrchestrator.resume_workflow)

    async def cancel_execution(self, execution_id: str):
        client = await self.client_wrapper.get_client()
        logger.info(f"Cancelling execution: {execution_id}")
        handle = client.get_workflow_handle(execution_id)
        await handle.cancel()

    async def terminate_execution(self, execution_id: str, reason: str = "Terminated by user"):
        client = await self.client_wrapper.get_client()
        logger.info(f"Terminating execution: {execution_id} due to: {reason}")
        handle = client.get_workflow_handle(execution_id)
        await handle.terminate(reason=reason)
