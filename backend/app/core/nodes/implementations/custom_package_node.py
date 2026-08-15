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

        # 2. Simulate the execution of the package logic
        output_data: Dict[str, Any] = {
            "package_name": package_name,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "status": "success"
        }

        if package_name == "@fluxa/core-extensions":
            output_data.update({
                "generated_uuid": str(uuid.uuid4()),
                "regex_match": {
                    "matched": True,
                    "groups": ["test@example.com"],
                    "input": "test@example.com"
                },
                "formatted_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            })
        elif package_name == "@fluxa/openai-vision":
            output_data.update({
                "ocr_text": "INVOICE SUMMARY\nInvoice Number: INV-2026-089\nTotal Amount: $4,580.00\nDate: 2026-08-12",
                "detected_objects": ["Text Block", "Invoice Table", "Header Logo"],
                "confidence_score": 0.985
            })
        elif package_name == "@fluxa/salesforce-crm":
            output_data.update({
                "lead_id": f"00Q{uuid.uuid4().hex[:15].upper()}",
                "lead_status": "New",
                "synced_fields": ["name", "email", "company"]
            })
        elif package_name == "@fluxa/aws-s3":
            output_data.update({
                "s3_url": f"https://fluxa-data-bucket.s3.amazonaws.com/uploads/file-{uuid.uuid4().hex[:8]}.json",
                "bytes_transferred": 8192,
                "encryption": "AES256"
            })
        else:
            output_data.update({
                "message": "Custom package executed successfully.",
                "payload": {}
            })

        # 3. Save output into the execution context
        context.set_node_output(node_id, output_data)

        return context
