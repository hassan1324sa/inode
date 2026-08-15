from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field
import logging
from app.core.security.context import SecurityContextHolder, SecurityException

class SecretRef(BaseModel):
    provider: str
    path: str
    version: str = "1"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseSecretProvider(ABC):
    @abstractmethod
    async def get(self, ref: SecretRef) -> str:
        pass

    @abstractmethod
    async def put(self, path: str, value: str) -> SecretRef:
        pass

    @abstractmethod
    async def rotate(self, path: str, new_value: str) -> SecretRef:
        pass

    @abstractmethod
    async def revoke(self, path: str):
        pass


class SecretRedactor:
    """
    Scans and redacts retrieved plaintext secrets from payloads, logging strings,
    and event representations.
    """
    _registered_secrets: Set = set()

    @classmethod
    def register_secret(cls, value: str):
        if value and len(value) > 3:
            cls._registered_secrets.add(value)

    @classmethod
    def redact(cls, data: Any) -> Any:
        if isinstance(data, str):
            res = data
            for sec in cls._registered_secrets:
                if sec in res:
                    res = res.replace(sec, "<redacted>")
            return res
        elif isinstance(data, dict):
            return {k: cls.redact(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.redact(x) for x in data]
        return data

    @classmethod
    def clear(cls):
        cls._registered_secrets.clear()


class VaultSecretProvider(BaseSecretProvider):
    # path -> version -> plaintext (class variables for shared in-memory state)
    _store: Dict[str, Dict[str, str]] = {}
    _revoked_paths: Set[str] = set()

    def __init__(self):
        pass

    def exists(self, path: str) -> bool:
        ctx = SecurityContextHolder.get_current_context()
        if not ctx or not ctx.organization_id:
            return False
        tenant_path = f"{ctx.organization_id}/{path}"
        return tenant_path in self._store and tenant_path not in self._revoked_paths

    async def get(self, ref: SecretRef) -> str:
        # Enforce SecurityContext lookup
        ctx = SecurityContextHolder.get_current_context()
        if not ctx or not ctx.organization_id:
            raise SecurityException("Unauthorized: Missing organization context")
        tenant_path = f"{ctx.organization_id}/{ref.path}"

        if tenant_path in self._revoked_paths:
            raise SecurityException(f"Access Denied: Secret path {ref.path} has been revoked.")

        # Try to load from MongoDB
        try:
            from app.models.credential import Credential
            cred = await Credential.find_one({
                "organization_id": ctx.organization_id,
                "provider": ref.path
            })
            if cred:
                secret_val = decrypt_value(cred.encrypted_data)
                SecretRedactor.register_secret(secret_val)
                return secret_val
        except Exception as e:
            logging.getLogger("fluxa.secrets").warning(f"Database lookup failed for credential {ref.path}, falling back to memory: {e}")

        # Fallback to in-memory store
        versions = self._store.get(tenant_path)
        if not versions or ref.version not in versions:
            raise ValueError(f"Secret version {ref.version} not found at path {ref.path}")

        secret_val = versions[ref.version]
        # Register for safety redaction
        SecretRedactor.register_secret(secret_val)
        return secret_val

    async def put(self, path: str, value: str) -> SecretRef:
        ctx = SecurityContextHolder.get_current_context()
        if not ctx or not ctx.organization_id:
            raise SecurityException("Unauthorized: Missing organization context")
        tenant_path = f"{ctx.organization_id}/{path}"

        if tenant_path in self._revoked_paths:
            self._revoked_paths.remove(tenant_path)

        # Store in MongoDB
        try:
            from app.models.credential import Credential
            encrypted_val = encrypt_value(value)
            
            cred = await Credential.find_one({
                "organization_id": ctx.organization_id,
                "provider": path
            })
            if cred:
                cred.encrypted_data = encrypted_val
                await cred.save()
            else:
                cred = Credential(
                    organization_id=ctx.organization_id,
                    provider=path,
                    encrypted_data=encrypted_val
                )
                await cred.insert()
        except Exception as e:
            logging.getLogger("fluxa.secrets").warning(f"Database save failed for credential {path}: {e}")

        # Sync to in-memory store
        if tenant_path not in self._store:
            self._store[tenant_path] = {}
        
        version = str(len(self._store[tenant_path]) + 1)
        self._store[tenant_path][version] = value
        
        return SecretRef(provider="vault", path=path, version=version)

    async def rotate(self, path: str, new_value: str) -> SecretRef:
        return await self.put(path, new_value)

    async def revoke(self, path: str):
        ctx = SecurityContextHolder.get_current_context()
        if not ctx or not ctx.organization_id:
            raise SecurityException("Unauthorized: Missing organization context")
        tenant_path = f"{ctx.organization_id}/{path}"
        self._revoked_paths.add(tenant_path)

        # Delete from MongoDB
        try:
            from app.models.credential import Credential
            cred = await Credential.find_one({
                "organization_id": ctx.organization_id,
                "provider": path
            })
            if cred:
                await cred.delete()
        except Exception as e:
            logging.getLogger("fluxa.secrets").warning(f"Database deletion failed for credential {path}: {e}")


def encrypt_value(value: str) -> str:
    import base64
    import hashlib
    from cryptography.fernet import Fernet
    from app.core.settings import settings
    
    key_material = settings.jwt.secret.encode()
    derived_key = hashlib.sha256(key_material).digest()
    fernet_key = base64.urlsafe_b64encode(derived_key)
    f = Fernet(fernet_key)
    return f.encrypt(value.encode()).decode()

def decrypt_value(encrypted_value: str) -> str:
    import base64
    import hashlib
    from cryptography.fernet import Fernet
    from app.core.settings import settings
    
    key_material = settings.jwt.secret.encode()
    derived_key = hashlib.sha256(key_material).digest()
    fernet_key = base64.urlsafe_b64encode(derived_key)
    f = Fernet(fernet_key)
    try:
        return f.decrypt(encrypted_value.encode()).decode()
    except Exception:
        # Fallback to plain text in case of unencrypted entries
        return encrypted_value
