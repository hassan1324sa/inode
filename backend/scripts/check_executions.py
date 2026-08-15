import asyncio
from app.core.database import db_manager
from app.models.execution import Execution
from app.models.user import User
from app.models.organization import Organization
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.models.node_execution import NodeExecution
from app.models.credential import Credential

async def f():
    await db_manager.connect_db(document_models=[
        User, Organization, Workflow, WorkflowVersion, Execution, NodeExecution, Credential
    ])
    execs = await Execution.find_all().to_list()
    print('Found executions count:', len(execs))
    for e in execs:
        print(f"ID: {e.id}, Status: {e.status}, Variables keys: {list(e.variables.keys()) if e.variables else 'None'}")
        if e.variables:
            print("Variables:", e.variables)
    await db_manager.close_db()

if __name__ == "__main__":
    asyncio.run(f())
