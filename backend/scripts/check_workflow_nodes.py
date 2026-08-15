import asyncio
from app.core.database import db_manager
from app.models.workflow_version import WorkflowVersion
from app.models.workflow import Workflow
from app.models.user import User
from app.models.organization import Organization

async def f():
    await db_manager.connect_db(document_models=[
        User, Organization, Workflow, WorkflowVersion
    ])
    wvs = await WorkflowVersion.find_all().to_list()
    for wv in wvs:
        print('ID:', wv.id, 'Workflow:', wv.workflow_id)
        print('Nodes count:', len(wv.nodes))
        for n in wv.nodes:
            print("  Node:", n.get('id'), "Type:", n.get('type'), "Data keys:", list(n.get('data', {}).keys()) if n.get('data') else 'None')
            if n.get('type') == 'ai_agent':
                print("    AI Agent Data:", n.get('data'))
        print('Edges:', wv.edges)
        print("="*60)
    await db_manager.close_db()

if __name__ == "__main__":
    asyncio.run(f())
