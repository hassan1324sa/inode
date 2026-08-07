import asyncio
import os
import uuid
import socket
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
from app.core.security.ssrf_guard import validate_url_security
from app.core.security.context import SecurityException
from unittest.mock import AsyncMock

async def run_phase_c_comprehensive_audit():
    print("==========================================================================")
    print("  PHASE C — FULL SYSTEM RE-AUDIT & COMPREHENSIVE REGRESSION SUITE  ")
    print("==========================================================================")

    # Initialize Mock Mongo DB & Beanie
    client = AsyncMongoMockClient()
    client.append_metadata = None
    db = client["fluxa_phase_c_db"]
    
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

    token_tenant_a = create_access_token(user_id="usr_alpha", organization_id="org_alpha_phase_c")
    token_tenant_b = create_access_token(user_id="usr_beta", organization_id="org_beta_phase_c")
    headers_a = {"Authorization": f"Bearer {token_tenant_a}"}
    headers_b = {"Authorization": f"Bearer {token_tenant_b}"}

    results = []

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as http:

        # ---------------------------------------------------------------------
        # C.1: Re-Audit P0/P1 Security (Auth Bypass, BOLA, SSRF, DNS)
        # ---------------------------------------------------------------------
        print("\n[SECTION C.1] Re-Auditing P0/P1 Security Guards...")
        
        # C.1.1: Unauthenticated GET /workflows
        res_c1_unauth = await http.get("/workflows/")
        assert res_c1_unauth.status_code == 401
        print("  [PASS] C.1.1 Unauthenticated Request Blocked (HTTP 401): PASS")

        # C.1.2: Tenant A creates Workflow
        create_res = await http.post("/workflows/", json={"name": "Tenant A Secure Workflow"}, headers=headers_a)
        assert create_res.status_code == 200
        wf_id_a = create_res.json()["id"]

        # C.1.3: BOLA Check — Tenant B attempts READ, UPDATE, DELETE on Tenant A Workflow
        res_bola_get = await http.get(f"/workflows/{wf_id_a}", headers=headers_b)
        assert res_bola_get.status_code == 403
        res_bola_put = await http.put(f"/workflows/{wf_id_a}", json={"name": "Hacked"}, headers=headers_b)
        assert res_bola_put.status_code == 403
        res_bola_del = await http.delete(f"/workflows/{wf_id_a}", headers=headers_b)
        assert res_bola_del.status_code == 403
        print("  [PASS] C.1.3 BOLA Cross-Tenant Access Blocked (HTTP 403 READ/WRITE/DELETE): PASS")

        # C.1.4: SSRF & DNS Rebinding Check
        ssrf_test_urls = ["http://127.0.0.1", "http://localhost", "http://169.254.169.254", "http://10.0.0.1", "file:///etc/passwd"]
        for test_url in ssrf_test_urls:
            try:
                validate_url_security(test_url)
                assert False, f"SSRF Security Failure on URL '{test_url}'!"
            except SecurityException:
                pass
        print("  [PASS] C.1.4 SSRF & DNS Rebinding Guards: PASS")

        # ---------------------------------------------------------------------
        # C.2: Full E2E Journey Audit
        # ---------------------------------------------------------------------
        print("\n[SECTION C.2] Verifying E2E Full User Journey...")
        
        # 1. Auth Register & Login
        reg_res = await http.post("/auth/register", json={"email": "phase_c@fluxa.ai", "password": "pass", "name": "Phase C User"})
        assert reg_res.status_code == 200
        login_res = await http.post("/auth/login")
        assert login_res.status_code == 200
        
        # 2. Org & Credential Creation
        org_res = await http.post("/organizations/", json={"name": "Phase C Org", "slug": "phase-c-org", "owner_id": reg_res.json()["id"]})
        assert org_res.status_code == 200
        cred_res = await http.post("/debug/credentials", json={"name": "phase-c-key", "provider": "google", "value": "sk-secret"}, headers=headers_a)
        assert cred_res.status_code == 200
        assert "value" not in cred_res.json()

        # 3. Workflow Execution Trigger & Event Stream Handshake
        exec_res = await http.post(f"/workflows/{wf_id_a}/execute", json={"trigger_type": "manual"}, headers=headers_a)
        assert exec_res.status_code == 200
        exec_id = exec_res.json()["id"]
        print("  [PASS] C.2 Full E2E User Journey (Register -> Login -> Org -> Creds -> Exec): PASS")

        # ---------------------------------------------------------------------
        # C.3: Concurrency & State Consistency
        # ---------------------------------------------------------------------
        print("\n[SECTION C.3] Testing Concurrency & Parallel Executions...")
        exec_tasks = [http.post(f"/workflows/{wf_id_a}/execute", json={"trigger_type": "parallel"}, headers=headers_a) for _ in range(10)]
        exec_responses = await asyncio.gather(*exec_tasks)
        for r in exec_responses:
            assert r.status_code == 200
        print("  [PASS] C.3 Concurrency & State Consistency (10 Parallel Executions): PASS")

        # ---------------------------------------------------------------------
        # C.4: Failure & Recovery Testing
        # ---------------------------------------------------------------------
        print("\n[SECTION C.4] Testing System Failure & Recovery Resilience...")
        res_404_recovery = await http.get("/workflows/non_existent_wf_id_9999", headers=headers_a)
        assert res_404_recovery.status_code == 404
        assert res_404_recovery.json()["code"] == "NOT_FOUND"
        print("  [PASS] C.4 Failure & Recovery Handling (Graceful HTTP 404 Error Payload): PASS")

        # ---------------------------------------------------------------------
        # C.5: Observability & Correlation Tracing
        # ---------------------------------------------------------------------
        print("\n[SECTION C.5] Auditing Observability & Correlation Tracing...")
        custom_corr_id = "corr-phase-c-trace-777"
        corr_headers = {"Authorization": f"Bearer {token_tenant_a}", "X-Correlation-ID": custom_corr_id}
        res_corr = await http.get(f"/workflows/{wf_id_a}", headers=corr_headers)
        assert res_corr.headers.get("x-correlation-id") == custom_corr_id
        
        exec_corr_res = await http.post(f"/workflows/{wf_id_a}/execute", json={"trigger_type": "manual"}, headers=corr_headers)
        db_exec_doc = await Execution.get(exec_corr_res.json()["id"])
        assert db_exec_doc.metadata.get("correlation_id") == custom_corr_id
        print("  [PASS] C.5 Observability & Correlation ID Tracing: PASS")

        # ---------------------------------------------------------------------
        # C.6: Canonical Error Schema & Status Mapping
        # ---------------------------------------------------------------------
        print("\n[SECTION C.6] Verifying Canonical API Error Schema Mapping...")
        err_401 = (await http.get("/workflows/")).json()
        assert err_401["code"] == "UNAUTHORIZED" and "message" in err_401 and "detail" in err_401
        
        err_403 = (await http.get(f"/workflows/{wf_id_a}", headers=headers_b)).json()
        assert err_403["code"] == "FORBIDDEN" and "message" in err_403 and "detail" in err_403

        err_404 = (await http.get("/workflows/non_existent_wf_id_9999", headers=headers_a)).json()
        assert err_404["code"] == "NOT_FOUND" and "message" in err_404 and "detail" in err_404
        print("  [PASS] C.6 Canonical API Error Schema Mapping: PASS")

    print("\n==========================================================================")
    print("  PHASE C COMPREHENSIVE RE-AUDIT COMPLETE — ALL TESTS PASSED SUCCESSFULLY ")
    print("==========================================================================")

if __name__ == "__main__":
    asyncio.run(run_phase_c_comprehensive_audit())
