import os
import json
import asyncio
from app.core.execution.workflows import WorkflowOrchestrator
from app.core.execution.context import ExecutionContext

# Mock Temporal and Activity execution for testing
class MockWorkflow:
    def __init__(self):
        self._paused = False

    async def wait_condition(self, fn):
        pass

    async def execute_activity(self, name, input_data, **kwargs):
        if name == "load_execution_context_activity":
            return {
                "execution_id": input_data["execution_id"],
                "workflow_definition_id": input_data["workflow_definition_id"],
                "workflow_definition_version": 1,
                "tenant_id": input_data["tenant_id"],
                "variables": {},
                "node_outputs": {}
            }
        if name == "execute_node_activity":
            node_def = input_data["node_def"]
            context_dict = input_data["context"]
            node_id = node_def["id"]
            context_dict["node_outputs"][node_id] = {"output_handle": "default"}
            return context_dict

async def main():
    evidence_dir = "Evidence/P1-graph"
    os.makedirs(evidence_dir, exist_ok=True)

    orchestrator = WorkflowOrchestrator()
    mock_wf = MockWorkflow()
    
    # Mock temporal dependencies
    import temporalio.workflow
    temporalio.workflow.execute_activity = mock_wf.execute_activity
    temporalio.workflow.wait_condition = mock_wf.wait_condition

    # 1. Linear Edge Execution
    nodes_linear = [
        {"id": "node-trigger", "type": "manual_trigger"},
        {"id": "node-b", "type": "ai_agent"},
        {"id": "node-c", "type": "send-email"}
    ]
    edges_linear = [
        {"source": "node-trigger", "target": "node-b", "sourceHandle": "default", "targetHandle": "default"},
        {"source": "node-b", "target": "node-c", "sourceHandle": "default", "targetHandle": "default"}
    ]
    input_linear = {
        "execution_id": "exec-linear",
        "workflow_definition_id": "wf-linear",
        "tenant_id": "org-1",
        "nodes": nodes_linear,
        "edges": edges_linear
    }
    res_linear = await orchestrator.run(input_linear)
    trace_linear = res_linear["variables"]["execution_trace"]
    
    with open(f"{evidence_dir}/linear-edge-execution.json", "w", encoding="utf-8") as f:
        json.dump({
            "nodes_input_order": [n["id"] for n in nodes_linear],
            "edges": edges_linear,
            "actual_execution_trace": trace_linear
        }, f, indent=2)

    # 2. Array Order Independence (input order shuffled)
    nodes_shuffled = [
        {"id": "node-c", "type": "send-email"},
        {"id": "node-trigger", "type": "manual_trigger"},
        {"id": "node-b", "type": "ai_agent"}
    ]
    input_shuffled = {
        "execution_id": "exec-shuffled",
        "workflow_definition_id": "wf-linear",
        "tenant_id": "org-1",
        "nodes": nodes_shuffled,
        "edges": edges_linear
    }
    res_shuffled = await orchestrator.run(input_shuffled)
    trace_shuffled = res_shuffled["variables"]["execution_trace"]
    
    with open(f"{evidence_dir}/array-order-independence.json", "w", encoding="utf-8") as f:
        json.dump({
            "nodes_input_order": [n["id"] for n in nodes_shuffled],
            "edges": edges_linear,
            "actual_execution_trace": trace_shuffled
        }, f, indent=2)

    # 3. Fan-out Execution
    nodes_fan = [
        {"id": "node-trigger", "type": "manual_trigger"},
        {"id": "node-b", "type": "ai_agent"},
        {"id": "node-c", "type": "send-email"}
    ]
    edges_fan = [
        {"source": "node-trigger", "target": "node-b", "sourceHandle": "default", "targetHandle": "default"},
        {"source": "node-trigger", "target": "node-c", "sourceHandle": "default", "targetHandle": "default"}
    ]
    input_fan = {
        "execution_id": "exec-fanout",
        "workflow_definition_id": "wf-fan",
        "tenant_id": "org-1",
        "nodes": nodes_fan,
        "edges": edges_fan
    }
    res_fan = await orchestrator.run(input_fan)
    trace_fan = res_fan["variables"]["execution_trace"]
    
    with open(f"{evidence_dir}/fan-out-execution.json", "w", encoding="utf-8") as f:
        json.dump({
            "nodes_input_order": [n["id"] for n in nodes_fan],
            "edges": edges_fan,
            "actual_execution_trace": trace_fan
        }, f, indent=2)

    print("P1 Traversal evidence successfully generated.")

if __name__ == "__main__":
    asyncio.run(main())
