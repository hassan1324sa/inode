import pytest
from app.core.execution.workflows import WorkflowOrchestrator
from app.core.execution.context import ExecutionContext
from app.core.nodes.implementations.loop import LoopNodeExecutor

class MockWorkflow:
    def __init__(self, names_list, execute_callback=None):
        self._paused = False
        self.names_list = names_list
        self.execute_callback = execute_callback

    async def wait_condition(self, fn):
        pass

    async def execute_activity(self, name, input_data, **kwargs):
        if name == "load_execution_context_activity":
            return {
                "execution_id": input_data["execution_id"],
                "workflow_definition_id": input_data["workflow_definition_id"],
                "workflow_definition_version": 1,
                "tenant_id": input_data["tenant_id"],
                "variables": {"names": self.names_list},
                "node_outputs": {}
            }
        
        if name == "resolve_loop_items_activity":
            if self.execute_callback:
                self.execute_callback(name, input_data)
            return self.names_list

        if name == "execute_node_activity":
            node_def = input_data["node_def"]
            node_id = node_def["id"]
            if self.execute_callback:
                self.execute_callback(name, input_data)
            context_dict = input_data["context"]
            context_dict["node_outputs"][node_id] = {"output_handle": "default"}
            return context_dict

@pytest.fixture(autouse=True)
def mock_temporal_env(monkeypatch):
    async def mock_wait_condition(fn, *args, **kwargs):
        pass
    monkeypatch.setattr("temporalio.workflow.wait_condition", mock_wait_condition)

@pytest.mark.anyio
async def test_loop_children_are_temporal_activities(monkeypatch):
    # 1. Define nodes and edges
    nodes = [
        {"id": "node-trigger", "type": "manual_trigger"},
        {
            "id": "loop-1",
            "type": "loop",
            "items_var": "names",
            "loop_nodes": [
                {"id": "loop-child-1", "type": "ai_agent"}
            ]
        }
    ]
    edges = [
        {"source": "node-trigger", "target": "loop-1", "sourceHandle": "default", "targetHandle": "default"}
    ]
    
    called_activities = []
    def track_activity(name, data):
        if name == "execute_node_activity":
            called_activities.append(f"execute_node_activity:{data['node_def']['id']}")
        else:
            called_activities.append(name)
            
    mock_wf = MockWorkflow(["Ahmed", "Ali"], track_activity)
    monkeypatch.setattr("temporalio.workflow.execute_activity", mock_wf.execute_activity)
    
    orchestrator = WorkflowOrchestrator()
    input_data = {
        "execution_id": "test-exec",
        "workflow_definition_id": "wf-1",
        "tenant_id": "org-1",
        "nodes": nodes,
        "edges": edges
    }
    
    result = await orchestrator.run(input_data)
    
    # Assert each child execution in the loop triggered a separate execute_node_activity Temporal activity call!
    assert "resolve_loop_items_activity" in called_activities
    assert called_activities.count("execute_node_activity:loop-child-1") == 2
    
    trace = result["variables"]["execution_trace"]
    assert trace == ["node-trigger", "loop-child-1", "loop-child-1"]


@pytest.mark.anyio
async def test_loop_max_iterations(monkeypatch):
    nodes = [
        {"id": "node-trigger", "type": "manual_trigger"},
        {
            "id": "loop-1",
            "type": "loop",
            "items_var": "names",
            "loop_nodes": [
                {"id": "loop-child-1", "type": "ai_agent"}
            ]
        }
    ]
    edges = [
        {"source": "node-trigger", "target": "loop-1", "sourceHandle": "default", "targetHandle": "default"}
    ]
    
    items_list = ["item"] * 101
    mock_wf = MockWorkflow(items_list)
    monkeypatch.setattr("temporalio.workflow.execute_activity", mock_wf.execute_activity)
    
    orchestrator = WorkflowOrchestrator()
    input_data = {
        "execution_id": "test-exec",
        "workflow_definition_id": "wf-1",
        "tenant_id": "org-1",
        "nodes": nodes,
        "edges": edges
    }
    
    with pytest.raises(ValueError) as exc:
        await orchestrator.run(input_data)
    assert "exceeds safety threshold of 100" in str(exc.value)


