import asyncio
import os
os.environ["FLUXA_SYSTEM_BOOTSTRAP"] = "true"

from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import db_manager
from app.models.user import User
from app.models.organization import Organization
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.models.execution import Execution
from app.models.node_execution import NodeExecution
from app.core.cache.memory import MemoryCache
from unittest.mock import AsyncMock

async def run_integration_contract_tests():
    print("--- Starting Backend Integration Contract Verification ---")
    
    # 1. Initialize Mock Mongo DB & Beanie
    client = AsyncMongoMockClient()
    client.append_metadata = None
    db = client["fluxa_test_db"]
    
    orig_list_collection_names = db.list_collection_names
    async def patched_list_collection_names(*args, **kwargs):
        return await orig_list_collection_names(*args)
    db.list_collection_names = patched_list_collection_names
    
    await init_beanie(
        database=db,
        document_models=[User, Organization, Workflow, WorkflowVersion, Execution, NodeExecution]
    )
    
    db_manager.client = client
    db_manager.connect_db = lambda: None
    db_manager.close_db = lambda: None
    
    mock_service = AsyncMock()
    mock_service.start_execution.return_value = "mock-run-id"
    app.state.memory_cache = MemoryCache()
    app.state.execution_service = mock_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as http:
        # TEST 1: Health Endpoint
        res = await http.get("/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print("[PASS] Health Check API Contract: PASS")
        
        # TEST 2: Auth Flow
        reg_res = await http.post("/auth/register", json={"email": "audit@fluxa.ai", "password": "pass", "name": "Auditor"})
        assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
        user_id = reg_res.json()["id"]
        assert reg_res.json()["email"] == "audit@fluxa.ai"
        print("[PASS] Auth Register API Contract: PASS")

        login_res = await http.post("/auth/login")
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        http.headers["Authorization"] = f"Bearer {token}"
        print("[PASS] Auth Login API Contract: PASS")

        # TEST 3: Organization & Settings Flow
        org_res = await http.post("/organizations/", json={"name": "Audit Org", "slug": "audit-org", "owner_id": user_id})
        assert org_res.status_code == 200
        org_id = org_res.json()["id"]
        print("[PASS] Organization Create API Contract: PASS")

        org_list = await http.get("/organizations/")
        assert org_list.status_code == 200
        assert len(org_list.json()) >= 1
        print("[PASS] Organization List API Contract: PASS")

        org_detail = await http.get("/organizations/audit-org")
        assert org_detail.status_code == 200
        assert org_detail.json()["slug"] == "audit-org"
        print("[PASS] Organization Get By Slug API Contract: PASS")

        # TEST 4: Workflow CRUD E2E Contract
        wf_create = await http.post("/workflows/", json={
            "name": "Integration Workflow",
            "description": "E2E Contract Audit Workflow",
            "nodes": [{"id": "node-1", "type": "webhook_trigger", "version": 1, "position": {"x": 0, "y": 0}, "data": {}}],
            "edges": [],
            "variables": {"test_var": 123}
        })
        assert wf_create.status_code == 200, f"Workflow create failed: {wf_create.text}"
        wf_data = wf_create.json()
        wf_id = wf_data["id"]
        assert wf_data["name"] == "Integration Workflow"
        assert len(wf_data["nodes"]) == 1
        assert wf_data["variables"]["test_var"] == 123
        print("[PASS] Workflow Create API Contract: PASS")

        wf_get = await http.get(f"/workflows/{wf_id}")
        assert wf_get.status_code == 200
        assert wf_get.json()["id"] == wf_id
        print("[PASS] Workflow Get API Contract: PASS")

        wf_update = await http.put(f"/workflows/{wf_id}", json={
            "name": "Updated Workflow Name",
            "description": "Updated Description",
            "nodes": [
                {"id": "node-1", "type": "webhook_trigger", "version": 1, "position": {"x": 0, "y": 0}, "data": {}},
                {"id": "node-2", "type": "http_request", "version": 1, "position": {"x": 200, "y": 0}, "data": {}}
            ],
            "edges": [{"id": "e1-2", "source": "node-1", "target": "node-2"}],
            "variables": {"test_var": 999}
        })
        assert wf_update.status_code == 200
        updated_data = wf_update.json()
        assert updated_data["name"] == "Updated Workflow Name"
        assert len(updated_data["nodes"]) == 2
        assert updated_data["variables"]["test_var"] == 999
        print("[PASS] Workflow Update API Contract: PASS")

        wf_delete = await http.delete(f"/workflows/{wf_id}")
        assert wf_delete.status_code == 200
        print("[PASS] Workflow Delete API Contract: PASS")

        wf_get_deleted = await http.get(f"/workflows/{wf_id}")
        assert wf_get_deleted.status_code == 404
        print("[PASS] Workflow 404 Verification API Contract: PASS")

        # TEST 5: Credentials Security & API Contract
        cred_create = await http.post("/debug/credentials", json={"name": "test-gemini-key", "provider": "google", "value": "sk-secret-12345"})
        assert cred_create.status_code == 200
        cred_resp = cred_create.json()
        assert cred_resp["credential_id"] == "test-gemini-key"
        assert "value" not in cred_resp, "SECURITY MISMATCH: Raw Secret Key returned in Create Credential response!"
        print("[PASS] Credential Create & Secret Protection API Contract: PASS")

        cred_list = await http.get("/debug/credentials")
        assert cred_list.status_code == 200
        creds = cred_list.json()["credentials"]
        assert any(c["credential_id"] == "test-gemini-key" for c in creds)
        for c in creds:
            assert "value" not in c, "SECURITY MISMATCH: Secret value leaked in List Credentials response!"
        print("[PASS] Credential List & Secret Protection API Contract: PASS")

        cred_del = await http.delete("/debug/credentials/test-gemini-key")
        assert cred_del.status_code == 200
        print("[PASS] Credential Delete API Contract: PASS")

    print("\n--- ALL BACKEND INTEGRATION CONTRACT TESTS PASSED SUCCESSFULLY ---")

if __name__ == "__main__":
    asyncio.run(run_integration_contract_tests())
