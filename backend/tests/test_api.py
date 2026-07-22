import pytest
from httpx import AsyncClient

@pytest.mark.anyio
async def test_health(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.anyio
async def test_auth_flow(client: AsyncClient):
    # Register
    register_payload = {
        "email": "test@example.com",
        "password": "securepassword",
        "name": "Test User"
    }
    response = await client.post("/api/v1/auth/register", json=register_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert "id" in data

    # Login
    response = await client.post("/api/v1/auth/login")
    assert response.status_code == 200
    login_data = response.json()
    assert login_data["access_token"] == "mock_token"

@pytest.mark.anyio
async def test_organizations_flow(client: AsyncClient):
    # Register user first to get an ID (owner_id)
    register_payload = {
        "email": "owner@example.com",
        "password": "ownerpassword",
        "name": "Owner User"
    }
    resp = await client.post("/api/v1/auth/register", json=register_payload)
    owner_id = resp.json()["id"]

    # Create Org
    org_payload = {
        "name": "Test Org",
        "slug": "test-org",
        "owner_id": owner_id
    }
    response = await client.post("/api/v1/organizations/", json=org_payload)
    assert response.status_code == 200
    org_data = response.json()
    assert org_data["name"] == "Test Org"
    assert org_data["slug"] == "test-org"
    assert "id" in org_data

    # List Orgs
    response = await client.get("/api/v1/organizations/")
    assert response.status_code == 200
    orgs_list = response.json()
    assert len(orgs_list) >= 1
    assert any(o["id"] == org_data["id"] for o in orgs_list)

@pytest.mark.anyio
async def test_workflow_and_execution_flow(client: AsyncClient):
    # Register and create organization
    resp = await client.post("/api/v1/auth/register", json={
        "email": "wf_owner@example.com",
        "password": "password",
        "name": "WF Owner"
    })
    owner_id = resp.json()["id"]

    resp = await client.post("/api/v1/organizations/", json={
        "name": "WF Org",
        "slug": "wf-org",
        "owner_id": owner_id
    })
    org_id = resp.json()["id"]

    # Create Workflow
    wf_payload = {
        "organization_id": org_id,
        "name": "Demo Workflow",
        "description": "My first automated workflow"
    }
    response = await client.post("/api/v1/workflows/", json=wf_payload)
    assert response.status_code == 200
    wf_data = response.json()
    assert wf_data["name"] == "Demo Workflow"
    wf_id = wf_data["id"]

    # List Workflows
    response = await client.get("/api/v1/workflows/")
    assert response.status_code == 200
    wfs_list = response.json()
    assert any(w["id"] == wf_id for w in wfs_list)

    # Create Version (implicitly creates v2 version)
    response = await client.post(f"/api/v1/workflows/{wf_id}/versions")
    assert response.status_code == 200
    version_data = response.json()
    assert version_data["version"] == "v2"

    # Execute Workflow
    exec_payload = {
        "trigger_type": "Manual",
        "inputs": {}
    }
    response = await client.post(f"/api/v1/workflows/{wf_id}/execute", json=exec_payload)
    assert response.status_code == 200
    exec_data = response.json()
    assert exec_data["status"] == "Queued"
    exec_id = exec_data["id"]

    # List Executions
    response = await client.get(f"/api/v1/workflows/{wf_id}/executions")
    assert response.status_code == 200
    executions_list = response.json()
    assert any(e["id"] == exec_id for e in executions_list)

    # Pause Execution
    response = await client.post(f"/api/v1/workflows/{wf_id}/executions/{exec_id}/pause")
    assert response.status_code == 200
    assert response.json()["message"] == "Pause signal sent successfully"

    # Resume Execution
    response = await client.post(f"/api/v1/workflows/{wf_id}/executions/{exec_id}/resume")
    assert response.status_code == 200
    assert response.json()["message"] == "Resume signal sent successfully"

    # Cancel Execution
    response = await client.post(f"/api/v1/workflows/{wf_id}/executions/{exec_id}/cancel")
    assert response.status_code == 200
    assert response.json()["message"] == "Cancellation request sent successfully"
