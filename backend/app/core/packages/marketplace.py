from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
from app.core.packages.package import PackageManifest
from app.core.packages.security import PackageSecurityManager, PackageSecurityReport
from app.core.packages.compatibility import PackageCompatibilityManager, CompatibilityResult

class InstallationReport(BaseModel):
    success: bool
    installed_packages: List[str] = Field(default_factory=list)
    security_reports: Dict[str, PackageSecurityReport] = Field(default_factory=dict)
    compatibility_reports: Dict[str, CompatibilityResult] = Field(default_factory=dict)
    error_message: Optional[str] = None

class PackageMarketplace:
    """
    Registry feed supporting publishing, searching, dependency resolution, and installation of packages.
    """
    _feed: Dict[str, PackageManifest] = {}
    _installed: Dict[str, PackageManifest] = {}

    @classmethod
    def publish(
        cls,
        manifest: PackageManifest,
        secret_key: Optional[str] = None
    ) -> PackageManifest:
        """
        Publish a package to the marketplace feed. Optionally signs it if a secret key is provided.
        """
        if secret_key:
            PackageSecurityManager.sign_manifest(manifest, secret_key)
        elif not manifest.hash:
            manifest.set_hash()
        
        cls._feed[manifest.name] = manifest
        return manifest

    @classmethod
    def get_package(cls, name: str) -> Optional[PackageManifest]:
        return cls._feed.get(name)

    @classmethod
    def list_packages(cls, category_filter: Optional[str] = None) -> List[PackageManifest]:
        return list(cls._feed.values())

    @classmethod
    def resolve_dependencies(
        cls,
        package_name: str,
        visited: Optional[Set[str]] = None
    ) -> List[PackageManifest]:
        """
        Resolves package dependencies recursively in topological installation order.
        """
        if visited is None:
            visited = set()
            
        if package_name in visited:
            return []
        visited.add(package_name)

        pkg = cls._feed.get(package_name)
        if not pkg:
            raise ValueError(f"Package '{package_name}' not found in marketplace feed.")

        resolved = []
        for dep_str in pkg.dependencies:
            # dep_str format: "package-name>=1.0" or just "package-name"
            dep_name = dep_str.split(">=")[0].split("<=")[0].split("==")[0].strip()
            resolved.extend(cls.resolve_dependencies(dep_name, visited))

        if pkg not in resolved:
            resolved.append(pkg)
        return resolved

    @classmethod
    def install(
        cls,
        package_name: str,
        runtime_engines: Dict[str, str],
        require_signature: bool = False,
        secret_key: Optional[str] = None
    ) -> InstallationReport:
        """
        Install a package and its dependencies after security verification and compatibility check.
        """
        try:
            to_install = cls.resolve_dependencies(package_name)
        except ValueError as e:
            return InstallationReport(
                success=False,
                error_message=str(e)
            )

        installed_list = []
        security_reports = {}
        compatibility_reports = {}

        for pkg in to_install:
            # Security verification
            sec_report = PackageSecurityManager.verify_package(pkg, secret_key)
            security_reports[pkg.name] = sec_report

            if not sec_report.manifest_hash_valid:
                return InstallationReport(
                    success=False,
                    security_reports=security_reports,
                    compatibility_reports=compatibility_reports,
                    error_message=f"Hash verification failed for package '{pkg.name}'"
                )

            if require_signature and not sec_report.signature_valid:
                return InstallationReport(
                    success=False,
                    security_reports=security_reports,
                    compatibility_reports=compatibility_reports,
                    error_message=f"Signature verification required but failed for package '{pkg.name}'"
                )

            # Compatibility verification
            comp_report = PackageCompatibilityManager.check_compatibility(pkg, runtime_engines)
            compatibility_reports[pkg.name] = comp_report

            if not comp_report.is_compatible:
                return InstallationReport(
                    success=False,
                    security_reports=security_reports,
                    compatibility_reports=compatibility_reports,
                    error_message=f"Compatibility check failed for '{pkg.name}': " + "; ".join(comp_report.incompatible_reasons)
                )

            # Install into local installed registry
            cls._installed[pkg.name] = pkg
            installed_list.append(pkg.name)

        return InstallationReport(
            success=True,
            installed_packages=installed_list,
            security_reports=security_reports,
            compatibility_reports=compatibility_reports
        )

    @classmethod
    def get_installed(cls, name: str) -> Optional[PackageManifest]:
        return cls._installed.get(name)

    @classmethod
    def list_installed(cls) -> List[PackageManifest]:
        return list(cls._installed.values())

    @classmethod
    def clear(cls):
        cls._feed.clear()
        cls._installed.clear()
