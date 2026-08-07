import asyncio
import os
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
from app.core.security.jwt import create_access_token
from unittest.mock import AsyncMock

async def test_phase_b1_security_invariants():
    print("================================================================")
    print("  PHASE B.1 REMEDIATION VERIFICATION: P0 AUTHENTICATION & BOLA ")
    print("================================================================")

    # Initialize Mock Mongo DB & Beanie
    client = AsyncMongoMockClient()
    client.append_metadata = None
    db = client["fluxa_test_b1_db"]
    
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

    # Create signed tokens for 2 different organizations (Org A and Org B)
    token_org_a = create_access_token(user_id="user_a", organization_id="org_alpha_123")
    token_org_b = create_access_token(user_id="user_b", organization_id="org_beta_999")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as http:
        
        # ---------------------------------------------------------------------
        # SECURITY INVARIANT 1: Unauthenticated request without JWT MUST be rejected with HTTP 401
        # ---------------------------------------------------------------------
        print("\n[TEST 1] Testing Unauthenticated Access Prevention (No JWT)...")
        res_no_auth = await http.get("/workflows/")
        assert res_no_auth.status_code == 401, f"SECURITY VIOLATION! Unauthenticated GET /workflows returned HTTP {res_no_auth.status_code}"
        print("[PASS] Security Invariant 1 Verified: Unauthenticated request rejected with HTTP 401.")

        res_no_auth_post = await http.post("/workflows/", json={"name": "Hacker Workflow"})
        assert res_no_auth_post.status_code == 401, f"SECURITY VIOLATION! Unauthenticated POST /workflows returned HTTP {res_no_auth_post.status_code}"
        print("[PASS] Security Invariant 1 Verified: Unauthenticated write rejected with HTTP 401.")

        res_no_auth_cred = await http.get("/debug/credentials")
        assert res_no_auth_cred.status_code == 401, f"SECURITY VIOLATION! Unauthenticated GET /credentials returned HTTP {res_no_auth_cred.status_code}"
        print("[PASS] Security Invariant 1 Verified: Unauthenticated credential access rejected with HTTP 401.")

        # ---------------------------------------------------------------------
        # SECURITY INVARIANT 2: Authenticated User A can create workflow in Tenant A
        # ---------------------------------------------------------------------
        print("\n[TEST 2] Creating Workflow under Tenant A (org_alpha_123)...")
        headers_a = {"Authorization": f"Bearer {token_org_a}"}
        create_res = await http.post("/workflows/", json={"name": "Tenant A Confidential Workflow"}, headers=headers_a)
        assert create_res.status_code == 200, f"Failed to create workflow: {create_res.text}"
        wf_data_a = create_res.json()
        wf_id_a = wf_data_a["id"]
        assert wf_data_a["organization_id"] == "org_alpha_123"
        print("[PASS] Security Invariant 2 Verified: Workflow successfully created bound to Tenant A.")

        # ---------------------------------------------------------------------
        # SECURITY INVARIANT 3: BOLA Check — Tenant B Token MUST NOT access Tenant A Workflow (HTTP 403)
        # ---------------------------------------------------------------------
        print("\n[TEST 3] Testing BOLA/Cross-Tenant Attack (Tenant B Token attempting to read Tenant A Workflow)...")
        headers_b = {"Authorization": f"Bearer {token_org_b}"}
        get_res_bola = await http.get(f"/workflows/{wf_id_a}", headers=headers_b)
        assert get_res_bola.status_code == 403, f"BOLA SECURITY FAILURE! Tenant B was able to access Tenant A workflow! HTTP Status: {get_res_bola.status_code}"
        print("[PASS] Security Invariant 3 Verified: Cross-Tenant read attempt blocked with HTTP 403 Forbidden.")

        print("\n[TEST 4] Testing BOLA/Cross-Tenant Attack (Tenant B Token attempting to update Tenant A Workflow)...")
        put_res_bola = await http.put(f"/workflows/{wf_id_a}", json={"name": "Hacked Name"}, headers=headers_b)
        assert put_res_bola.status_code == 403, f"BOLA SECURITY FAILURE! Tenant B was able to update Tenant A workflow! HTTP Status: {put_res_bola.status_code}"
        print("[PASS] Security Invariant 3 Verified: Cross-Tenant write attempt blocked with HTTP 403 Forbidden.")

        print("\n[TEST 5] Testing BOLA/Cross-Tenant Attack (Tenant B Token attempting to delete Tenant A Workflow)...")
        del_res_bola = await http.delete(f"/workflows/{wf_id_a}", headers=headers_b)
        assert del_res_bola.status_code == 403, f"BOLA SECURITY FAILURE! Tenant B was able to delete Tenant A workflow! HTTP Status: {del_res_bola.status_code}"
        print("[PASS] Security Invariant 3 Verified: Cross-Tenant delete attempt blocked with HTTP 403 Forbidden.")

        # ---------------------------------------------------------------------
        # SECURITY INVARIANT 4: Legitimate Owner (Tenant A) CAN access and manage Tenant A Workflow
        # ---------------------------------------------------------------------
        print("\n[TEST 6] Verifying Legitimate Access for Tenant A Owner...")
        get_res_owner = await http.get(f"/workflows/{wf_id_a}", headers=headers_a)
        assert get_res_owner.status_code == 200
        assert get_res_owner.json()["name"] == "Tenant A Confidential Workflow"
        print("[PASS] Security Invariant 4 Verified: Legitimate owner granted access.")

    print("\n================================================================")
    print("  ALL PHASE B.1 SECURITY INVARIANTS (P0) PASSED SUCCESSFULLY!  ")
    print("================================================================")

if __name__ == "__main__":
    asyncio.run(test_phase_b1_security_invariants())
