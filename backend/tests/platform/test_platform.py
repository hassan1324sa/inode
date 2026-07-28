import pytest
import asyncio
from unittest.mock import MagicMock
from app.core.registry.node_registry import NodeRegistry, NodeManifest, NodeCapabilities
from app.core.registry.provider_registry import ProviderRegistry, ProviderMetadata
from app.core.registry.trigger_registry import TriggerRegistry
from app.core.triggers.base import TriggerRequest
from app.core.triggers.implementations import WebhookTrigger, ScheduleTrigger
from app.core.execution.permissions import PolicyEngine
from app.core.execution.context import ExecutionContext, ExecutionState, NodeExecutionResult
from app.core.execution.middleware.permissions import PermissionMiddleware
from app.core.execution.errors import PermanentError
from app.core.events.event_bus import ExecutionEventBus
from app.core.execution.events import ExecutionEvent
from app.core.compiler.models import CompiledNode
from app.core.services.factory import ExecutionServicesFactory

# Mock BaseNodeExecutor subclass for registry tests
from app.core.nodes.node_executor import BaseNodeExecutor

class MockNodeExecutor(BaseNodeExecutor):
    async def execute(self, node_data, context, state, services):
        return NodeExecutionResult()

# Ensure clean state for registries before each test
@pytest.fixture(autouse=True)
def clean_registries():
    NodeRegistry.clear()
    ProviderRegistry.clear()
    TriggerRegistry.clear()
    ExecutionEventBus.clear()
    yield

# --- REGISTRY TESTS ---

def test_duplicate_manifest_registration():
    manifest1 = NodeManifest(
        id="test_node",
        version="1.0",
        author="test",
        category="custom",
        capabilities=NodeCapabilities(supports_retry=True),
        inputs={},
        outputs={}
    )
    manifest2 = NodeManifest(
        id="test_node",
        version="1.0",
        author="test2",
        category="custom",
        capabilities=NodeCapabilities(supports_retry=False),
        inputs={},
        outputs={}
    )
    
    NodeRegistry.register(manifest1, MockNodeExecutor)
    with pytest.raises(ValueError, match="Duplicate node registration detected"):
        NodeRegistry.register(manifest2, MockNodeExecutor)

def test_search_by_category():
    manifest_ai = NodeManifest(
        id="ai_node",
        version="1.0",
        author="author",
        category="ai",
        capabilities=NodeCapabilities(),
        inputs={},
        outputs={}
    )
    manifest_http = NodeManifest(
        id="http_node",
        version="1.0",
        author="author",
        category="network",
        capabilities=NodeCapabilities(),
        inputs={},
        outputs={}
    )
    NodeRegistry.register(manifest_ai, MockNodeExecutor)
    NodeRegistry.register(manifest_http, MockNodeExecutor)
    
    ai_manifests = NodeRegistry.list_manifests(category="ai")
    assert len(ai_manifests) == 1
    assert ai_manifests[0].id == "ai_node"

# --- PERMISSION TESTS ---

def test_wildcard_permission():
    # Grant list
    granted = ["network:*", "llm:invoke", "file:read"]
    
    # Matching checks
    assert PolicyEngine.is_allowed(["network:http"], granted) is True
    assert PolicyEngine.is_allowed(["network:https"], granted) is True
    assert PolicyEngine.is_allowed(["llm:invoke"], granted) is True
    
    # Mismatch checks
    assert PolicyEngine.is_allowed(["file:write"], granted) is False
    assert PolicyEngine.is_allowed(["database:read"], granted) is False

@pytest.mark.anyio
async def test_permission_middleware_blocking():
    # Register node requiring specific permissions
    manifest = NodeManifest(
        id="restricted_node",
        version="1.0",
        author="author",
        category="test",
        capabilities=NodeCapabilities(),
        inputs={},
        outputs={},
        permissions=["network:http"]
    )
    NodeRegistry.register(manifest, MockNodeExecutor)
    
    # 1. Deny case (ExecutionContext lacks permission)
    ctx_deny = ExecutionContext(
        execution_id="ex1",
        workflow_definition_id="wf1",
        workflow_definition_version=1,
        tenant_id="tenant1",
        permissions=["file:read"]
    )
    node = CompiledNode(id="n1", name="Restricted", type="restricted_node", data={})
    state = ExecutionState()
    services = ExecutionServicesFactory.create_services()
    
    middleware = PermissionMiddleware()
    
    async def dummy_next():
        return NodeExecutionResult()
        
    with pytest.raises(PermanentError, match="execution denied"):
        await middleware.execute(node, ctx_deny, state, services, dummy_next)

    # 2. Allow case (ExecutionContext has correct permission)
    ctx_allow = ExecutionContext(
        execution_id="ex2",
        workflow_definition_id="wf1",
        workflow_definition_version=1,
        tenant_id="tenant1",
        permissions=["network:http"]
    )
    result = await middleware.execute(node, ctx_allow, state, services, dummy_next)
    assert result.status.value == "Completed"

# --- TRIGGER TESTS ---

@pytest.mark.anyio
async def test_trigger_creates_execution_request():
    trigger = WebhookTrigger(id="trig_web", workflow_id="wf_target")
    req = TriggerRequest(trigger_id="trig_web", payload={"foo": "bar"})
    
    # Validation should succeed
    await trigger.validate(req)
    
    exec_req = await trigger.create_execution(req)
    assert exec_req.workflow_id == "wf_target"
    assert exec_req.input_data["foo"] == "bar"

@pytest.mark.anyio
async def test_schedule_validation():
    trigger_valid = ScheduleTrigger(id="trig_sch", cron="0 0 * * *", workflow_id="wf_target")
    req = TriggerRequest(trigger_id="trig_sch", payload={"scheduled_at": "2026-07-29T00:00:00Z"})
    
    # Valid cron works
    await trigger_valid.validate(req)
    
    # Invalid cron fails
    trigger_invalid = ScheduleTrigger(id="trig_sch_fail", cron="* * *", workflow_id="wf_target")
    with pytest.raises(ValueError, match="Invalid cron expression"):
        await trigger_invalid.validate(req)

# --- EVENT BUS TESTS ---

@pytest.mark.anyio
async def test_async_subscribers():
    bus_event = ExecutionEvent(event_type="TestEvent", execution_id="ex_bus")
    received_events = []
    
    async def sub1(event):
        await asyncio.sleep(0.01)
        received_events.append(("sub1", event.execution_id))
        
    async def sub2(event):
        await asyncio.sleep(0.01)
        received_events.append(("sub2", event.execution_id))
        
    ExecutionEventBus.subscribe(sub1)
    ExecutionEventBus.subscribe(sub2)
    
    await ExecutionEventBus.publish(bus_event)
    
    assert len(received_events) == 2
    assert ("sub1", "ex_bus") in received_events
    assert ("sub2", "ex_bus") in received_events

@pytest.mark.anyio
async def test_failed_subscriber_does_not_break_bus():
    bus_event = ExecutionEvent(event_type="TestEvent", execution_id="ex_bus")
    runs = []
    
    async def failing_sub(event):
        raise RuntimeError("Fail!")
        
    async def success_sub(event):
        runs.append(True)
        
    ExecutionEventBus.subscribe(failing_sub)
    ExecutionEventBus.subscribe(success_sub)
    
    # Publish should not raise RuntimeError and success_sub should still execute
    await ExecutionEventBus.publish(bus_event)
    
    assert len(runs) == 1
    assert runs[0] is True
