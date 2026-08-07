import pytest
from httpx import AsyncClient
from app.models.user import User
from app.models.organization import Organization
from app.core.security.password import verify_password
from jose import jwt
from app.core.settings import settings

@pytest.mark.anyio
async def test_password_policy_and_hashing(client: AsyncClient):
    # Test short password (< 8 chars)
    payload_short = {
        "email": "short@fluxa.ai",
        "password": "short",
        "name": "Short Pass User"
    }
    resp = await client.post("/api/v1/auth/register", json=payload_short)
    assert resp.status_code == 400 or resp.status_code == 422  # validation error

    # Test empty password
    payload_empty = {
        "email": "empty@fluxa.ai",
        "password": "",
        "name": "Empty Pass User"
    }
    resp = await client.post("/api/v1/auth/register", json=payload_empty)
    assert resp.status_code == 400 or resp.status_code == 422

    # Test successful registration
    payload_success = {
        "email": "correct@fluxa.ai",
        "password": "securepassword123",
        "name": "Valid User"
    }
    resp = await client.post("/api/v1/auth/register", json=payload_success)
    assert resp.status_code == 200
    reg_data = resp.json()
    assert reg_data["email"] == "correct@fluxa.ai"

    # Verify password is NOT stored as plaintext
    db_user = await User.find_one(User.email == "correct@fluxa.ai")
    assert db_user is not None
    assert db_user.password_hash != "securepassword123"
    assert verify_password("securepassword123", db_user.password_hash)

@pytest.mark.anyio
async def test_login_flow(client: AsyncClient):
    # Setup user
    from app.core.security.password import hash_password
    user = User(
        email="login_test@fluxa.ai",
        password_hash=hash_password("mysecretpassword"),
        name="Login Test User",
        is_verified=True
    )
    await user.insert()

    # Login with wrong password
    login_payload_wrong = {
        "email": "login_test@fluxa.ai",
        "password": "wrongpassword"
    }
    resp = await client.post("/api/v1/auth/login", json=login_payload_wrong)
    assert resp.status_code == 401

    # Login with correct password
    login_payload_correct = {
        "email": "login_test@fluxa.ai",
        "password": "mysecretpassword"
    }
    resp = await client.post("/api/v1/auth/login", json=login_payload_correct)
    assert resp.status_code == 200
    login_data = resp.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"

@pytest.mark.anyio
async def test_jwt_validation_and_tampering(client: AsyncClient):
    # Create valid token
    from app.core.security.jwt import create_access_token
    token = create_access_token(user_id="usr_123", organization_id="org_123")

    # Access protected health/docs endpoint (public routes don't require token, so let's hit a protected route like /organizations/)
    # But first let's try with missing token
    resp = await client.get("/api/v1/organizations/")
    assert resp.status_code == 401
    assert "Missing or invalid authorization header" in resp.json()["message"]

    # Access with valid token
    resp = await client.get("/api/v1/organizations/", headers={"Authorization": f"Bearer {token}"})
    # Since we have no orgs in DB, it returns empty list but status must be 200
    assert resp.status_code == 200

    # Access with tampered token (change a character)
    tampered_token = token[:-5] + "aaaaa"
    resp = await client.get("/api/v1/organizations/", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp.status_code == 401
    assert "Invalid or expired JWT token" in resp.json()["message"]

    # Access with invalid algorithm (e.g. none) using manually constructed token
    import base64
    import json
    header_b64 = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps({"sub": "usr_123", "org_id": "org_123", "iat": 1500000000, "exp": 2500000000}).encode()).decode().rstrip("=")
    none_token = f"{header_b64}.{payload_b64}."
    resp = await client.get("/api/v1/organizations/", headers={"Authorization": f"Bearer {none_token}"})
    assert resp.status_code == 401

    # Access with alternative but unconfigured algorithm (e.g. HS384)
    hs384_token = jwt.encode({"sub": "usr_123", "org_id": "org_123", "iat": 1500000000, "exp": 2500000000}, settings.jwt.secret, algorithm="HS384")
    resp = await client.get("/api/v1/organizations/", headers={"Authorization": f"Bearer {hs384_token}"})
    assert resp.status_code == 401

