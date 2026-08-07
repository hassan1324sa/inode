import pytest
from httpx import AsyncClient
from app.core.execution.validation import GraphValidator, WorkflowValidationError
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from unittest.mock import AsyncMock

@pytest.mark.anyio
async def test_graph_validation_rules():
    # 1. Trigger missing
    nodes_no_trigger = [
        {"id": "node-1", "type": "ai_agent"},
        {"id": "node-2", "type": "send-email"}
    ]
    edges_no_trigger = [
        {"source": "node-1", "target": "node-2", "sourceHandle": "default", "targetHandle": "default"}
    ]
    with pytest.raises(WorkflowValidationError) as exc:
        GraphValidator.validate_graph(nodes_no_trigger, edges_no_trigger)
    assert any("Workflow must contain exactly one trigger node (none found)" in err for err in exc.value.errors)

    # 2. Duplicate node IDs
    nodes_dup = [
        {"id": "node-1", "type": "manual_trigger"},
        {"id": "node-2", "type": "ai_agent"},
        {"id": "node-2", "type": "send-email"}
    ]
    with pytest.raises(WorkflowValidationError) as exc:
        GraphValidator.validate_graph(nodes_dup, [])
    assert any("Duplicate node ID detected: node-2" in err for err in exc.value.errors)

    # 3. Edge source/target existence
    nodes_valid = [
        {"id": "node-trigger", "type": "manual_trigger"},
        {"id": "node-ai", "type": "ai_agent"}
    ]
    edges_invalid_target = [
        {"source": "node-trigger", "target": "non-existent", "sourceHandle": "default", "targetHandle": "default"}
    ]
    with pytest.raises(WorkflowValidationError) as exc:
        GraphValidator.validate_graph(nodes_valid, edges_invalid_target)
    assert any("Edge target 'non-existent' does not exist" in err for err in exc.value.errors)

    # 4. Invalid handle check
    edges_invalid_handle = [
        {"source": "node-trigger", "target": "node-ai", "sourceHandle": "invalid-handle", "targetHandle": "default"}
    ]
    with pytest.raises(WorkflowValidationError) as exc:
        GraphValidator.validate_graph(nodes_valid, edges_invalid_handle)
    assert any("Invalid output handle 'invalid-handle'" in err for err in exc.value.errors)

    # 5. Duplicate edge check
    nodes_dup_edges = [
        {"id": "node-trigger", "type": "manual_trigger"},
        {"id": "node-ai", "type": "ai_agent"}
    ]
    edges_dup = [
        {"source": "node-trigger", "target": "node-ai", "sourceHandle": "default", "targetHandle": "default"},
        {"source": "node-trigger", "target": "node-ai", "sourceHandle": "default", "targetHandle": "default"}
    ]
    with pytest.raises(WorkflowValidationError) as exc:
        GraphValidator.validate_graph(nodes_dup_edges, edges_dup)
    assert any("Duplicate edge detected" in err for err in exc.value.errors)

    # 6. Unreachable nodes
    nodes_unreachable = [
        {"id": "node-trigger", "type": "manual_trigger"},
        {"id": "node-ai", "type": "ai_agent"},
        {"id": "node-email", "type": "send-email"}
    ]
    edges_unreachable = [
        {"source": "node-trigger", "target": "node-ai", "sourceHandle": "default", "targetHandle": "default"}
    ]
    with pytest.raises(WorkflowValidationError) as exc:
        GraphValidator.validate_graph(nodes_unreachable, edges_unreachable)
    assert any("Node 'node-email' is unreachable from trigger" in err for err in exc.value.errors)

    # 7. Cycle check
    nodes_cycle = [
        {"id": "node-trigger", "type": "manual_trigger"},
        {"id": "node-a", "type": "ai_agent"},
        {"id": "node-b", "type": "send-email"}
    ]
    edges_cycle = [
        {"source": "node-trigger", "target": "node-a", "sourceHandle": "default", "targetHandle": "default"},
        {"source": "node-a", "target": "node-b", "sourceHandle": "default", "targetHandle": "default"},
        {"source": "node-b", "target": "node-a", "sourceHandle": "default", "targetHandle": "default"}
    ]
    with pytest.raises(WorkflowValidationError) as exc:
        GraphValidator.validate_graph(nodes_cycle, edges_cycle)
    assert any("Structural cycle detected" in err for err in exc.value.errors)


@pytest.mark.anyio
async def test_invalid_graph_does_not_start_temporal(client: AsyncClient, mock_execution_service):
    # Setup test user and org to get access token
    register_payload = {
        "email": "test-gate@example.com",
        "password": "securepassword",
        "name": "Gate Test User"
    }
    await client.post("/api/v1/auth/register", json=register_payload)
    resp_login = await client.post("/api/v1/auth/login", json={
        "email": "test-gate@example.com",
        "password": "securepassword"
    })
    token = resp_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create Workflow definition with unreachable node (invalid graph)
    wf_resp = await client.post("/api/v1/workflows/", json={
        "name": "Invalid Gate Workflow",
        "description": "Will fail validation"
    }, headers=headers)
    wf_id = wf_resp.json()["id"]

    # Insert an invalid version directly in DB
    # node-email is unreachable
    nodes = [
        {"id": "node-trigger", "type": "manual_trigger"},
        {"id": "node-ai", "type": "ai_agent"},
        {"id": "node-email", "type": "send-email"}
    ]
    edges = [
        {"source": "node-trigger", "target": "node-ai", "sourceHandle": "default", "targetHandle": "default"}
    ]
    
    # We update the workflow version definition with this invalid graph
    await client.put(f"/api/v1/workflows/{wf_id}", json={
        "nodes": nodes,
        "edges": edges
    }, headers=headers)

    # Reset mock execution service call history
    mock_execution_service.start_execution.reset_mock()

    # Trigger execution - should return 400
    exec_payload = {
        "trigger_type": "Manual",
        "inputs": {}
    }
    response = await client.post(f"/api/v1/workflows/{wf_id}/execute", json=exec_payload, headers=headers)
    assert response.status_code == 400
    assert "Unreachable nodes detected" in response.json()["message"]

    # CRITICAL: Prove Temporal client / start_execution was NEVER called
    mock_execution_service.start_execution.assert_not_called()
