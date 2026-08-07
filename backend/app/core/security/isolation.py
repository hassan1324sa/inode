from typing import Dict, Any, Optional
from app.core.security.context import SecurityContextHolder, SecurityException

class TenantScopedResource:
    def __init__(self, resource_id: str, tenant_id: str, workspace_id: str, data: Any):
        self.resource_id = resource_id
        self.tenant_id = tenant_id
        self.workspace_id = workspace_id
        self.data = data


class TenantScopedRepository:
    """
    Enforces tenant context validations on every retrieve/save operation.
    """
    def __init__(self):
        # resource_id -> TenantScopedResource
        self._store: Dict[str, TenantScopedResource] = {}

    def save(self, resource: TenantScopedResource):
        # Mandatory context verification (Fail Closed)
        ctx = SecurityContextHolder.get_current_context()
        if ctx.organization_id != resource.tenant_id or ctx.workspace_id != resource.workspace_id:
            raise SecurityException("Access Denied: Cross-tenant write violation.")
            
        self._store[resource.resource_id] = resource

    def get(self, resource_id: str) -> TenantScopedResource:
        ctx = SecurityContextHolder.get_current_context()
        resource = self._store.get(resource_id)
        if not resource:
            raise ValueError(f"Resource {resource_id} not found.")

        if ctx.organization_id != resource.tenant_id or ctx.workspace_id != resource.workspace_id:
            raise SecurityException("Access Denied: Cross-tenant access violation.")

        return resource


class WorkerIsolationManager:
    """
    Verifies and enforces task executor constraints.
    """
    @classmethod
    def execute_worker_task(cls, bound_tenant_id: str, bound_workspace_id: str, task_fn: Any, *args, **kwargs) -> Any:
        ctx = SecurityContextHolder.get_current_context()
        
        # Enforce worker bound context check
        if ctx.organization_id != bound_tenant_id or ctx.workspace_id != bound_workspace_id:
            raise SecurityException("Access Denied: Worker execution context violation.")
            
        return task_fn(*args, **kwargs)
