import pytest
from app.main import app
from app.core.security.context import SecurityContext, SecurityContextHolder, SecurityException
from app.core.registry.provider_registry import ProviderRegistry, ProviderMetadata
from app.core.providers.mcp import MCPProviderManager, MCPToolSchema, redact_url

@pytest.fixture(autouse=True)
def clean_registry():
    import os
    orig_bootstrap = os.environ.pop("FLUXA_SYSTEM_BOOTSTRAP", None)
    ProviderRegistry.clear()
    SecurityContextHolder.clear_context()
    yield
    ProviderRegistry.clear()
    SecurityContextHolder.clear_context()
    if orig_bootstrap:
        os.environ["FLUXA_SYSTEM_BOOTSTRAP"] = orig_bootstrap

def test_url_credential_redaction():
    # Wipes usernames and passwords from URLs
    secret_url = "http://admin:supersecretpassword@localhost:8080/mcp"
    redacted = redact_url(secret_url)
    assert "supersecretpassword" not in redacted
    assert "admin" not in redacted
    assert redacted == "http://localhost:8080/mcp"

@pytest.mark.anyio
async def test_mcp_fail_closed_without_context():
    # If no context is set, registering or listing raises SecurityException
    tool = MCPToolSchema(name="t1", description="desc")
    with pytest.raises(SecurityException):
        MCPProviderManager.register_mcp_server("postgres", "http://localhost", [tool])

    with pytest.raises(SecurityException):
        MCPProviderManager.get_mcp_driver("postgres")

    with pytest.raises(SecurityException):
        MCPProviderManager.list_mcp_drivers()

@pytest.mark.anyio
async def test_mcp_tenant_isolation_org_a_vs_org_b():
    ctx_a = SecurityContext(
        organization_id="org-a", workspace_id="w-1",
        environment_id="e-1", project_id="p-1", user_id="u-a"
    )
    ctx_b = SecurityContext(
        organization_id="org-b", workspace_id="w-1",
        environment_id="e-1", project_id="p-1", user_id="u-b"
    )

    tool = MCPToolSchema(name="query_db", description="SQL tool")

    # 1. Register under Org A context
    SecurityContextHolder.set_context(ctx_a)
    MCPProviderManager.register_mcp_server("postgres_mcp", "http://localhost:8001/mcp", [tool])

    # Org A should find the driver
    drv_a = MCPProviderManager.get_mcp_driver("postgres_mcp")
    assert drv_a is not None
    assert drv_a.server_url == "http://localhost:8001/mcp"

    # Org A list drivers should contain postgres_mcp
    drivers_a = MCPProviderManager.list_mcp_drivers()
    assert any(d.name == "postgres_mcp" for d in drivers_a)

    # 2. Shift to Org B context
    SecurityContextHolder.set_context(ctx_b)

    # Org B should NOT be able to retrieve Org A's driver
    drv_b = MCPProviderManager.get_mcp_driver("postgres_mcp")
    assert drv_b is None

    # Org B list drivers should NOT contain postgres_mcp
    drivers_b = MCPProviderManager.list_mcp_drivers()
    assert not any(d.name == "postgres_mcp" for d in drivers_b)

@pytest.mark.anyio
async def test_mcp_explicit_global_registration():
    ctx_a = SecurityContext(
        organization_id="org-a", workspace_id="w-1",
        environment_id="e-1", project_id="p-1", user_id="u-a"
    )
    ctx_b = SecurityContext(
        organization_id="org-b", workspace_id="w-1",
        environment_id="e-1", project_id="p-1", user_id="u-b"
    )

    # Explicitly register a global driver (simulating trusted system bootstrap)
    meta = ProviderMetadata(name="global_fs", type="mcp", capabilities=["tool:read_file"])
    from app.core.providers.mcp import MCPClientDriver
    driver = MCPClientDriver(server_url="stdio://filesystem")
    
    # Global registration bypassing get_org_prefix (explicitly called)
    ProviderRegistry.register_global(meta, driver)

    # Both Org A and Org B should be able to retrieve the global driver
    SecurityContextHolder.set_context(ctx_a)
    drv_a = MCPProviderManager.get_mcp_driver("global_fs")
    assert drv_a is not None
    assert drv_a.server_url == "stdio://filesystem"

    SecurityContextHolder.set_context(ctx_b)
    drv_b = MCPProviderManager.get_mcp_driver("global_fs")
    assert drv_b is not None
    assert drv_b.server_url == "stdio://filesystem"
