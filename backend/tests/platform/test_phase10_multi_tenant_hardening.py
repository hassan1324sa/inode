import pytest
from app.core.security.context import SecurityContext, SecurityContextHolder, SecurityException
from app.core.execution.context import ExecutionContext
from app.core.execution.activities import execute_node_activity
from app.models.execution import Execution
from app.models.node_execution import NodeExecution
from bson import ObjectId

@pytest.fixture(autouse=True)
def clean_security_state():
    SecurityContextHolder.clear_context()
    yield
    SecurityContextHolder.clear_context()

@pytest.mark.anyio
async def test_worker_activity_reconstructs_security_context():
    # 1. Setup Execution Context mock payload for Org A
    context_a = ExecutionContext(
        execution_id=str(ObjectId()),
        workflow_definition_id="wf-1",
        workflow_definition_version=1,
        tenant_id="org-alpha",
        variables={},
        node_outputs={},
        current_node_id="node-1",
        metadata={
            "workspace_id": "ws-alpha",
            "environment_id": "env-alpha",
            "project_id": "proj-alpha",
            "user_id": "user-alpha",
            "permissions": ["read", "write"]
        },
        permissions=["read", "write"]
    )

    # Mock execute_node call to capture the context inside the execution chain
    captured_context = None

    class MockFactory:
        async def execute_node(self, node_def, ctx):
            nonlocal captured_context
            # Capture the SecurityContext currently active in contextvars
            captured_context = SecurityContextHolder.get_current_context()
            return ctx

        async def ensure_db_connected(self):
            pass

    # Insert mock Execution and NodeExecution to satisfy database updates in activity
    exec_doc = Execution(
        id=ObjectId(context_a.execution_id),
        workflow_id="wf-1",
        workflow_version_id="v1",
        organization_id="org-alpha",
        metadata=context_a.metadata
    )
    await exec_doc.insert()

    node_def = {"id": "node-1", "type": "conditional", "expression": "1 == 1"}
    input_data = {
        "node_def": node_def,
        "context": context_a.model_dump()
    }

    # Patch ActivityFactory to use MockFactory
    from unittest.mock import patch
    with patch("temporalio.activity.heartbeat"), \
         patch("temporalio.activity.is_cancelled", return_value=False), \
         patch("app.core.execution.activities.factory", MockFactory()):
        # Run activity
        await execute_node_activity(input_data)

    # 2. Verify that captured SecurityContext matches the metadata claims exactly
    assert captured_context is not None
    assert captured_context.organization_id == "org-alpha"
    assert captured_context.workspace_id == "ws-alpha"
    assert captured_context.environment_id == "env-alpha"
    assert captured_context.project_id == "proj-alpha"
    assert captured_context.user_id == "user-alpha"
    assert "read" in captured_context.permissions

    # 3. Verify that context leakage does not occur (cleared after execution completes)
    assert SecurityContextHolder._context_var.get() is None


@pytest.mark.anyio
async def test_worker_activity_fails_closed_without_tenant():
    # If the activity executes with a blank tenant_id or empty context, it must fail closed
    context_empty = ExecutionContext(
        execution_id=str(ObjectId()),
        workflow_definition_id="wf-2",
        workflow_definition_version=1,
        tenant_id="",  # Blank organization identity
        variables={},
        node_outputs={},
        current_node_id="node-2"
    )

    exec_doc = Execution(
        id=ObjectId(context_empty.execution_id),
        workflow_id="wf-2",
        workflow_version_id="v1",
        organization_id="",
        metadata={}
    )
    await exec_doc.insert()

    node_def = {"id": "node-2", "type": "conditional", "expression": "1 == 1"}
    input_data = {
        "node_def": node_def,
        "context": context_empty.model_dump()
    }

    class MockFactory:
        async def execute_node(self, node_def, ctx):
            # Attempt to resolve context -> should fail closed
            SecurityContextHolder.get_current_context()
            return ctx

        async def ensure_db_connected(self):
            pass

    from unittest.mock import patch
    with patch("temporalio.activity.heartbeat"), \
         patch("temporalio.activity.is_cancelled", return_value=False), \
         patch("app.core.execution.activities.factory", MockFactory()):
        with pytest.raises(SecurityException):
            await execute_node_activity(input_data)
