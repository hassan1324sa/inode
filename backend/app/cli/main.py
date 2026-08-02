import os
import json
from typing import Dict, Any, Optional, List
from app.core.packages.package import PackageManifest
from app.core.packages.marketplace import PackageMarketplace, InstallationReport
from app.core.packages.security import PackageSecurityManager, PackageSecurityReport
from app.core.packages.compatibility import PackageCompatibilityManager, CompatibilityResult

class FluxaCLI:
    """
    Fluxa Command Line Interface implementation for managing projects, packages, and workflows.
    """
    @classmethod
    def init(cls, project_dir: str, project_name: str = "fluxa-project") -> Dict[str, Any]:
        """
        Initialize a new Fluxa project directory structure.
        """
        os.makedirs(os.path.join(project_dir, "workflows"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "packages"), exist_ok=True)
        
        config_path = os.path.join(project_dir, "fluxa.yaml")
        config_data = {
            "name": project_name,
            "version": "0.1.0",
            "engines": {
                "fluxa": ">=1.0.0",
                "python": ">=3.10"
            },
            "dependencies": []
        }
        yaml_content = (
            f"name: {project_name}\n"
            "version: '0.1.0'\n"
            "engines:\n"
            "  fluxa: '>=1.0.0'\n"
            "  python: '>=3.10'\n"
            "dependencies: []\n"
        )
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)
            
        return {
            "status": "success",
            "message": f"Initialized empty Fluxa project in {project_dir}",
            "config": config_data
        }

    @classmethod
    def install(
        cls,
        package_name: str,
        runtime_engines: Optional[Dict[str, str]] = None,
        require_signature: bool = False,
        secret_key: Optional[str] = None
    ) -> InstallationReport:
        """
        Install a package and its dependencies from the Package Marketplace.
        """
        if runtime_engines is None:
            runtime_engines = {"fluxa": "1.3.0", "python": "3.12.0"}
        return PackageMarketplace.install(
            package_name=package_name,
            runtime_engines=runtime_engines,
            require_signature=require_signature,
            secret_key=secret_key
        )

    @classmethod
    def verify(
        cls,
        package_name: str,
        secret_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify security signature, hash, and publisher of an installed or marketplace package.
        """
        pkg = PackageMarketplace.get_installed(package_name) or PackageMarketplace.get_package(package_name)
        if not pkg:
            raise ValueError(f"Package '{package_name}' not found.")

        sec_report = PackageSecurityManager.verify_package(pkg, secret_key)
        return {
            "package": pkg.name,
            "version": pkg.version,
            "is_valid": sec_report.is_valid,
            "hash_valid": sec_report.manifest_hash_valid,
            "signature_valid": sec_report.signature_valid,
            "publisher_trusted": sec_report.publisher_trusted,
            "errors": sec_report.errors,
            "warnings": sec_report.warnings
        }

    @classmethod
    def publish(
        cls,
        manifest: PackageManifest,
        secret_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish a package manifest to the marketplace after computing hash and optionally signing.
        """
        pkg = PackageMarketplace.publish(manifest, secret_key=secret_key)
        return {
            "status": "success",
            "package": pkg.name,
            "version": pkg.version,
            "hash": pkg.hash,
            "signature": pkg.signature
        }

    @classmethod
    def list(cls) -> Dict[str, Any]:
        """
        List available marketplace packages and installed packages.
        """
        feed = [p.name for p in PackageMarketplace.list_packages()]
        installed = [p.name for p in PackageMarketplace.list_installed()]
        return {
            "marketplace_feed": feed,
            "installed": installed
        }

    @classmethod
    def scaffold(cls, target_dir: str, plugin_type: str, name: str) -> Dict[str, Any]:
        """
        Scaffold a new custom node or package plugin skeleton.
        """
        from app.dx.generator import PluginGenerator
        if plugin_type == "node":
            return PluginGenerator.scaffold_node(target_dir, name)
        elif plugin_type == "package":
            return PluginGenerator.scaffold_package(target_dir, name)
        else:
            raise ValueError(f"Unsupported plugin type '{plugin_type}'. Supported types: 'node', 'package'.")

    @classmethod
    def emulate(cls, workflow_data: Dict[str, Any], inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run a workflow using the zero-dependency LocalEmulator.
        """
        from app.dx.emulator import LocalEmulator
        import asyncio
        emulator = LocalEmulator()
        res = asyncio.run(emulator.run(workflow_data, inputs=inputs))
        return res.model_dump()

    @classmethod
    def docgen(cls, output_dir: str, format: str = "markdown") -> Dict[str, Any]:
        """
        Auto-generate documentation in various formats (markdown, html, json, openapi).
        """
        from app.dx.docgen import DocumentationGenerator
        os.makedirs(output_dir, exist_ok=True)
        if format == "markdown":
            content = DocumentationGenerator.generate_markdown()
            ext = "md"
        elif format == "html":
            content = DocumentationGenerator.generate_html()
            ext = "html"
        elif format == "json":
            content = DocumentationGenerator.generate_json()
            ext = "json"
        elif format == "openapi":
            content = DocumentationGenerator.generate_openapi_summary()
            ext = "json"
        else:
            raise ValueError(f"Unsupported format '{format}'. Supported: markdown, html, json, openapi.")

        out_file = os.path.join(output_dir, f"docs.{ext}")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "success", "file": out_file, "format": format}

    @classmethod
    def completion(cls, shell: str) -> str:
        """
        Generate shell auto-completion scripts for bash, zsh, or powershell.
        """
        commands = "init install verify publish list scaffold emulate docgen completion"
        if shell == "bash":
            return f"complete -W '{commands}' fluxa"
        elif shell == "zsh":
            return f"#compdef fluxa\ncompadd {commands}"
        elif shell == "powershell":
            return f"Register-ArgumentCompleter -CommandName fluxa -ScriptBlock {{ param($c, $w) '{commands}'.Split() | Where-Object {{ $_ -like '$w*' }} }}"
        else:
            raise ValueError(f"Unsupported shell '{shell}'. Supported: bash, zsh, powershell.")

