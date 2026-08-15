import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from app.core.settings import settings
from app.core.security.context import SecurityContext

SECRET_KEY = settings.jwt.secret
ALGORITHM = settings.jwt.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt.access_token_expire_minutes

from typing import Optional, Dict, Any, Tuple

def create_access_token(
    user_id: str,
    organization_id: str,
    workspace_id: str = "default-w",
    environment_id: str = "default-e",
    project_id: str = "default-p",
    expires_delta: Optional[timedelta] = None
) -> str:
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.jwt.access_token_expire_minutes)
    
    to_encode = {
        "sub": user_id,
        "org_id": organization_id,
        "ws_id": workspace_id,
        "env_id": environment_id,
        "proj_id": project_id,
        "iat": now,
        "exp": expire,
        "type": "access",
        "jti": str(uuid.uuid4())
    }
    encoded_jwt = jwt.encode(to_encode, settings.jwt.secret, algorithm=settings.jwt.algorithm)
    return encoded_jwt

def create_refresh_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, str]:
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=7)
    
    jti = str(uuid.uuid4())
    to_encode = {
        "sub": user_id,
        "type": "refresh",
        "jti": jti,
        "iat": now,
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, settings.jwt.secret, algorithm=settings.jwt.algorithm)
    return encoded_jwt, jti

def decode_access_token(token: str) -> SecurityContext:
    try:
        # Explicitly decode with ONLY the configured algorithm to prevent algorithm switching attacks
        payload = jwt.decode(
            token, 
            settings.jwt.secret, 
            algorithms=[settings.jwt.algorithm],
            options={"require_exp": True, "require_iat": True}
        )
        user_id: str = payload.get("sub")
        org_id: str = payload.get("org_id")
        ws_id: str = payload.get("ws_id", "default-w")
        env_id: str = payload.get("env_id", "default-e")
        proj_id: str = payload.get("proj_id", "default-p")
        token_type: str = payload.get("type")
        
        if token_type != "access":
            raise JWTError("Invalid token type for access token")
        if user_id is None or org_id is None:
            raise JWTError("Invalid token payload: missing sub or org_id")
            
        return SecurityContext(
            organization_id=org_id,
            workspace_id=ws_id,
            environment_id=env_id,
            project_id=proj_id,
            user_id=user_id
        )
    except JWTError as e:
        raise ValueError(f"Invalid or expired JWT token: {str(e)}")

