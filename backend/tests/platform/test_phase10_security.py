import pytest
import asyncio
from app.core.security.context import SecurityContext, SecurityContextHolder, SecurityException
from app.core.security.secrets import VaultSecretProvider, SecretRef, SecretRedactor
from app.core.security.policies import LocalPolicyEngine, PolicyRequest, OPAPolicyEngine, CedarPolicyEngine
from app.core.security.isolation import TenantScopedResource, TenantScopedRepository, WorkerIsolationManager
from app.core.security.audit import SecurityAuditLogger, AuditEvent

@pytest.fixture(autouse=True)
def clean_security_state():
    import os
    orig_bootstrap = os.environ.pop("FLUXA_SYSTEM_BOOTSTRAP", None)
    SecurityContextHolder.clear_context()
    SecretRedactor.clear()
    SecurityAuditLogger.clear()
    yield
    SecurityContextHolder.clear_context()
    SecretRedactor.clear()
    SecurityAuditLogger.clear()
    if orig_bootstrap:
        os.environ["FLUXA_SYSTEM_BOOTSTRAP"] = orig_bootstrap


@pytest.mark.anyio
async def test_missing_security_context_fails_closed():
    # 1. Secret Provider fails closed
    provider = VaultSecretProvider()
    ref = SecretRef(provider="vault", path="api_key")
    with pytest.raises(SecurityException, match="Missing security context"):
        await provider.get(ref)

    # 2. Policy Engine fails closed
    policy_engine = LocalPolicyEngine()
    req = PolicyRequest(
        subject="user-1", action="read", resource="doc-1",
        tenant_id="t-1", workspace_id="w-1", environment_id="env-1"
    )
    with pytest.raises(SecurityException, match="Missing security context"):
        await policy_engine.evaluate(req)

    # 3. Repository fails closed
    repo = TenantScopedRepository()
    with pytest.raises(SecurityException, match="Missing security context"):
        repo.get("res-1")


def test_cross_tenant_access_denied():
    ctx_a = SecurityContext(
        organization_id="tenant-a", workspace_id="workspace-1",
        environment_id="env-1", project_id="proj-1", user_id="user-a"
    )
    ctx_b = SecurityContext(
        organization_id="tenant-b", workspace_id="workspace-1",
        environment_id="env-1", project_id="proj-1", user_id="user-b"
    )

    repo = TenantScopedRepository()

    # Save resource as Tenant A
    SecurityContextHolder.set_context(ctx_a)
    res_a = TenantScopedResource(resource_id="res-1", tenant_id="tenant-a", workspace_id="workspace-1", data="sensitive")
    repo.save(res_a)

    # Attempt save as Tenant B on Tenant A's scope -> DENY
    SecurityContextHolder.set_context(ctx_b)
    res_b = TenantScopedResource(resource_id="res-2", tenant_id="tenant-a", workspace_id="workspace-1", data="hijack")
    with pytest.raises(SecurityException, match="Cross-tenant write violation"):
        repo.save(res_b)

    # Attempt retrieve Tenant A resource as Tenant B -> DENY
    with pytest.raises(SecurityException, match="Cross-tenant access violation"):
        repo.get("res-1")


@pytest.mark.anyio
async def test_secrets_rotation_revocation_and_redaction():
    ctx = SecurityContext(
        organization_id="tenant-a", workspace_id="workspace-1",
        environment_id="env-1", project_id="proj-1", user_id="user-a"
    )
    SecurityContextHolder.set_context(ctx)

    provider = VaultSecretProvider()
    ref = await provider.put("db_pass", "super_secret_password_123")
    
    # 1. Fetch & Verify Redaction registration
    plaintext = await provider.get(ref)
    assert plaintext == "super_secret_password_123"

    log_msg = f"Database password set to: {plaintext}"
    redacted_log = SecretRedactor.redact(log_msg)
    assert "super_secret_password_123" not in redacted_log
    assert "<redacted>" in redacted_log

    # 2. Rotation check
    new_ref = await provider.rotate("db_pass", "new_secret_456")
    assert new_ref.version == "2"
    assert await provider.get(new_ref) == "new_secret_456"

    # Redaction registry contains both secrets
    assert SecretRedactor.redact("new_secret_456") == "<redacted>"

    # 3. Revocation check
    await provider.revoke("db_pass")
    with pytest.raises(SecurityException, match="revoked"):
        await provider.get(new_ref)


@pytest.mark.anyio
async def test_policy_decisions_and_fail_closed():
    ctx = SecurityContext(
        organization_id="tenant-a", workspace_id="w-1",
        environment_id="env-1", project_id="proj-1", user_id="user-a"
    )
    SecurityContextHolder.set_context(ctx)

    # Local Engine tests
    engine = LocalPolicyEngine()
    req_allow = PolicyRequest(
        subject="user-a", action="read", resource="doc-1",
        tenant_id="tenant-a", workspace_id="w-1", environment_id="env-1"
    )
    dec_allow = await engine.evaluate(req_allow)
    assert dec_allow.effect == "ALLOW"

    req_deny = req_allow.model_copy(update={"action": "restricted_action"})
    dec_deny = await engine.evaluate(req_deny)
    assert dec_deny.effect == "DENY"

    req_approval = req_allow.model_copy(update={"action": "approval_required_action"})
    dec_approval = await engine.evaluate(req_approval)
    assert dec_approval.effect == "REQUIRE_APPROVAL"

    # OPA/Cedar Engine Fail-Closed on missing config/endpoint
    opa = OPAPolicyEngine(opa_url=None)
    dec_opa = await opa.evaluate(req_allow)
    assert dec_opa.effect == "DENY"
    assert "Fail Closed" in dec_opa.reason

    cedar = CedarPolicyEngine(cedar_url=None)
    dec_cedar = await cedar.evaluate(req_allow)
    assert dec_cedar.effect == "DENY"
    assert "Fail Closed" in dec_cedar.reason


def test_worker_isolation_enforcement():
    ctx_a = SecurityContext(
        organization_id="tenant-a", workspace_id="w-1",
        environment_id="env-1", project_id="proj-1", user_id="user-a"
    )
    SecurityContextHolder.set_context(ctx_a)

    def dummy_task(x):
        return x * 2

    # Match bound context -> success
    res = WorkerIsolationManager.execute_worker_task("tenant-a", "w-1", dummy_task, 5)
    assert res == 10

    # Mismatch bound context -> DENY
    with pytest.raises(SecurityException, match="Worker execution context violation"):
        WorkerIsolationManager.execute_worker_task("tenant-b", "w-1", dummy_task, 5)


def test_security_audit_logging():
    ctx = SecurityContext(
        organization_id="tenant-a", workspace_id="w-1",
        environment_id="env-1", project_id="proj-1", user_id="user-a"
    )
    SecurityContextHolder.set_context(ctx)

    # Register secret to redact
    SecretRedactor.register_secret("secret_token")

    event = AuditEvent(
        actor="user-a",
        tenant_id="tenant-a",
        workspace_id="w-1",
        action="read",
        resource="credentials",
        decision="ALLOW",
        metadata={"token_used": "secret_token", "normal": "safe"}
    )
    
    SecurityAuditLogger.log_event(event)
    logs = SecurityAuditLogger.get_logs()
    
    assert len(logs) == 1
    assert logs[0].metadata["token_used"] == "<redacted>"
    assert logs[0].metadata["normal"] == "safe"


# Helper for running async methods in sync pytest blocks
def asyncio_run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)
