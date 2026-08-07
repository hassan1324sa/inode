import time
import uuid
import logging
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field
from fastapi import WebSocket, WebSocketDisconnect
from app.core.execution.events import ExecutionEvent
from app.core.events.event_bus import ExecutionEventBus
from app.core.execution.durable_store import MongoDBEventStore, ExecutionSnapshot

logger = logging.getLogger("fluxa.live_debug")

class VariableState(BaseModel):
    name: str
    value: Any
    node_id: str
    sequence: int
    timestamp: float = Field(default_factory=time.time)


class EventStore:
    """
    Durable Event Store adapter querying MongoDBEventStore.
    """
    @classmethod
    async def append_event(cls, event: ExecutionEvent) -> int:
        return await MongoDBEventStore.append_event(event)

    @classmethod
    async def get_events(cls, execution_id: str, since_sequence: int = 0) -> List[ExecutionEvent]:
        # Return converted events
        evs = await MongoDBEventStore.get_events(execution_id, since_sequence)
        return [ExecutionEvent(**e.model_dump()) for e in evs]

    @classmethod
    async def get_variable_value_at_step(cls, execution_id: str, variable_name: str, up_to_sequence: int) -> Any:
        events = await cls.get_events(execution_id)
        current_val = None
        for ev in events:
            if ev.sequence > up_to_sequence:
                break
            if ev.event_type == "VariableChanged" and ev.payload.get("variable_name") == variable_name:
                current_val = ev.payload.get("current_value")
        return current_val

    @classmethod
    async def save_snapshot(cls, snapshot: ExecutionSnapshot):
        await MongoDBEventStore.save_snapshot(snapshot)

    @classmethod
    async def get_snapshot(cls, execution_id: str) -> Optional[ExecutionSnapshot]:
        return await MongoDBEventStore.get_snapshot(execution_id)

    @classmethod
    def clear(cls):
        # Cleared in pytest fixture; in Mongo we do this per test or via drop
        pass


class LiveExecutionStreamManager:
    """
    Coordinates WebSocket subscriptions for execution events, respecting tenant isolation and auth.
    """
    _active_connections: Dict[str, Dict[WebSocket, str]] = {}  # execution_id -> {websocket: tenant_id}

    @classmethod
    async def initialize(cls):
        ExecutionEventBus.subscribe(cls.handle_bus_event)

    @classmethod
    async def handle_bus_event(cls, event: ExecutionEvent):
        # 1. Persistence first
        await EventStore.append_event(event)

        # 2. Broadcast second
        exec_id = event.execution_id
        if exec_id in cls._active_connections:
            dead_sockets = []
            for ws, conn_tenant_id in cls._active_connections[exec_id].items():
                # Enforce tenant isolation check: do not broadcast if tenant mismatch!
                if conn_tenant_id != event.tenant_id:
                    logger.warning(f"Cross-tenant event broadcast blocked! Socket tenant: {conn_tenant_id}, Event tenant: {event.tenant_id}")
                    continue
                try:
                    await ws.send_json(event.model_dump())
                except Exception:
                    dead_sockets.append(ws)
            for ds in dead_sockets:
                cls._active_connections[exec_id].pop(ds, None)

    @classmethod
    async def connect(
        self,
        websocket: WebSocket,
        execution_id: str,
        tenant_id: str,
        last_sequence: int = 0
    ) -> bool:
        # Verify tenant mismatch on catch-up events
        if last_sequence > 0:
            missed_events = await EventStore.get_events(execution_id, since_sequence=last_sequence)
            for me in missed_events:
                if me.tenant_id != tenant_id:
                    logger.warning("Cross-tenant access blocked on catchup query.")
                    return False
                await websocket.send_json(me.model_dump())

        if execution_id not in self._active_connections:
            self._active_connections[execution_id] = {}
            
        self._active_connections[execution_id][websocket] = tenant_id
        return True

    @classmethod
    def disconnect(self, websocket: WebSocket, execution_id: str):
        if execution_id in self._active_connections:
            self._active_connections[execution_id].pop(websocket, None)
            if not self._active_connections[execution_id]:
                del self._active_connections[execution_id]


class ReplayEngine:
    """
    Handles Temporal-safe workflow re-execution (Replay) and snapshot bootstrapping (Restart).
    """
    @classmethod
    async def trigger_restart(cls, execution_id: str, from_node_id: str, tenant_id: str) -> Dict[str, Any]:
        snapshot = await EventStore.get_snapshot(execution_id)
        if not snapshot:
            raise ValueError(f"Snapshot not found for execution {execution_id}")

        if snapshot.tenant_id != tenant_id:
            raise PermissionError("Access denied: tenant mismatch.")

        new_execution_id = f"restart-{uuid.uuid4()}"
        
        await ExecutionEventBus.publish(
            ExecutionEvent(
                execution_id=new_execution_id,
                workflow_id=snapshot.workflow_id,
                tenant_id=tenant_id,
                event_type="ExecutionRestarted",
                node_id=from_node_id,
                payload={
                    "original_execution_id": execution_id,
                    "variables": snapshot.variables,
                    "node_states": snapshot.node_states,
                    "agent_state": snapshot.agent_state
                }
            )
        )
        return {
            "status": "success",
            "new_execution_id": new_execution_id,
            "bootstrapped_from": from_node_id
        }

    @classmethod
    async def trigger_replay(cls, execution_id: str, tenant_id: str) -> Dict[str, Any]:
        events = await EventStore.get_events(execution_id)
        if not events:
            raise ValueError(f"No events found to replay for execution {execution_id}")

        replay_id = f"replay-{execution_id}"
        for ev in events:
            if ev.tenant_id != tenant_id:
                raise PermissionError("Access denied: tenant mismatch.")
                
            replay_ev = ev.model_copy()
            replay_ev.execution_id = replay_id
            replay_ev.event_id = str(uuid.uuid4())
            replay_ev.event_type = f"Replay:{ev.event_type}"
            await ExecutionEventBus.publish(replay_ev)

        return {
            "status": "success",
            "replay_execution_id": replay_id,
            "events_replayed": len(events)
        }


class DiffEngine:
    """
    Computes structural, status, and variable differences across execution states.
    """
    @classmethod
    def diff_executions(
        cls,
        snapshot_a: ExecutionSnapshot,
        snapshot_b: ExecutionSnapshot
    ) -> Dict[str, Any]:
        
        nodes_a = set(snapshot_a.node_states.keys())
        nodes_b = set(snapshot_b.node_states.keys())
        added_nodes = list(nodes_b - nodes_a)
        removed_nodes = list(nodes_a - nodes_b)

        status_diff = {}
        for node in nodes_a.intersection(nodes_b):
            st_a = snapshot_a.node_states[node]
            st_b = snapshot_b.node_states[node]
            if st_a != st_b:
                status_diff[node] = {"before": st_a, "after": st_b}

        var_diff = {}
        vars_a = set(snapshot_a.variables.keys())
        vars_b = set(snapshot_b.variables.keys())
        for var in vars_a.union(vars_b):
            val_a = snapshot_a.variables.get(var)
            val_b = snapshot_b.variables.get(var)
            if val_a != val_b:
                var_diff[var] = {"before": val_a, "after": val_b}

        return {
            "workflow_structure_diff": {
                "added_nodes": added_nodes,
                "removed_nodes": removed_nodes
            },
            "node_execution_diff": status_diff,
            "state_variable_diff": var_diff
        }
