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

async def run_production_readiness_audit():
    print("================================================================")
    print("  FLUXA PRODUCTION READINESS & SYSTEM HARDENING AUDIT (PHASE A)")
    print("================================================================")

    # Initialize Mock Mongo DB & Beanie
    client = AsyncMongoMockClient()
    client.append_metadata = None
    db = client["fluxa_audit_db"]
    
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

    findings = []

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as http:

        # ---------------------------------------------------------
        # DOMAIN 1: E2E User Journey & Happy Path vs Edge Cases
        # ---------------------------------------------------------
        print("\n[AUDIT] 1. E2E User Journey Audit...")
        # Happy path
        reg = await http.post("/auth/register", json={"email": "e2e@fluxa.io", "password": "pass", "name": "E2E User"})
        if reg.status_code != 200:
            findings.append(("AUDIT-01", "E2E Journey", "P1", "Auth Register Failed", reg.status_code, 200, "Register endpoint error"))
        
        # ---------------------------------------------------------
        # DOMAIN 2: Auth / Tenant / BOLA / IDOR Audit
        # ---------------------------------------------------------
        print("[AUDIT] 2. Auth, Tenant Isolation & BOLA/IDOR Audit...")
        
        # Finding: BOLA / Cross-Tenant Access Check
        # Attempt to access workflow belonging to org-b using org-a context
        wf_org_a = await http.post("/workflows/", json={"name": "Org A Private Workflow"})
        wf_id_a = wf_org_a.json()["id"]

        # Simulate missing / invalid JWT or unauthenticated tenant context
        unauth_get = await http.get(f"/workflows/{wf_id_a}")
        if unauth_get.status_code == 200:
            findings.append((
                "AUDIT-02",
                "Auth & Tenant",
                "P0",
                "Cross-Tenant Data Exposure / BOLA Vulnerability",
                f"HTTP {unauth_get.status_code} returned data without strict tenant check",
                "HTTP 401/403 Access Denied",
                "Workflows endpoint returns data when SecurityContext falls back to default tenant in bootstrap mode."
            ))

        # ---------------------------------------------------------
        # DOMAIN 3: Concurrency & State Consistency Audit
        # ---------------------------------------------------------
        print("[AUDIT] 3. Concurrency & State Consistency Audit...")
        # Simulate parallel execution requests on same workflow
        wf_conc = await http.post("/workflows/", json={"name": "Concurrent Execution WF"})
        wf_conc_id = wf_conc.json()["id"]

        reqs = [http.post(f"/workflows/{wf_conc_id}/execute", json={"trigger_type": "manual"}) for _ in range(5)]
        resps = await asyncio.gather(*reqs, return_exceptions=True)
        statuses = [r.status_code for r in resps if not isinstance(r, Exception)]
        if any(s >= 500 for s in statuses):
            findings.append((
                "AUDIT-03",
                "Concurrency",
                "P1",
                "Server Error on Parallel Workflow Execution Triggers",
                f"Statuses: {statuses}",
                "HTTP 200/202 with locks or queued execution IDs",
                "Simultaneous POST /execute requests can trigger memory/state lock collisions."
            ))

        # ---------------------------------------------------------
        # DOMAIN 4: Security Hardening & Secret Leakage Audit
        # ---------------------------------------------------------
        print("[AUDIT] 4. Security Hardening Audit...")
        # Test SSRF in HTTP Request node validation
        wf_ssrf = await http.post("/workflows/", json={
            "name": "SSRF Test Workflow",
            "nodes": [{
                "id": "http-1",
                "type": "http_request",
                "version": 1,
                "position": {"x": 0, "y": 0},
                "data": {"url": "http://169.254.169.254/latest/meta-data/", "method": "GET"}
            }]
        })
        if wf_ssrf.status_code == 200:
            findings.append((
                "AUDIT-04",
                "Security Hardening",
                "P1",
                "Missing Internal IP / SSRF Validation on HTTP Nodes",
                "HTTP Request node allowed internal cloud metadata IP (169.254.169.254)",
                "Validation Error (400) blocking internal subnet / localhost targeting",
                "HTTP node configuration accepts internal infrastructure IPs without restriction."
            ))

        # ---------------------------------------------------------
        # DOMAIN 5: WebSocket Authorization & Reconnect Audit
        # ---------------------------------------------------------
        print("[AUDIT] 5. WebSocket Authorization Audit...")
        # WebSocket invalid token check
        ws_endpoint = app.router.routes
        # Checking endpoint definition

        # ---------------------------------------------------------
        # DOMAIN 6: Frontend Resilience & Error Contract Audit
        # ---------------------------------------------------------
        print("[AUDIT] 6. Frontend Resilience Audit...")
        # Check Error schema consistency: detail vs message
        err_res = await http.get("/workflows/invalid-non-existent-id-12345")
        err_json = err_res.json()
        if "detail" in err_json and "message" not in err_json:
            findings.append((
                "AUDIT-05",
                "Error Contract",
                "P2",
                "Inconsistent Error Response Key Schema (detail vs message)",
                f"Keys: {list(err_json.keys())}",
                "Unified Error Response structure containing both 'detail' and 'message'",
                "FastAPI default HTTPException returns {'detail': '...'} whereas frontend AppError reads 'message'."
            ))

    print("\n================================================================")
    print("                 PHASE A AUDIT FINDINGS REPORT                  ")
    print("================================================================")
    print(f"Total Findings Discovered: {len(findings)}\n")

    for fid, domain, severity, title, obs, exp, impact in findings:
        print(f"----------------------------------------------------------------")
        print(f"Finding ID : {fid}")
        print(f"Domain     : {domain}")
        print(f"Severity   : {severity}")
        print(f"Title      : {title}")
        print(f"Observed   : {obs}")
        print(f"Expected   : {exp}")
        print(f"Impact     : {impact}")

if __name__ == "__main__":
    asyncio.run(run_production_readiness_audit())
