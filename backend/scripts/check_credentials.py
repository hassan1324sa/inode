import asyncio
from app.core.database import db_manager
from app.models.credential import Credential
from app.models.user import User
from app.models.organization import Organization
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.models.execution import Execution
from app.models.node_execution import NodeExecution

async def f():
    await db_manager.connect_db(document_models=[
        User, Organization, Workflow, WorkflowVersion, Execution, NodeExecution, Credential
    ])
    creds = await Credential.find_all().to_list()
    print('Found credentials count:', len(creds))
    for c in creds:
        # Decrypt to check values safely
        from app.core.security.secrets import decrypt_value
        val = decrypt_value(c.encrypted_data)
        # Check if the val is like sk-... or similar
        print(f"Org: {c.organization_id}, Provider (Path): {c.provider}, Value (partially masked): {val[:12]}...")
    await db_manager.close_db()

if __name__ == "__main__":
    asyncio.run(f())
