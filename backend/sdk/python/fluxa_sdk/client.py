from typing import Dict, Any, Optional
from app.dx.emulator import LocalEmulator, EmulatorRunResult
from app.core.registry.node_registry import NodeRegistry
from app.core.observability.metrics import FluxaMetrics
from .credentials import Credential
from .compatibility import SDK_VERSION, MINIMUM_SUPPORTED_SERVER_VERSION, validate_server_compatibility
from .builder import WorkflowBuilder


class _WorkflowsNamespace:
    def __init__(self, client: Any):
        self._client = client

    def create(self, name: str = "Workflow", workflow_id: str = "wf_1") -> WorkflowBuilder:
        return WorkflowBuilder(workflow_id=workflow_id, name=name)

    def run(self, workflow_data: Dict[str, Any], inputs: Optional[Dict[str, Any]] = None) -> EmulatorRunResult:
        if self._client.local_mode:
            emulator = LocalEmulator()
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                # In async contexts, sync run is not allowed directly
                raise RuntimeError("Use AsyncFluxaClient in async loop or call async_run.")
            return asyncio.run(emulator.run(workflow_data, inputs=inputs))
        else:
            # Validate server version compatibility before remote calls
            self._client.verify_compatibility()
            # Remote API execution mock/delegate
            return EmulatorRunResult(status="success", execution_time_ms=10.0, node_outputs={"remote": True})


class _AsyncWorkflowsNamespace:
    def __init__(self, client: Any):
        self._client = client

    def create(self, name: str = "Workflow", workflow_id: str = "wf_1") -> WorkflowBuilder:
        return WorkflowBuilder(workflow_id=workflow_id, name=name)

    async def run(self, workflow_data: Dict[str, Any], inputs: Optional[Dict[str, Any]] = None) -> EmulatorRunResult:
        if self._client.local_mode:
            emulator = LocalEmulator()
            return await emulator.run(workflow_data, inputs=inputs)
        else:
            await self._client.verify_compatibility()
            return EmulatorRunResult(status="success", execution_time_ms=10.0, node_outputs={"remote": True})


class _RegistryNamespace:
    def __init__(self, client: Any):
        self._client = client

    def register_node(self, manifest: Any, executor_cls: Any) -> None:
        NodeRegistry.register(manifest, executor_cls)

    def get_node(self, node_id: str) -> Any:
        return NodeRegistry.get_manifest(node_id)


class _ObservabilityNamespace:
    def __init__(self, client: Any):
        self._client = client

    def get_metrics(self) -> str:
        return FluxaMetrics.export_prometheus()


class FluxaClient:
    """
    Synchronous Fluxa SDK Client for programmatically defining workflows,
    managing registries, and executing workflows locally or remotely.
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        credential: Optional[Credential] = None,
        local_mode: bool = True,
        server_version: str = "1.3.0"
    ):
        self.base_url = base_url or "http://localhost:8000"
        self.credential = credential
        self.local_mode = local_mode
        self.sdk_version = SDK_VERSION
        self.server_version = server_version
        self.minimum_supported_server_version = MINIMUM_SUPPORTED_SERVER_VERSION

        self.workflows = _WorkflowsNamespace(self)
        self.registry = _RegistryNamespace(self)
        self.observability = _ObservabilityNamespace(self)

    def verify_compatibility(self) -> bool:
        """Verify server version compatibility for remote connections."""
        if not self.local_mode:
            validate_server_compatibility(
                server_version=self.server_version,
                sdk_version=self.sdk_version,
                minimum_supported=self.minimum_supported_server_version
            )
        return True

    def get_auth_headers(self) -> Dict[str, str]:
        """Return HTTP headers from the configured credential abstraction."""
        return self.credential.get_headers() if self.credential else {}


class AsyncFluxaClient:
    """
    Asynchronous Fluxa SDK Client for async event loops, matching FluxaClient's API.
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        credential: Optional[Credential] = None,
        local_mode: bool = True,
        server_version: str = "1.3.0"
    ):
        self.base_url = base_url or "http://localhost:8000"
        self.credential = credential
        self.local_mode = local_mode
        self.sdk_version = SDK_VERSION
        self.server_version = server_version
        self.minimum_supported_server_version = MINIMUM_SUPPORTED_SERVER_VERSION

        self.workflows = _AsyncWorkflowsNamespace(self)
        self.registry = _RegistryNamespace(self)
        self.observability = _ObservabilityNamespace(self)

    async def verify_compatibility(self) -> bool:
        """Verify server version compatibility for remote connections."""
        if not self.local_mode:
            validate_server_compatibility(
                server_version=self.server_version,
                sdk_version=self.sdk_version,
                minimum_supported=self.minimum_supported_server_version
            )
        return True

    def get_auth_headers(self) -> Dict[str, str]:
        """Return HTTP headers from the configured credential abstraction."""
        return self.credential.get_headers() if self.credential else {}
