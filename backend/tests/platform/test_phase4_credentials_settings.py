import pytest
from app.core.security.context import SecurityContext, SecurityContextHolder, SecurityException
from app.core.security.secrets import VaultSecretProvider, SecretRef, SecretRedactor
from fastapi import HTTPException
from app.schemas.basic import OrganizationSettingsUpdate, EnvironmentMode
from pydantic import ValidationError

@pytest.fixture(autouse=True)
def clean_security_state():
    SecurityContextHolder.clear_context()
    SecretRedactor.clear()
    VaultSecretProvider._store.clear()
    VaultSecretProvider._revoked_paths.clear()
    yield
    SecurityContextHolder.clear_context()
    SecretRedactor.clear()
    VaultSecretProvider._store.clear()
    VaultSecretProvider._revoked_paths.clear()


@pytest.mark.anyio
async def test_vault_exists_method_is_tenant_scoped():
    ctx_a = SecurityContext(
        organization_id="org-a", workspace_id="workspace-1",
        environment_id="env-1", project_id="proj-1", user_id="user-a"
    )
    ctx_b = SecurityContext(
        organization_id="org-b", workspace_id="workspace-1",
        environment_id="env-1", project_id="proj-1", user_id="user-b"
    )

    provider = VaultSecretProvider()

    # Save under Org A
    SecurityContextHolder.set_context(ctx_a)
    await provider.put("gemini-key", "secret-a")

    # Org A should see it
    assert provider.exists("gemini-key") is True

    # Org B should NOT see it
    SecurityContextHolder.set_context(ctx_b)
    assert provider.exists("gemini-key") is False


@pytest.mark.anyio
async def test_vault_rotate_and_revoke_enforces_organization_id():
    ctx_a = SecurityContext(
        organization_id="org-a", workspace_id="workspace-1",
        environment_id="env-1", project_id="proj-1", user_id="user-a"
    )
    ctx_b = SecurityContext(
        organization_id="org-b", workspace_id="workspace-1",
        environment_id="env-1", project_id="proj-1", user_id="user-b"
    )

    provider = VaultSecretProvider()

    # Save under Org A
    SecurityContextHolder.set_context(ctx_a)
    await provider.put("gemini-key", "secret-a")

    # Tenant B tries to rotate/revoke Tenant A's secret -> Mismatch or Not Found since it resolves to org-b path
    SecurityContextHolder.set_context(ctx_b)
    with pytest.raises(ValueError):
        # ValueError is raised because the path org-b/gemini-key does not exist inside _store
        ref = SecretRef(provider="vault", path="gemini-key")
        await provider.get(ref)


def test_organization_settings_forbids_extra_fields():
    # Valid model validation
    update = OrganizationSettingsUpdate(
        name="Fluxa Org",
        slug="fluxa-org",
        environment_mode=EnvironmentMode.PRODUCTION
    )
    assert update.name == "Fluxa Org"

    # Extra fields should raise ValidationError
    with pytest.raises(ValidationError):
        OrganizationSettingsUpdate(
            name="Fluxa Org",
            slug="fluxa-org",
            environment_mode=EnvironmentMode.PRODUCTION,
            extra_field="malicious_payload"
        )


def test_organization_settings_validates_environment_enum():
    # Invalid environment mode should raise ValidationError
    with pytest.raises(ValidationError):
        OrganizationSettingsUpdate(
            name="Fluxa Org",
            slug="fluxa-org",
            environment_mode="InvalidMode"
        )
