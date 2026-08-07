import pytest
import os
import csv
from unittest.mock import patch, MagicMock
from app.core.execution.context import ExecutionContext
from app.core.execution.engine import ExecutionEngine
from app.core.events.event_bus import ExecutionEventBus
from app.core.execution.live_debug import LiveExecutionStreamManager, EventStore
from app.core.execution.durable_store import MongoDBEventStore, ExecutionEffect
from app.core.security.secrets import VaultSecretProvider, SecretRef
from app.core.security.context import SecurityContext, SecurityContextHolder

@pytest.fixture(autouse=True)
async def clean_automation_state():
    ExecutionEventBus.clear()
    await LiveExecutionStreamManager.initialize()
    await MongoDBEventStore.setup_indexes()
    db = db_manager.db if 'db_manager' in globals() else None
    if db:
        await db["execution_events"].delete_many({})
        await db["execution_snapshots"].delete_many({})
        await db["execution_effects"].delete_many({})
        await db["execution_sequence_counters"].delete_many({})
    VaultSecretProvider._store.clear()
    VaultSecretProvider._revoked_paths.clear()
    LiveExecutionStreamManager._active_connections.clear()
    yield
    ExecutionEventBus.clear()
    VaultSecretProvider._store.clear()
    VaultSecretProvider._revoked_paths.clear()
    LiveExecutionStreamManager._active_connections.clear()

@pytest.mark.anyio
async def test_e2e_excel_to_email_automation():
    # 1. Create a temporary CSV file
    temp_csv_path = "temp_customers.csv"
    with open(temp_csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "email", "sales", "last_order", "status"])
        writer.writerow(["Ahmed", "ahmed@example.com", "25000", "5 days ago", "Active"])
        writer.writerow(["Mohamed", "mohamed@example.com", "8000", "40 days ago", "Inactive"])
        writer.writerow(["Ali", "ali@example.com", "18000", "10 days ago", "Active"])
        
    # 2. Setup Security Context and Vault password secret
    ctx = SecurityContext(
        organization_id="tenant-a", workspace_id="w-1",
        environment_id="env-1", project_id="p-1", user_id="u-1",
        session_id="exec-e2e-1"
    )
    SecurityContextHolder.set_context(ctx)
    
    provider = VaultSecretProvider()
    await provider.put("smtp_pass", "super_smtp_secret_pass")
    
    # 3. Build the E2E Workflow structure
    read_excel_node = {
        "id": "read-excel-1",
        "type": "read-excel",
        "file_path": temp_csv_path,
        "output_var": "customers"
    }
    
    loop_node = {
        "id": "loop-1",
        "type": "loop",
        "items_var": "customers",
        "loop_nodes": [
            {
                "id": "cond-1",
                "type": "conditional",
                "field": "sales",
                "operator": ">",
                "value": 15000
            },
            {
                "id": "send-email-1",
                "type": "send-email",
                "if_condition": "variables.last_condition_result",
                "recipient": "current_row.email",
                "subject": "Offer for {current_row.name}",
                "body": "Hello {current_row.name}, your last order was {current_row.last_order}.",
                "smtp_host": "localhost",
                "smtp_port": 1025,
                "username": "sales@fluxa.com",
                "password_ref": {"provider": "vault", "path": "smtp_pass"}
            }
        ]
    }
    
    # 4. Mock SMTP sending
    mock_smtp = MagicMock()
    with patch("smtplib.SMTP", return_value=mock_smtp):
        # Execute E2E flow
        exec_ctx = ExecutionContext(
            execution_id="exec-e2e-1",
            workflow_definition_id="wf-automation",
            workflow_definition_version=1,
            tenant_id="tenant-a",
            variables={},
            node_outputs={},
            current_node_id=None
        )
        
        engine = ExecutionEngine()
        exec_ctx = await engine.execute_node(read_excel_node, exec_ctx)
        
        # Simulate Loop Orchestrator Traversal
        items = exec_ctx.variables.get("customers", [])
        for idx, item in enumerate(items):
            exec_ctx.variables["current_row"] = item
            exec_ctx.variables["loop_index"] = idx
            exec_ctx.variables["last_condition_result"] = True
            for sub_node in loop_node["loop_nodes"]:
                if_cond = sub_node.get("if_condition")
                if if_cond == "variables.last_condition_result":
                    if not exec_ctx.variables.get("last_condition_result", True):
                        continue
                exec_ctx = await engine.execute_node(sub_node, exec_ctx)
        
        # Verify result:
        # Ahmed: sales 25000 > 15000 -> Should send email
        # Mohamed: sales 8000 < 15000 -> Should skip email
        # Ali: sales 18000 > 15000 -> Should send email
        assert mock_smtp.sendmail.call_count == 2
        
        # Check sendmail calls parameters
        calls = mock_smtp.sendmail.call_args_list
        recipients = [call[0][1][0] for call in calls]
        assert "ahmed@example.com" in recipients
        assert "ali@example.com" in recipients
        assert "mohamed@example.com" not in recipients
        
        # 5. Deterministic Replay Check
        # During Replay, SMTP sendmail should NEVER be called again (returns from effect cache)
        mock_smtp.reset_mock()
        
        replay_ctx = SecurityContext(
            organization_id="tenant-a", workspace_id="w-1",
            environment_id="env-1", project_id="p-1", user_id="u-1",
            session_id="replay-exec-e2e-1"  # Prefix replay-
        )
        SecurityContextHolder.set_context(replay_ctx)
        
        replay_exec_ctx = ExecutionContext(
            execution_id="replay-exec-e2e-1",
            workflow_definition_id="wf-automation",
            workflow_definition_version=1,
            tenant_id="tenant-a",
            variables={},
            node_outputs={},
            current_node_id=None
        )
        
        replay_exec_ctx = await engine.execute_node(read_excel_node, replay_exec_ctx)
        
        # Simulate Loop Replay Orchestrator Traversal
        items_rep = replay_exec_ctx.variables.get("customers", [])
        for idx, item in enumerate(items_rep):
            replay_exec_ctx.variables["current_row"] = item
            replay_exec_ctx.variables["loop_index"] = idx
            replay_exec_ctx.variables["last_condition_result"] = True
            for sub_node in loop_node["loop_nodes"]:
                if_cond = sub_node.get("if_condition")
                if if_cond == "variables.last_condition_result":
                    if not replay_exec_ctx.variables.get("last_condition_result", True):
                        continue
                replay_exec_ctx = await engine.execute_node(sub_node, replay_exec_ctx)
        
        # Assert sendmail was NOT called during replay
        assert mock_smtp.sendmail.call_count == 0

    # Cleanup temp file
    if os.path.exists(temp_csv_path):
        os.remove(temp_csv_path)
    SecurityContextHolder.clear_context()
