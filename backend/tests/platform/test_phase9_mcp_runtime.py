import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.organization import Organization
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.core.security.context import SecurityContext, SecurityContextHolder, SecurityException
from app.core.providers.mcp import MCPProviderManager, MCPToolSchema
from app.core.agents.tools import MCPTool

from app.core.registry.provider_registry import ProviderRegistry

@pytest.fixture(autouse=True)
def clean_context():
    SecurityContextHolder.clear_context()
    ProviderRegistry.clear()
    yield
    SecurityContextHolder.clear_context()
    ProviderRegistry.clear()

@pytest.mark.anyio
async def test_workflow_ownership_and_mcp_runtime_isolation():
    client = TestClient(app)

    # 1. Setup Mock Organizations
    org_a = await Organization.find_one(Organization.slug == "org-a")
    if not org_a:
        org_a = Organization(name="Org A", slug="org-a", owner_id="owner-a", settings={})
        await org_a.insert()

    org_b = await Organization.find_one(Organization.slug == "org-b")
    if not org_b:
        org_b = Organization(name="Org B", slug="org-b", owner_id="owner-b", settings={})
        await org_b.insert()

    # 2. Setup Workflows
    wf_a = Workflow(organization_id="org-a", name="Workflow A", current_version="v1", status="Draft")
    await wf_a.insert()
    wv_a = WorkflowVersion(workflow_id=str(wf_a.id), version="v1", nodes=[], edges=[], created_by="system")
    await wv_a.insert()

    wf_b = Workflow(organization_id="org-b", name="Workflow B", current_version="v1", status="Draft")
    await wf_b.insert()
    wv_b = WorkflowVersion(workflow_id=str(wf_b.id), version="v1", nodes=[], edges=[], created_by="system")
    await wv_b.insert()

    # Define Security Contexts via JWT tokens and objects
    from app.core.security.jwt import create_access_token
    token_a = create_access_token(user_id="u-a", organization_id="org-a")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    ctx_a = SecurityContext(
        organization_id="org-a", workspace_id="w-1",
        environment_id="e-1", project_id="p-1", user_id="u-a"
    )
    ctx_b = SecurityContext(
        organization_id="org-b", workspace_id="w-1",
        environment_id="e-1", project_id="p-1", user_id="u-b"
    )


    # --- WORKFLOW ID ENUMERATION & OWNERSHIP TESTS ---
    
    # Org A tries to GET Org B's workflow -> Deny (403 Mismatch)
    res_get = client.get(f"/api/v1/workflows/{str(wf_b.id)}", headers=headers_a)
    assert res_get.status_code == 403

    # Org A tries to UPDATE Org B's workflow -> Deny (403 Mismatch)
    res_put = client.put(f"/api/v1/workflows/{str(wf_b.id)}", json={"name": "Hacked"}, headers=headers_a)
    assert res_put.status_code == 403

    # Org A tries to DELETE Org B's workflow -> Deny (403 Mismatch)
    res_del = client.delete(f"/api/v1/workflows/{str(wf_b.id)}", headers=headers_a)
    assert res_del.status_code == 403

    # Org A tries to EXECUTE Org B's workflow -> Deny (403 Mismatch)
    res_exec = client.post(f"/api/v1/workflows/{str(wf_b.id)}/execute", json={"trigger_type": "manual"}, headers=headers_a)
    assert res_exec.status_code == 403

    # Org A list workflows should only return Org A's workflow
    res_list = client.get("/api/v1/workflows/", headers=headers_a)
    assert res_list.status_code == 200
    listed_wfs = res_list.json()
    assert len(listed_wfs) > 0

    assert all(w["organization_id"] == "org-a" for w in listed_wfs)

    # --- MCP RUNTIME ISOLATION TESTS ---

    tool_schema = MCPToolSchema(name="query_db", description="SQL tool")

    # Register MCP server under Org B
    SecurityContextHolder.set_context(ctx_b)
    MCPProviderManager.register_mcp_server("postgres_mcp", "http://localhost:8001/mcp", [tool_schema])

    # Org B executes tool -> OK
    mcp_tool_b = MCPTool(server_name="postgres_mcp", tool_name="query_db")
    res_b = await mcp_tool_b.execute({"query": "SELECT 1"}, None)
    assert res_b["status"] == "success"

    # Shift to Org A context and try to execute Org B's tool -> Deny
    SecurityContextHolder.set_context(ctx_a)
    with pytest.raises(SecurityException) as exc_info:
        await mcp_tool_b.execute({"query": "SELECT 1"}, None)
    assert "not registered or not authorized" in str(exc_info.value)

    # Missing context completely -> Deny
    SecurityContextHolder.clear_context()
    with pytest.raises(SecurityException) as exc_info_missing:
        await mcp_tool_b.execute({"query": "SELECT 1"}, None)
    assert "Missing organization context" in str(exc_info_missing.value)
