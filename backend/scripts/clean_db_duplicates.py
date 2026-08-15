import asyncio
from app.core.database import db_manager
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
    print("Connected to Database.")
    res = await db_manager.db['execution_events'].delete_many({'sequence': None})
    print(f"Cleared null sequences: {res.deleted_count} documents removed.")
    
    # Also drop the unique index to let startup rebuild it clean
    try:
        await db_manager.db['execution_events'].drop_index("execution_id_1_sequence_1")
        print("Dropped duplicate index successfully.")
    except Exception as e:
        print(f"Index drop status: {e}")
        
    await db_manager.close_db()

if __name__ == "__main__":
    asyncio.run(f())