@pytest.mark.anyio
async def test_empty_loop(monkeypatch):
    nodes = [
        {"id": "node-trigger", "type": "manual_trigger"},
        {
            "id": "loop-1",
            "type": "loop",
            "items_var": "names",
            "loop_nodes": [
                {"id": "loop-child-1", "type": "ai_agent"}
            ]
        }
    ]
    edges = [
        {"source": "node-trigger", "target": "loop-1", "sourceHandle": "default", "targetHandle": "default"}
    ]
    
    mock_wf = MockWorkflow([])
    monkeypatch.setattr("temporalio.workflow.execute_activity", mock_wf.execute_activity)
    
    orchestrator = WorkflowOrchestrator()
    input_data = {
        "execution_id": "test-exec",
        "workflow_definition_id": "wf-1",
        "tenant_id": "org-1",
        "nodes": nodes,
        "edges": edges
    }
    
    result = await orchestrator.run(input_data)
    trace = result["variables"]["execution_trace"]
    assert trace == ["node-trigger"]


@pytest.mark.anyio
async def test_loop_executor_contract():
    executor = LoopNodeExecutor()
    result = await executor.execute({}, ExecutionContext(
        execution_id="test", workflow_definition_id="test",
        workflow_definition_version=1,
        tenant_id="test"
    ))
    assert result is not None


@pytest.mark.anyio
async def test_retry_side_effect_idempotency(monkeypatch):
    # Mock SMTP object
    class MockSMTP:
        sendmail_count = 0
        def __init__(self, *args, **kwargs):
            pass
        def login(self, *args, **kwargs):
            pass
        def sendmail(self, *args, **kwargs):
            MockSMTP.sendmail_count += 1
        def quit(self):
            pass

    import smtplib
    monkeypatch.setattr(smtplib, "SMTP", MockSMTP)
    
    # Initialize execution context with a unique execution_id
    execution_id = "test-durability-retry-idemp-1"
    
    from app.core.execution.context import ExecutionContext
    from app.core.nodes.implementations.send_email import SendEmailNodeExecutor
    from app.core.execution.durable_store import MongoDBEventStore
    from app.core.database import db_manager
    
    # Clear any leftover effects for clean test run
    await db_manager.db["execution_effects"].delete_many({"execution_id": execution_id})
    
    context = ExecutionContext(
        execution_id=execution_id,
        workflow_definition_id="wf-test",
        workflow_definition_version=1,
        tenant_id="tenant-a",
        variables={"current_row": {"email": "ahmed@example.com", "name": "Ahmed"}}
    )
    
    node_data = {
        "id": "email-node-1",
        "type": "send_email",
        "recipient": "current_row.email",
        "subject": "Hello Test",
        "body": "Hi {{current_row.name}}",
        "username": "test_user"
    }
    
    executor = SendEmailNodeExecutor()
    
    # 1. Run First Attempt (Succeeds sending SMTP but suppose a crash happens before workflow state registers response)
    # The executor runs and sends the email
    context = await executor.execute(node_data, context)
    assert MockSMTP.sendmail_count == 1
    
    # Verify effect is written in DB
    effect = await db_manager.db["execution_effects"].find_one({"execution_id": execution_id})
    assert effect is not None
    
    # Reset smtp count to 0
    MockSMTP.sendmail_count = 0
    
    # 2. Run Second Attempt (Temporal retries the activity because of the failure)
    # The executor runs again with same context/execution_id. It should load the cached effect and NOT send email again.
    retry_context = ExecutionContext(
        execution_id=execution_id,
        workflow_definition_id="wf-test",
        workflow_definition_version=1,
        tenant_id="tenant-a",
        variables={"current_row": {"email": "ahmed@example.com", "name": "Ahmed"}}
    )
    
    retry_context = await executor.execute(node_data, retry_context)
    
    # Assert sendmail count remains 0 (idempotency key matching prevents duplicate side effect!)
    assert MockSMTP.sendmail_count == 0

