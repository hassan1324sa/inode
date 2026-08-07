import pytest
import os
import shutil
import tempfile
from app.core.packages import (
    PackageManifest,
    PackageSecurityManager,
    PackageCompatibilityManager,
    PackageMarketplace
)
from app.core.providers.mcp import MCPProviderManager, MCPToolSchema
from app.cli import FluxaCLI
from app.core.registry.provider_registry import ProviderRegistry

@pytest.fixture(autouse=True)
def clean_marketplace():
    import os
    os.environ["FLUXA_SYSTEM_BOOTSTRAP"] = "true"
    PackageMarketplace.clear()
    ProviderRegistry.clear()
    yield
    PackageMarketplace.clear()
    ProviderRegistry.clear()

# --- SECURITY & SIGNATURE TESTS ---

def test_package_hash_and_signature_verification():
    manifest = PackageManifest(
        name="fluxa-analytics",
        version="1.2.0",
        author="official",
        publisher="fluxa-official",
        engines={"fluxa": ">=1.0.0"},
        nodes=["analytics_node"]
    )
    secret_key = "super-secret-publisher-key"
    
    # Sign manifest
    sig = PackageSecurityManager.sign_manifest(manifest, secret_key)
    assert manifest.hash is not None
    assert manifest.signature == sig

    # Valid check
    report = PackageSecurityManager.verify_package(manifest, secret_key)
    assert report.is_valid is True
    assert report.manifest_hash_valid is True
    assert report.signature_valid is True
    assert report.publisher_trusted is True

    # Tamper with manifest name to break hash/signature
    manifest.name = "fluxa-tampered"
    tampered_report = PackageSecurityManager.verify_package(manifest, secret_key)
    assert tampered_report.is_valid is False
    assert "Manifest hash mismatch" in tampered_report.errors[0]

# --- COMPATIBILITY TESTS ---

def test_package_compatibility_check():
    manifest = PackageManifest(
        name="fluxa-ml",
        version="2.0.0",
        engines={
            "fluxa": ">=1.2.0",
            "python": ">=3.10"
        }
    )

    # Compatible runtime
    res_ok = PackageCompatibilityManager.check_compatibility(
        manifest,
        {"fluxa": "1.3.0", "python": "3.12.0"}
    )
    assert res_ok.is_compatible is True

    # Incompatible runtime (fluxa too old)
    res_fail = PackageCompatibilityManager.check_compatibility(
        manifest,
        {"fluxa": "1.0.0", "python": "3.12.0"}
    )
    assert res_fail.is_compatible is False
    assert "does not satisfy constraint" in res_fail.incompatible_reasons[0]

# --- MARKETPLACE & DEPENDENCY RESOLUTION TESTS ---

def test_marketplace_dependency_resolution_and_installation():
    base_pkg = PackageManifest(
        name="fluxa-core-utils",
        version="1.0.0",
        author="fluxa-official",
        publisher="fluxa-official",
        engines={"fluxa": ">=1.0"}
    )
    ml_pkg = PackageManifest(
        name="fluxa-ml-suite",
        version="1.0.0",
        author="fluxa-official",
        publisher="fluxa-official",
        dependencies=["fluxa-core-utils>=1.0"],
        engines={"fluxa": ">=1.0"}
    )
    PackageMarketplace.publish(base_pkg)
    PackageMarketplace.publish(ml_pkg)

    # Dependency resolution
    resolved = PackageMarketplace.resolve_dependencies("fluxa-ml-suite")
    names = [p.name for p in resolved]
    assert names == ["fluxa-core-utils", "fluxa-ml-suite"]

    # Installation
    report = PackageMarketplace.install(
        "fluxa-ml-suite",
        runtime_engines={"fluxa": "1.3.0"}
    )
    assert report.success is True
    assert "fluxa-core-utils" in report.installed_packages
    assert "fluxa-ml-suite" in report.installed_packages

# --- MCP PROVIDER REGISTRY TESTS ---

@pytest.mark.anyio
async def test_mcp_provider_registry_integration():
    tool_schema = MCPToolSchema(
        name="sql_query",
        description="Execute a read-only SQL query",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}}
    )

    async def custom_handler(tool_name, args):
        return {"result": f"Executed {tool_name} with {args.get('query')}"}

    driver = MCPProviderManager.register_mcp_server(
        name="postgres_mcp",
        server_url="http://localhost:8080/mcp",
        tools=[tool_schema],
        tool_handler=custom_handler
    )

    retrieved_driver = MCPProviderManager.get_mcp_driver("postgres_mcp")
    assert retrieved_driver is not None
    assert len(retrieved_driver.list_tools()) == 1
    assert retrieved_driver.list_tools()[0].name == "sql_query"

    output = await retrieved_driver.call_tool("sql_query", {"query": "SELECT 1"})
    assert "Executed sql_query" in output["result"]

# --- CLI TESTS ---

def test_fluxa_cli_init_publish_install():
    temp_dir = tempfile.mkdtemp()
    try:
        init_res = FluxaCLI.init(temp_dir, project_name="my-test-project")
        assert init_res["status"] == "success"
        assert os.path.exists(os.path.join(temp_dir, "fluxa.yaml"))

        pkg = PackageManifest(
            name="cli-test-pkg",
            version="0.1.0",
            publisher="fluxa-official",
            engines={"fluxa": ">=1.0"}
        )
        pub_res = FluxaCLI.publish(pkg, secret_key="my-key")
        assert pub_res["status"] == "success"
        assert pub_res["signature"] is not None

        install_res = FluxaCLI.install("cli-test-pkg", require_signature=True, secret_key="my-key")
        assert install_res.success is True
        assert "cli-test-pkg" in install_res.installed_packages

        verify_res = FluxaCLI.verify("cli-test-pkg", secret_key="my-key")
        assert verify_res["is_valid"] is True
    finally:
        shutil.rmtree(temp_dir)
