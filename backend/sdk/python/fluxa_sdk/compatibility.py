from typing import Tuple

SDK_VERSION = "1.3.0"
MINIMUM_SUPPORTED_SERVER_VERSION = "1.0.0"


class VersionIncompatibleError(Exception):
    """Raised when the SDK version is incompatible with the target server version."""
    def __init__(self, sdk_version: str, server_version: str, minimum_supported: str):
        super().__init__(
            f"SDK version {sdk_version} is incompatible with server version {server_version}. "
            f"Minimum supported server version is {minimum_supported}."
        )
        self.sdk_version = sdk_version
        self.server_version = server_version
        self.minimum_supported = minimum_supported


def _parse_semver(version_str: str) -> Tuple[int, int, int]:
    clean = version_str.lstrip("vV")
    parts = clean.split(".")
    try:
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2].split("-")[0]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except ValueError:
        return (0, 0, 0)


def validate_server_compatibility(
    server_version: str,
    sdk_version: str = SDK_VERSION,
    minimum_supported: str = MINIMUM_SUPPORTED_SERVER_VERSION
) -> bool:
    """
    Validate that the connected server version meets the minimum supported version for this SDK.
    Raises VersionIncompatibleError if incompatible.
    """
    s_ver = _parse_semver(server_version)
    min_ver = _parse_semver(minimum_supported)
    
    if s_ver < min_ver:
        raise VersionIncompatibleError(sdk_version, server_version, minimum_supported)
    return True
