import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.organization import Organization
from app.core.security.context import SecurityContext, SecurityContextHolder
from app.core.packages import PackageMarketplace

@pytest.fixture(autouse=True)
def clean_context():
    SecurityContextHolder.clear_context()
    PackageMarketplace.clear()
    yield
    SecurityContextHolder.clear_context()
    PackageMarketplace.clear()

@pytest.mark.anyio
async def test_tenant_isolated_package_installation_lifecycle():
    client = TestClient(app)

    # 1. Create Mock Organizations in DB
    org_a = await Organization.find_one(Organization.slug == "org-a")
    if not org_a:
        org_a = Organization(
            name="Org A",
            slug="org-a",
            owner_id="owner-a",
            settings={}
        )
        await org_a.insert()

    org_b = await Organization.find_one(Organization.slug == "org-b")
    if not org_b:
        org_b = Organization(
            name="Org B",
            slug="org-b",
            owner_id="owner-b",
            settings={}
        )
        await org_b.insert()

    # Define Security Contexts
    from app.core.security.jwt import create_access_token
    token_a = create_access_token(user_id="u-a", organization_id="org-a")
    token_b = create_access_token(user_id="u-b", organization_id="org-b")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    ctx_a = SecurityContext(
        organization_id="org-a", workspace_id="w-1",
        environment_id="e-1", project_id="p-1", user_id="u-a"
    )
    ctx_b = SecurityContext(
        organization_id="org-b", workspace_id="w-1",
        environment_id="e-1", project_id="p-1", user_id="u-b"
    )

    # 2. Query Packages list as Org A -> Check all uninstalled
    SecurityContextHolder.set_context(ctx_a)
    res_list_a = client.get("/api/v1/packages/", headers=headers_a)
    assert res_list_a.status_code == 200
    pkgs_a = res_list_a.json()
    assert len(pkgs_a) > 0
    assert any(p["name"] == "@fluxa/openai-vision" and not p["installed"] for p in pkgs_a)

    # 3. Install Package X on Org A
    res_inst = client.post("/api/v1/packages/install", json={"package_name": "@fluxa/openai-vision"}, headers=headers_a)
    assert res_inst.status_code == 200
    data_inst = res_inst.json()
    assert data_inst["status"] == "installed"
    assert data_inst["installed_metadata"]["status"] == "installed"

    # Verify Org A settings updated
    org_a_updated = await Organization.find_one(Organization.slug == "org-a")
    assert "@fluxa/openai-vision" in org_a_updated.settings["installed_packages"]

    # 4. Shift to Org B and check package list -> Should remain uninstalled
    SecurityContextHolder.set_context(ctx_b)
    res_list_b = client.get("/api/v1/packages/", headers=headers_b)
    assert res_list_b.status_code == 200
    pkgs_b = res_list_b.json()
    assert any(p["name"] == "@fluxa/openai-vision" and not p["installed"] for p in pkgs_b)

    # 5. Shift back to Org A and uninstall
    SecurityContextHolder.set_context(ctx_a)
    res_uninst = client.post("/api/v1/packages/uninstall", json={"package_name": "@fluxa/openai-vision"}, headers=headers_a)
    assert res_uninst.status_code == 200
    assert res_uninst.json()["status"] == "uninstalled"


    # Verify Org A settings updated
    org_a_final = await Organization.find_one(Organization.slug == "org-a")
    assert "@fluxa/openai-vision" not in org_a_final.settings["installed_packages"]
