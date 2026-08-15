import asyncio
from app.core.database import db_manager
from app.core.execution.durable_store import MongoDBEventStore
from app.models.user import User
from app.models.organization import Organization
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.models.execution import Execution
from app.models.node_execution import NodeExecution
from app.models.credential import Credential

async def f():
    await db_manager.connect_db(document_models=[
        User, Organization, Workflow, WorkflowVersion, Execution, NodeExecution, Credential
    ])
    print("Rebuilding indexes...")
    await MongoDBEventStore.setup_indexes()
    print("Indexes Rebuilt successfully.")
    await db_manager.close_db()

if __name__ == "__main__":
    asyncio.run(f())
