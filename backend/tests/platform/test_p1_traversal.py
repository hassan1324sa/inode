import pytest
from app.core.execution.workflows import WorkflowOrchestrator
from app.core.execution.context import ExecutionContext

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
            node_type = node_def["type"]
            
            outputs = {}
            if node_type == "conditional":
                branch = node_def.get("mock_branch", "true")
                outputs = {"output_handle": branch, "branch": branch}
            else:
                outputs = {"output_handle": "default"}
                
            context_dict["node_outputs"][node_id] = outputs
            return context_dict

@pytest.fixture(autouse=True)
def mock_temporal_env(monkeypatch):
    async def mock_wait_condition(fn, *args, **kwargs):
        pass
    monkeypatch.setattr("temporalio.workflow.wait_condition", mock_wait_condition)

@pytest.mark.anyio
async def test_array_order_independence(monkeypatch):
    # 1. Define nodes in order [A, B, C]
    nodes_abc = [
        {"id": "node-trigger", "type": "manual_trigger"},
        {"id": "node-b", "type": "ai_agent"},
        {"id": "node-c", "type": "send-email"}
    ]
    edges = [
        {"source": "node-trigger", "target": "node-b", "sourceHandle": "default", "targetHandle": "default"},
        {"source": "node-b", "target": "node-c", "sourceHandle": "default", "targetHandle": "default"}
    ]
    
    input_abc = {
        "execution_id": "exec-abc",
        "workflow_definition_id": "wf-1",
        "tenant_id": "org-1",
        "nodes": nodes_abc,
        "edges": edges
    }

    orchestrator = WorkflowOrchestrator()
    mock_wf = MockWorkflow()
    monkeypatch.setattr("temporalio.workflow.execute_activity", mock_wf.execute_activity)
    
    result_abc = await orchestrator.run(input_abc)
    trace_abc = result_abc["variables"]["execution_trace"]
    assert trace_abc == ["node-trigger", "node-b", "node-c"]

    # 2. Define same nodes in shuffled order [C, trigger, B]
    nodes_cab = [
        {"id": "node-c", "type": "send-email"},
        {"id": "node-trigger", "type": "manual_trigger"},
        {"id": "node-b", "type": "ai_agent"}
    ]
    
    input_cab = {
        "execution_id": "exec-cab",
        "workflow_definition_id": "wf-1",
        "tenant_id": "org-1",
        "nodes": nodes_cab,
        "edges": edges
    }
    
    result_cab = await orchestrator.run(input_cab)
    trace_cab = result_cab["variables"]["execution_trace"]
    
    assert trace_cab == ["node-trigger", "node-b", "node-c"]


@pytest.mark.anyio
async def test_fan_out_execution(monkeypatch):
    nodes = [
        {"id": "node-trigger", "type": "manual_trigger"},
        {"id": "node-b", "type": "ai_agent"},
        {"id": "node-c", "type": "send-email"}
    ]
    edges = [
        {"source": "node-trigger", "target": "node-b", "sourceHandle": "default", "targetHandle": "default"},
        {"source": "node-trigger", "target": "node-c", "sourceHandle": "default", "targetHandle": "default"}
    ]
    
    input_data = {
        "execution_id": "exec-fanout",
        "workflow_definition_id": "wf-fan",
        "tenant_id": "org-1",
        "nodes": nodes,
        "edges": edges
    }

    orchestrator = WorkflowOrchestrator()
    mock_wf = MockWorkflow()
    monkeypatch.setattr("temporalio.workflow.execute_activity", mock_wf.execute_activity)
    
    result = await orchestrator.run(input_data)
    trace = result["variables"]["execution_trace"]
    
    assert "node-trigger" == trace[0]
    assert "node-b" in trace[1:]
    assert "node-c" in trace[1:]
    assert len(trace) == 3


@pytest.mark.anyio
async def test_conditional_routing(monkeypatch):
    nodes = [
        {"id": "node-trigger", "type": "manual_trigger"},
        {"id": "node-cond", "type": "conditional", "mock_branch": "true"},
        {"id": "node-true-branch", "type": "ai_agent"},
        {"id": "node-false-branch", "type": "send-email"}
    ]
    edges = [
        {"source": "node-trigger", "target": "node-cond", "sourceHandle": "default", "targetHandle": "default"},
        {"source": "node-cond", "target": "node-true-branch", "sourceHandle": "true", "targetHandle": "default"},
        {"source": "node-cond", "target": "node-false-branch", "sourceHandle": "false", "targetHandle": "default"}
    ]
    
    input_true = {
        "execution_id": "exec-cond-true",
        "workflow_definition_id": "wf-cond",
        "tenant_id": "org-1",
        "nodes": nodes,
        "edges": edges
    }

    orchestrator = WorkflowOrchestrator()
    mock_wf = MockWorkflow()
    monkeypatch.setattr("temporalio.workflow.execute_activity", mock_wf.execute_activity)
    
    result_true = await orchestrator.run(input_true)
    trace_true = result_true["variables"]["execution_trace"]
    assert "node-true-branch" in trace_true
    assert "node-false-branch" not in trace_true

    nodes_false = [
        {"id": "node-trigger", "type": "manual_trigger"},
        {"id": "node-cond", "type": "conditional", "mock_branch": "false"},
        {"id": "node-true-branch", "type": "ai_agent"},
        {"id": "node-false-branch", "type": "send-email"}
    ]
    input_false = {
        "execution_id": "exec-cond-false",
        "workflow_definition_id": "wf-cond",
        "tenant_id": "org-1",
        "nodes": nodes_false,
        "edges": edges
    }
    
    result_false = await orchestrator.run(input_false)
    trace_false = result_false["variables"]["execution_trace"]
    assert "node-false-branch" in trace_false
    assert "node-true-branch" not in trace_false
