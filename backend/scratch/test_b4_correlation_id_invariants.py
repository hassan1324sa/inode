import asyncio
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

async def test_phase_b4_correlation_id_invariants():
    print("================================================================")
    print("  PHASE B.4 REMEDIATION VERIFICATION: P2 CORRELATION ID TRACING ")
    print("================================================================")

    # Initialize Mock Mongo DB & Beanie
    client = AsyncMongoMockClient()
    client.append_metadata = None
    db = client["fluxa_test_b4_db"]
    
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

    token_org_a = create_access_token(user_id="user_a", organization_id="org_alpha_123")
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as http:

        # ---------------------------------------------------------------------
        # TEST 1: Request with Client-Provided X-Correlation-ID Header Propagation
        # ---------------------------------------------------------------------
        print("\n[TEST 1] Testing Custom Client Provided X-Correlation-ID Propagation...")
        client_correlation_id = "corr-custom-client-trace-999"
        headers_with_corr = {
            "Authorization": f"Bearer {token_org_a}",
            "X-Correlation-ID": client_correlation_id
        }
        
        res = await http.get("/workflows/", headers=headers_with_corr)
        assert res.status_code == 200
        assert "x-correlation-id" in res.headers, "X-Correlation-ID missing from response headers!"
        assert res.headers["x-correlation-id"] == client_correlation_id, f"Correlation ID Mismatch! Expected '{client_correlation_id}', got '{res.headers['x-correlation-id']}'"
        print(f"[PASS] Client Provided Correlation ID Propagated in Response Headers: {res.headers['x-correlation-id']}")

        # ---------------------------------------------------------------------
        # TEST 2: Request without X-Correlation-ID Header Auto-Generation
        # ---------------------------------------------------------------------
        print("\n[TEST 2] Testing Server Auto-Generation of X-Correlation-ID when Omitted...")
        headers_no_corr = {"Authorization": f"Bearer {token_org_a}"}
        res_auto = await http.get("/workflows/", headers=headers_no_corr)
        assert res_auto.status_code == 200
        assert "x-correlation-id" in res_auto.headers, "Auto-generated X-Correlation-ID missing from response!"
        auto_gen_id = res_auto.headers["x-correlation-id"]
        assert auto_gen_id.startswith("corr-"), f"Auto-generated Correlation ID format invalid: {auto_gen_id}"
        print(f"[PASS] Server Auto-Generated Correlation ID: {auto_gen_id}")

        # ---------------------------------------------------------------------
        # TEST 3: Execution Metadata Correlation ID Propagation
        # ---------------------------------------------------------------------
        print("\n[TEST 3] Testing Correlation ID Propagation to Workflow Execution Metadata...")
        wf_create = await http.post("/workflows/", json={"name": "Correlation Test Workflow"}, headers=headers_with_corr)
        wf_id = wf_create.json()["id"]

        exec_corr_id = "corr-execution-trace-555"
        exec_headers = {
            "Authorization": f"Bearer {token_org_a}",
            "X-Correlation-ID": exec_corr_id
        }
        exec_res = await http.post(f"/workflows/{wf_id}/execute", json={"trigger_type": "manual"}, headers=exec_headers)
        assert exec_res.status_code == 200
        exec_id = exec_res.json()["id"]

        # Verify DB Execution document contains correlation_id in metadata
        db_exec = await Execution.get(exec_id)
        assert db_exec is not None
        assert "correlation_id" in db_exec.metadata, "correlation_id missing from Execution metadata!"
        assert db_exec.metadata["correlation_id"] == exec_corr_id, f"Execution metadata correlation_id mismatch: {db_exec.metadata['correlation_id']}"
        print(f"[PASS] Execution Metadata Correlation ID Verified: {db_exec.metadata['correlation_id']}")

        # ---------------------------------------------------------------------
        # TEST 4: Isolation of Correlation IDs between Concurrent Parallel Requests
        # ---------------------------------------------------------------------
        print("\n[TEST 4] Testing Correlation ID Isolation across Concurrent Parallel Requests...")
        async def make_corr_req(req_idx: int):
            corr = f"corr-parallel-req-{req_idx}"
            r = await http.get("/workflows/", headers={"Authorization": f"Bearer {token_org_a}", "X-Correlation-ID": corr})
            return r.headers.get("x-correlation-id"), corr

        tasks = [make_corr_req(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        for actual_corr, expected_corr in results:
            assert actual_corr == expected_corr, f"CONCURRENCY CORRELATION LEAK! Expected '{expected_corr}', got '{actual_corr}'"
        print("[PASS] Concurrency Isolation Verified: 10 parallel requests maintained 10 unique, non-interfering Correlation IDs.")

    print("\n================================================================")
    print("  ALL PHASE B.4 SECURITY INVARIANTS (P2) PASSED SUCCESSFULLY!  ")
    print("================================================================")

if __name__ == "__main__":
    asyncio.run(test_phase_b4_correlation_id_invariants())
