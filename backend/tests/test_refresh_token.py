import pytest
import hashlib
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from app.models.user import User
from app.models.organization import Organization
from app.core.security.password import hash_password
from jose import jwt
from app.core.settings import settings

@pytest.mark.anyio
async def test_refresh_token_scenarios(client: AsyncClient):
    # 1. Setup a test user
    test_email = "refresh_test_user@fluxa.ai"
    user = User(
        email=test_email,
        password_hash=hash_password("verysecurepassword"),
        name="Refresh Test User",
        is_verified=True
    )
    await user.insert()

    # 2. Login and verify access_token and refresh_token are returned
    login_payload = {
        "email": test_email,
        "password": "verysecurepassword"
    }
    resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert resp.status_code == 200
    login_data = resp.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data
    assert login_data["token_type"] == "bearer"

    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]

    # 3. Verify access_token payload has type = access
    access_payload = jwt.decode(
        access_token,
        settings.jwt.secret,
        algorithms=[settings.jwt.algorithm]
    )
    assert access_payload.get("type") == "access"

    # 4. Verify refresh_token payload has type = refresh and a jti
    refresh_payload = jwt.decode(
        refresh_token,
        settings.jwt.secret,
        algorithms=[settings.jwt.algorithm]
    )
    assert refresh_payload.get("type") == "refresh"
    assert "jti" in refresh_payload
    jti = refresh_payload["jti"]

    # Verify DB has hashed record
    db_user = await User.get(user.id)
    assert len(db_user.refresh_token_records) == 1
    record = db_user.refresh_token_records[0]
    assert record.jti == jti
    assert record.token_hash == hashlib.sha256(refresh_token.encode('utf-8')).hexdigest()

    # 5. Refresh with valid token -> 200 OK and rotated tokens
    refresh_payload_req = {
        "refresh_token": refresh_token
    }
    resp = await client.post("/api/v1/auth/refresh/", json=refresh_payload_req)
    assert resp.status_code == 200
    refresh_data = resp.json()
    assert "access_token" in refresh_data
    assert "refresh_token" in refresh_data
    
    new_access_token = refresh_data["access_token"]
    new_refresh_token = refresh_data["refresh_token"]

    # 6. Verify reuse of old refresh token -> Rejected
    resp = await client.post("/api/v1/auth/refresh/", json={"refresh_token": refresh_token})
    assert resp.status_code == 401
    assert "revoked" in resp.json()["detail"].lower() or "reused" in resp.json()["detail"].lower()

    # 7. Access token sent to refresh endpoint -> Rejected
    resp = await client.post("/api/v1/auth/refresh/", json={"refresh_token": access_token})
    assert resp.status_code == 401
    assert "type" in resp.json()["detail"].lower()

    # 8. Malformed refresh token -> Rejected
    resp = await client.post("/api/v1/auth/refresh/", json={"refresh_token": "malformed_token_string"})
    assert resp.status_code == 401

    # 9. Expired refresh token -> Rejected
    from app.core.security.jwt import create_refresh_token
    expired_token, expired_jti = create_refresh_token(str(user.id), expires_delta=timedelta(seconds=-10))
    # inject into user records manually so it's recognized but expired
    db_user = await User.get(user.id)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db_user.refresh_token_records.append({
        "jti": expired_jti,
        "token_hash": hashlib.sha256(expired_token.encode('utf-8')).hexdigest(),
        "created_at": now - timedelta(minutes=10),
        "expires_at": now - timedelta(seconds=10)
    })
    await db_user.save()

    resp = await client.post("/api/v1/auth/refresh/", json={"refresh_token": expired_token})
    assert resp.status_code == 401

    # 10. Refresh token belonging to another user -> Rejected
    another_user = User(
        email="another@fluxa.ai",
        password_hash=hash_password("verysecurepassword"),
        name="Another User",
        is_verified=True
    )
    await another_user.insert()
    another_refresh_token, another_jti = create_refresh_token(str(another_user.id))
    # store in another user's DB records
    another_user.refresh_token_records.append({
        "jti": another_jti,
        "token_hash": hashlib.sha256(another_refresh_token.encode('utf-8')).hexdigest(),
        "created_at": now,
        "expires_at": now + timedelta(days=7)
    })
    await another_user.save()
