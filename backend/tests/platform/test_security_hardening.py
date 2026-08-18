import pytest
import os
import json
from httpx import AsyncClient
from app.models.organization import Organization
from app.models.user import User
from app.models.workflow import Workflow
from app.models.execution import Execution
from app.core.security.jwt import create_access_token
from app.core.security.context import SecurityContext
from bson import ObjectId

pytestmark = pytest.mark.anyio

async def create_user_and_org(client: AsyncClient, prefix: str):
    res = await client.post("/api/v1/auth/register", json={"email": f"{prefix}@example.com", "password": "TestPassword123", "name": prefix})
    assert res.status_code == 200
    user_id = res.json()["id"]
    
    # Login to create default org
    login_res = await client.post("/api/v1/auth/login", json={"email": f"{prefix}@example.com", "password": "TestPassword123"})
    token = login_res.json()["access_token"]
    
    # Fetch user's org
    org = await Organization.find_one(Organization.owner_id == user_id)
    org_id = str(org.id)
    return user_id, org_id, token

@pytest.mark.anyio
async def test_jwt_missing(client: AsyncClient):
    # Public route should work
    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    
    # Protected route should fail 401
    res = await client.get("/api/v1/organizations/")
    assert res.status_code == 401
    data = res.json()
    assert data["code"] == "UNAUTHORIZED"

@pytest.mark.anyio
async def test_jwt_invalid(client: AsyncClient):
    res = await client.get("/api/v1/organizations/", headers={"Authorization": "Bearer invalid_token_123"})
    assert res.status_code == 401
    data = res.json()
    assert data["message"] == "Invalid or expired JWT token"
    # Ensure no stack trace in details
    assert "jose.exceptions" not in data.get("detail", "")

@pytest.mark.anyio
async def test_multi_tenant_workflow_isolation(client: AsyncClient):
    user1_id, org1_id, token1 = await create_user_and_org(client, "tenant1")
    user2_id, org2_id, token2 = await create_user_and_org(client, "tenant2")
    
    # Tenant 1 creates a workflow
    res = await client.post("/api/v1/workflows/", headers={"Authorization": f"Bearer {token1}"}, json={"name": "Tenant 1 Workflow"})
    assert res.status_code == 200
    wf_id = res.json()["id"]
    
    # Tenant 1 accesses their workflow
    res1 = await client.get(f"/api/v1/workflows/{wf_id}", headers={"Authorization": f"Bearer {token1}"})
    assert res1.status_code == 200
    
    # Tenant 2 tries to access Tenant 1's workflow
    res2 = await client.get(f"/api/v1/workflows/{wf_id}", headers={"Authorization": f"Bearer {token2}"})
    # Could be 403 or 404 depending on implementation, both are safe
    assert res2.status_code in (403, 404)

@pytest.mark.anyio
async def test_multi_tenant_execution_isolation(client: AsyncClient):
    user1_id, org1_id, token1 = await create_user_and_org(client, "exec1")
    user2_id, org2_id, token2 = await create_user_and_org(client, "exec2")
    
    # Tenant 1 creates a workflow
    res = await client.post("/api/v1/workflows/", headers={"Authorization": f"Bearer {token1}"}, json={"name": "Tenant 1 Exec WF"})
    wf_id = res.json()["id"]
    
    # We must create a version to execute it
    version_res = await client.post(f"/api/v1/workflows/{wf_id}/versions", headers={"Authorization": f"Bearer {token1}"}, json={
        "nodes": [{"id": "1", "type": "manual_trigger", "data": {}}],
        "edges": []
    })
    
    # Tenant 1 starts execution
    res = await client.post(f"/api/v1/workflows/{wf_id}/execute", headers={"Authorization": f"Bearer {token1}"}, json={"trigger_type": "manual"})
    assert res.status_code == 200
    exec_id = res.json()["id"]
    
    # Tenant 2 attempts to pause the execution
    res2 = await client.post(f"/api/v1/workflows/{wf_id}/executions/{exec_id}/pause", headers={"Authorization": f"Bearer {token2}"})
    assert res2.status_code in (403, 404)

@pytest.mark.anyio
async def test_error_handling_no_stack_trace(client: AsyncClient):
    # Trigger a 500 error on purpose if we can, or rely on bad input
    user1_id, org1_id, token1 = await create_user_and_org(client, "erruser")
    res = await client.get("/api/v1/workflows/invalid_obj_id", headers={"Authorization": f"Bearer {token1}"})
    # If 404, it's caught. If 500, it should not leak.
    data = res.json()
    assert "Traceback" not in json.dumps(data)
    assert "File " not in json.dumps(data)

@pytest.mark.anyio
async def test_ssrf_protection_http_node():
    from app.core.nodes.implementations.http_request import HTTPRequestNodeExecutor
    from app.core.execution.context import ExecutionContext
    from app.core.security.context import SecurityException
    
    executor = HTTPRequestNodeExecutor()
    ctx = ExecutionContext(execution_id="1", workflow_definition_id="1", workflow_definition_version="1", tenant_id="1", nodes=[], edges=[])
    
    # Private IP
    node_data_private = {"id": "n1", "url": "http://169.254.169.254/latest/meta-data/"}
    with pytest.raises(SecurityException) as exc:
        await executor.execute(node_data_private, ctx)
    assert "blocked" in str(exc.value).lower() or "restricted" in str(exc.value).lower()
    
    # Localhost
    node_data_local = {"id": "n2", "url": "http://localhost:8000"}
    with pytest.raises(SecurityException) as exc:
        await executor.execute(node_data_local, ctx)
    assert "restricted" in str(exc.value).lower()

@pytest.mark.anyio
async def test_path_traversal_file_storage():
    from app.core.nodes.implementations.file_storage import FileStorageNodeExecutor
    from app.core.execution.context import ExecutionContext
    
    executor = FileStorageNodeExecutor()
    ctx = ExecutionContext(execution_id="1", workflow_definition_id="1", workflow_definition_version="1", tenant_id="1", nodes=[], edges=[])
    
    node_data = {"id": "f1", "operation": "write", "filePath": "../../../windows/system32/config.sys", "content": "test"}
    with pytest.raises(ValueError) as exc:
        await executor.execute(node_data, ctx)
    assert "Invalid path traversal" in str(exc.value)

@pytest.mark.anyio
async def test_credentials_redaction(client: AsyncClient):
    user1_id, org1_id, token1 = await create_user_and_org(client, "credtest")
    
    # Create credential
    res = await client.post("/api/v1/debug/credentials", headers={"Authorization": f"Bearer {token1}"}, json={
        "name": "my-secret-api-key",
        "provider": "openai",
        "value": "sk-supersecret123456"
    })
    assert res.status_code == 200
    
    # List credentials
    res = await client.get("/api/v1/debug/credentials", headers={"Authorization": f"Bearer {token1}"})
    assert res.status_code == 200
    
    data = res.json()
    dump = json.dumps(data)
    # The value should NOT be returned
    assert "sk-supersecret123456" not in dump
    assert "my-secret-api-key" in dump
