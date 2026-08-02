import re
from typing import Dict, List, Tuple, Optional
from pydantic import BaseModel, Field
from app.core.packages.package import PackageManifest

class CompatibilityResult(BaseModel):
    is_compatible: bool
    engine_checks: Dict[str, bool] = Field(default_factory=dict)
    missing_engines: List[str] = Field(default_factory=list)
    incompatible_reasons: List[str] = Field(default_factory=list)

class PackageCompatibilityManager:
    """
    Validates semantic version constraints for Fluxa package engines and dependencies.
    """
    @classmethod
    def _parse_version(cls, version_str: str) -> Tuple[int, ...]:
        clean = re.sub(r"[^0-9.]", "", version_str)
        return tuple(int(x) for x in clean.split(".") if x.isdigit())

    @classmethod
    def _satisfies_constraint(cls, actual_ver_str: str, constraint: str) -> bool:
        """
        Supports basic semver constraints: '>=1.0', '<=2.0', '==1.2', '>1.0', '<2.0', or exact version.
        """
        actual = cls._parse_version(actual_ver_str)
        constraint = constraint.strip()
        
        if constraint.startswith(">="):
            target = cls._parse_version(constraint[2:])
            return actual >= target
        elif constraint.startswith("<="):
            target = cls._parse_version(constraint[2:])
            return actual <= target
        elif constraint.startswith("=="):
            target = cls._parse_version(constraint[2:])
            return actual == target
        elif constraint.startswith(">"):
            target = cls._parse_version(constraint[1:])
            return actual > target
        elif constraint.startswith("<"):
            target = cls._parse_version(constraint[1:])
            return actual < target
        elif constraint.startswith("^"):
            # Caret requirement: compatible with same major version
            target = cls._parse_version(constraint[1:])
            if not target:
                return False
            return actual >= target and actual[0] == target[0]
        else:
            # Try equality if no prefix
            target = cls._parse_version(constraint)
            if target:
                return actual == target
            return True

    @classmethod
    def check_compatibility(
        cls,
        manifest: PackageManifest,
        runtime_engines: Dict[str, str]
    ) -> CompatibilityResult:
        """
        Validate that the current runtime engines satisfy manifest engine constraints.
        Example runtime_engines: {"fluxa": "1.3.0", "python": "3.12.0"}
        """
        engine_checks = {}
        missing_engines = []
        reasons = []

        for engine_name, constraint in manifest.engines.items():
            if engine_name not in runtime_engines:
                missing_engines.append(engine_name)
                engine_checks[engine_name] = False
                reasons.append(f"Required engine '{engine_name}' is not present in runtime.")
                continue
            
            actual_version = runtime_engines[engine_name]
            satisfied = cls._satisfies_constraint(actual_version, constraint)
            engine_checks[engine_name] = satisfied
            if not satisfied:
                reasons.append(
                    f"Engine '{engine_name}' version {actual_version} does not satisfy constraint '{constraint}'"
                )

        is_compatible = len(reasons) == 0

        return CompatibilityResult(
            is_compatible=is_compatible,
            engine_checks=engine_checks,
            missing_engines=missing_engines,
            incompatible_reasons=reasons
        )
