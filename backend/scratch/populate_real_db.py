import asyncio
from app.core.database import db_manager
from app.core.settings import settings
from app.models.user import User
from app.models.organization import Organization
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.models.execution import Execution
from app.models.node_execution import NodeExecution
from app.models.enums import ExecutionStatus

async def populate():
    # Make sure we use the real config database name
    settings.db.database_name = "fluxa"
    
    print(f"Connecting to database: {settings.db.database_name}...")
    await db_manager.connect_db(document_models=[
        User, Organization, Workflow, WorkflowVersion, Execution, NodeExecution
    ])
    
    print("Database connected. Inserting mock data...")
    
    # 1. Create a User
    user = User(
        email="belamohamed386@gmail.com",
        password_hash="hashed_password_placeholder",
        name="Belal Mohamed",
        is_verified=True
    )
    await user.insert()
    print(f"User created: {user.id}")
    
    # 2. Create an Organization
    org = Organization(
        name="Fluxa Org",
        slug="fluxa-org",
        owner_id=str(user.id),
        plan="premium",
        settings={"theme": "dark"},
        limits={"max_workflows": 50, "max_executions_daily": 10000}
    )
    await org.insert()
    print(f"Organization created: {org.id}")
    
    # 3. Create a Workflow
    wf = Workflow(
        organization_id=str(org.id),
        name="Lead Generation Sync",
        description="Syncs Facebook Leads to Google Sheets",
        current_version="v1",
        status="Active"
    )
    await wf.insert()
    print(f"Workflow created: {wf.id}")
    
    # 4. Create a Workflow Version
    wf_version = WorkflowVersion(
        workflow_id=str(wf.id),
        version="v1",
        nodes=[
            {
                "id": "trigger-1",
                "name": "Webhook Trigger",
                "type": "webhook",
                "config": {"path": "/hooks/facebook"}
            },
            {
                "id": "action-1",
                "name": "Format Lead Data",
                "type": "transform",
                "config": {"template": "Name: {{name}}, Email: {{email}}"}
            },
            {
                "id": "action-2",
                "name": "Add to Sheets",
                "type": "google_sheets",
                "config": {"spreadsheet_id": "sheet_12345"}
            }
        ],
        edges=[
            {"from": "trigger-1", "to": "action-1"},
            {"from": "action-1", "to": "action-2"}
        ],
        created_by=str(user.id)
    )
    await wf_version.insert()
    print(f"Workflow version v1 created: {wf_version.id}")
    
    # 5. Create an Execution
    execution = Execution(
        workflow_id=str(wf.id),
        workflow_version_id="v1",
        organization_id=str(org.id),
        status=ExecutionStatus.COMPLETED,
        trigger_type="Webhook",
        started_at=None,
        nodes_snapshot=[],
        edges_snapshot=[]
    )
    await execution.insert()
    print(f"Execution record created: {execution.id}")
    
    await db_manager.close_db()
    print("Done! Real database populated successfully.")

if __name__ == "__main__":
    asyncio.run(populate())
