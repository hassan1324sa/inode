import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.core.execution.events import ExecutionEvent
from app.core.events.event_bus import ExecutionEventBus
from app.core.execution.live_debug import LiveExecutionStreamManager, EventStore, ExecutionSnapshot, ReplayEngine, DiffEngine

@pytest.fixture(autouse=True)
async def clean_live_state():
    EventStore.clear()
    LiveExecutionStreamManager._active_connections.clear()
    await LiveExecutionStreamManager.initialize()
    yield
    EventStore.clear()
    LiveExecutionStreamManager._active_connections.clear()
    ExecutionEventBus.clear()


@pytest.mark.anyio
async def test_websocket_streaming_and_auth():
    client = TestClient(app)
    from app.core.security.jwt import create_access_token
    from fastapi.websockets import WebSocketDisconnect

    # 1. Invalid token -> connection close
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/debug/ws?execution_id=ex-1&tenant_id=t-1&token=invalid_token") as ws:
            pass
    assert exc_info.value.code == 1008

    # 2. Missing token -> connection close
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/debug/ws?execution_id=ex-1&tenant_id=t-1") as ws:
            pass
    assert exc_info.value.code == 1008

    # 3. Mismatched tenant ID -> connection close
    token_mismatch = create_access_token(user_id="u-1", organization_id="different-tenant")
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/debug/ws?execution_id=ex-1&tenant_id=t-1&token={token_mismatch}") as ws:
            pass
    assert exc_info.value.code == 1008

    # 4. Valid connection & Event broadcasting
    token_valid = create_access_token(user_id="u-1", organization_id="t-1")
    with client.websocket_connect(f"/api/v1/debug/ws?execution_id=ex-1&tenant_id=t-1&token={token_valid}") as ws:
        # Publish event on EventBus
        event = ExecutionEvent(
            execution_id="ex-1",
            workflow_id="wf-1",
            tenant_id="t-1",
            event_type="NodeStarted",
            node_id="node-a",
            payload={"message": "Node started successfully"}
        )
        await ExecutionEventBus.publish(event)
        
        # Receive event from WS
        received = ws.receive_json()
        assert received["execution_id"] == "ex-1"
        assert received["event_type"] == "NodeStarted"
        assert received["sequence"] == 1



@pytest.mark.anyio
async def test_reconnection_and_catchup():
    from app.core.security.jwt import create_access_token
    # Append events first
    event_1 = ExecutionEvent(execution_id="ex-2", workflow_id="wf-1", tenant_id="t-1", event_type="NodeStarted", node_id="node-a")
    event_2 = ExecutionEvent(execution_id="ex-2", workflow_id="wf-1", tenant_id="t-1", event_type="NodeCompleted", node_id="node-a")
    
    await EventStore.append_event(event_1)
    await EventStore.append_event(event_2)
    
    client = TestClient(app)
    # Connect requesting catch-up since sequence 1
    token = create_access_token(user_id="u-1", organization_id="t-1")
    with client.websocket_connect(f"/api/v1/debug/ws?execution_id=ex-2&tenant_id=t-1&last_sequence=1&token={token}") as ws:
        received = ws.receive_json()
        assert received["event_type"] == "NodeCompleted"
        assert received["sequence"] == 2


@pytest.mark.anyio
async def test_replay_and_restart():
    from app.core.security.jwt import create_access_token
    snapshot = ExecutionSnapshot(
        execution_id="ex-3",
        workflow_id="wf-1",
        tenant_id="t-1",
        variables={"count": 10, "status": "active"},
        node_states={"node-1": "Completed", "node-2": "Failed"},
        memory_context={"goal": "run task"},
        agent_state={"budget": 2.5}
    )
    await EventStore.save_snapshot(snapshot)

    # 1. Trigger Restart from node-2
    client = TestClient(app)
    token = create_access_token(user_id="u-1", organization_id="t-1")
    headers = {"Authorization": f"Bearer {token}"}
    res_restart = client.post("/api/v1/debug/executions/ex-3/restart?from_node_id=node-2&tenant_id=t-1", headers=headers)
    assert res_restart.status_code == 200
    data = res_restart.json()
    assert data["status"] == "success"
    assert data["bootstrapped_from"] == "node-2"
    assert data["new_execution_id"].startswith("restart-")

    # 2. Trigger Replay (simulate event bus replay)
    event = ExecutionEvent(execution_id="ex-3", workflow_id="wf-1", tenant_id="t-1", event_type="NodeStarted", node_id="node-1")
    await EventStore.append_event(event)

    res_replay = client.post("/api/v1/debug/executions/ex-3/replay?tenant_id=t-1", headers=headers)
    assert res_replay.status_code == 200
    replay_data = res_replay.json()
    assert replay_data["status"] == "success"
    assert replay_data["events_replayed"] == 1
    assert replay_data["replay_execution_id"] == "replay-ex-3"



@pytest.mark.anyio
async def test_variable_history_time_travel():
    # Simulate variable mutation sequence
    event_1 = ExecutionEvent(
        execution_id="ex-var",
        workflow_id="wf-1",
        tenant_id="t-1",
        event_type="VariableChanged",
        node_id="node-1",
        payload={"variable_name": "count", "previous_value": 0, "current_value": 5}
    )
    event_2 = ExecutionEvent(
        execution_id="ex-var",
        workflow_id="wf-1",
        tenant_id="t-1",
        event_type="VariableChanged",
        node_id="node-2",
        payload={"variable_name": "count", "previous_value": 5, "current_value": 15}
    )
    
    await EventStore.append_event(event_1)
    await EventStore.append_event(event_2)
    
    # Query count at sequence 1 (should be 5)
    val_seq_1 = await EventStore.get_variable_value_at_step("ex-var", "count", up_to_sequence=1)
    assert val_seq_1 == 5

    # Query count at sequence 2 (should be 15)
    val_seq_2 = await EventStore.get_variable_value_at_step("ex-var", "count", up_to_sequence=2)
    assert val_seq_2 == 15



@pytest.mark.anyio
async def test_diff_engine():
    snap_a = ExecutionSnapshot(
        execution_id="ex-a",
        workflow_id="wf-1",
        tenant_id="t-1",
        variables={"x": 10},
        node_states={"node-1": "Completed", "node-2": "Running"}
    )
    snap_b = ExecutionSnapshot(
        execution_id="ex-b",
        workflow_id="wf-1",
        tenant_id="t-1",
        variables={"x": 20},
        node_states={"node-1": "Completed", "node-2": "Completed", "node-3": "Pending"}
    )

    diff = DiffEngine.diff_executions(snap_a, snap_b)
    
    # Check structure changes
    assert diff["workflow_structure_diff"]["added_nodes"] == ["node-3"]
    # Check node status changes
    assert diff["node_execution_diff"]["node-2"] == {"before": "Running", "after": "Completed"}
    # Check variable values changes
    assert diff["state_variable_diff"]["x"] == {"before": 10, "after": 20}
