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

async def test_phase_b3_error_contract_invariants():
    print("================================================================")
    print("  PHASE B.3 REMEDIATION VERIFICATION: P2 CANONICAL ERROR MODEL  ")
    print("================================================================")

    # Initialize Mock Mongo DB & Beanie
    client = AsyncMongoMockClient()
    client.append_metadata = None
    db = client["fluxa_test_b3_db"]
    
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
    headers_a = {"Authorization": f"Bearer {token_org_a}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1") as http:

        # ---------------------------------------------------------------------
        # CANONICAL CONTRACT TEST 1: HTTP 401 UNAUTHORIZED
        # ---------------------------------------------------------------------
        print("\n[TEST 1] Testing HTTP 401 UNAUTHORIZED Canonical Error Schema...")
        res_401 = await http.get("/workflows/")
        assert res_401.status_code == 401
        payload_401 = res_401.json()
        assert payload_401["statusCode"] == 401
        assert payload_401["code"] == "UNAUTHORIZED"
        assert "message" in payload_401
        assert "detail" in payload_401
        print(f"[PASS] 401 Canonical Schema Verified: {payload_401}")

        # ---------------------------------------------------------------------
        # CANONICAL CONTRACT TEST 2: HTTP 403 FORBIDDEN
        # ---------------------------------------------------------------------
        print("\n[TEST 2] Testing HTTP 403 FORBIDDEN Canonical Error Schema...")
        wf_create = await http.post("/workflows/", json={"name": "Org A Workflow"}, headers=headers_a)
        wf_id = wf_create.json()["id"]

        token_org_b = create_access_token(user_id="user_b", organization_id="org_beta_999")
        headers_b = {"Authorization": f"Bearer {token_org_b}"}

        res_403 = await http.get(f"/workflows/{wf_id}", headers=headers_b)
        assert res_403.status_code == 403
        payload_403 = res_403.json()
        assert payload_403["statusCode"] == 403
        assert payload_403["code"] == "FORBIDDEN"
        assert "message" in payload_403
        assert "detail" in payload_403
        print(f"[PASS] 403 Canonical Schema Verified: {payload_403}")

        # ---------------------------------------------------------------------
        # CANONICAL CONTRACT TEST 3: HTTP 404 NOT FOUND
        # ---------------------------------------------------------------------
        print("\n[TEST 3] Testing HTTP 404 NOT_FOUND Canonical Error Schema...")
        res_404 = await http.get("/workflows/6a7494db4d87d199a83a9999", headers=headers_a)
        assert res_404.status_code == 404
        payload_404 = res_404.json()
        assert payload_404["statusCode"] == 404
        assert payload_404["code"] == "NOT_FOUND"
        assert "message" in payload_404
        assert "detail" in payload_404
        print(f"[PASS] 404 Canonical Schema Verified: {payload_404}")

        # ---------------------------------------------------------------------
        # CANONICAL CONTRACT TEST 4: HTTP 400 VALIDATION ERROR
        # ---------------------------------------------------------------------
        print("\n[TEST 4] Testing HTTP 400 VALIDATION_ERROR Canonical Error Schema...")
        res_400 = await http.post("/workflows/", json={"nodes": "invalid_string_instead_of_list"}, headers=headers_a)
        assert res_400.status_code == 400
        payload_400 = res_400.json()
        assert payload_400["statusCode"] == 400
        assert payload_400["code"] == "VALIDATION_ERROR"
        assert "message" in payload_400
        assert "detail" in payload_400
        print(f"[PASS] 400 Canonical Schema Verified: {payload_400}")

    print("\n================================================================")
    print("  ALL PHASE B.3 SECURITY INVARIANTS (P2) PASSED SUCCESSFULLY!  ")
    print("================================================================")

if __name__ == "__main__":
    asyncio.run(test_phase_b3_error_contract_invariants())
