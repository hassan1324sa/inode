from typing import Any, Dict
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext
from app.models.organization import Organization
from bson import ObjectId
import uuid
from datetime import datetime, timezone

@NodeExecutorRegistry.register("custom_package_node")
class CustomPackageExecutor(BaseNodeExecutor):
    """
    Node executor to execute logic from an installed dynamic extension package.
    """
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        package_name = node_data.get("packageName", "@fluxa/pkg-example")
        node_id = node_data.get("id", "unknown")

        # 1. Enforce multi-tenant package installation isolation
        if not context.tenant_id:
            raise ValueError("Unauthorized: Missing organization context.")

        try:
            org = await Organization.get(ObjectId(context.tenant_id))
        except Exception:
            org = await Organization.find_one(Organization.slug == context.tenant_id)

        if not org:
            raise ValueError(f"Organization '{context.tenant_id}' not found.")

        installed_packages = org.settings.get("installed_packages", {})
        if package_name not in installed_packages:
            raise ValueError(f"Access Denied: Package '{package_name}' is not installed in this organization.")

        # 2. Package execution logic is not implemented
        raise NotImplementedError("Custom package execution is not currently supported.")

        return context
