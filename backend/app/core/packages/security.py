import hmac
import hashlib
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.core.packages.package import PackageManifest

class PackageSecurityReport(BaseModel):
    is_valid: bool
    manifest_hash_valid: bool
    signature_valid: bool
    publisher_trusted: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class PackageSecurityManager:
    """
    Handles cryptographic signing, verification, and publisher trust for Fluxa packages.
    """
    _trusted_publishers: set = {"fluxa-official", "fluxa-community", "enterprise-trusted"}

    @classmethod
    def sign_manifest(cls, manifest: PackageManifest, secret_key: str) -> str:
        """
        Signs the canonical hash of the manifest using HMAC-SHA256 with the publisher secret key.
        """
        manifest_hash = manifest.compute_hash()
        manifest.hash = manifest_hash
        signature = hmac.new(
            secret_key.encode("utf-8"),
            manifest_hash.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        manifest.signature = signature
        return signature

    @classmethod
    def verify_signature(cls, manifest: PackageManifest, secret_key: str) -> bool:
        """
        Verifies that the signature matches the manifest hash and secret key.
        """
        if not manifest.hash or not manifest.signature:
            return False
        expected_sig = hmac.new(
            secret_key.encode("utf-8"),
            manifest.hash.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(manifest.signature, expected_sig)

    @classmethod
    def add_trusted_publisher(cls, publisher: str):
        cls._trusted_publishers.add(publisher)

    @classmethod
    def verify_package(
        cls,
        manifest: PackageManifest,
        secret_key: Optional[str] = None
    ) -> PackageSecurityReport:
        """
        Performs a full security verification on a package manifest:
        1. Hash integrity
        2. Signature validity (if secret_key provided or present)
        3. Publisher trust
        """
        errors = []
        warnings = []
        
        # 1. Hash Integrity
        computed_hash = manifest.compute_hash()
        if manifest.hash and manifest.hash != computed_hash:
            errors.append(f"Manifest hash mismatch: expected {manifest.hash}, computed {computed_hash}")
            hash_valid = False
        elif not manifest.hash:
            warnings.append("Manifest has no precomputed hash.")
            hash_valid = True
        else:
            hash_valid = True

        # 2. Signature Validation
        sig_valid = True
        if secret_key:
            if not manifest.signature:
                errors.append("Package has no signature to verify against provided key.")
                sig_valid = False
            else:
                sig_valid = cls.verify_signature(manifest, secret_key)
                if not sig_valid:
                    errors.append("Package signature verification failed.")
        elif not manifest.signature:
            warnings.append("Package is unsigned.")

        # 3. Publisher Trust
        publisher = manifest.publisher or manifest.author or "unknown"
        pub_trusted = publisher in cls._trusted_publishers
        if not pub_trusted:
            warnings.append(f"Publisher '{publisher}' is not in the trusted publishers list.")

        is_valid = len(errors) == 0

        return PackageSecurityReport(
            is_valid=is_valid,
            manifest_hash_valid=hash_valid,
            signature_valid=sig_valid,
            publisher_trusted=pub_trusted,
            errors=errors,
            warnings=warnings
        )
