from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.settings import settings
from app.core.database import db_manager
from app.core.cache.memory import MemoryCache
from app.core.execution.worker import execution_worker
import asyncio
import logging

from app.models.user import User
from app.models.organization import Organization
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.models.execution import Execution
from app.models.node_execution import NodeExecution
from app.models.enums import ExecutionStatus

from app.api.v1.health import router as health_router
from app.api.v1.endpoints import auth_router, org_router, wf_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Fluxa API...")
    try:
        await db_manager.connect_db(document_models=[
            User, Organization, Workflow, WorkflowVersion, Execution, NodeExecution
        ])
        logger.info("MongoDB connected and Beanie initialized.")
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        logger.warning("Starting API without database connection (for /docs preview only)")
        
    app.state.memory_cache = MemoryCache()
    app.state.execution_queue = asyncio.Queue()
    
    # Startup Recovery
    try:
        queued_executions = await Execution.find(Execution.status == ExecutionStatus.QUEUED).to_list()
        for exec_doc in queued_executions:
            await app.state.execution_queue.put(str(exec_doc.id))
            logger.info(f"Recovered QUEUED execution: {exec_doc.id}")
            
        stale_executions = await Execution.find(Execution.status == ExecutionStatus.RUNNING).to_list()
        for exec_doc in stale_executions:
            exec_doc.status = ExecutionStatus.FAILED
            exec_doc.nodes_snapshot = getattr(exec_doc, "nodes_snapshot", []) # Fallback
            # Wait, Execution model doesn't have an error field, but we can just mark it failed
            await exec_doc.save()
            logger.info(f"Marked stale RUNNING execution as FAILED: {exec_doc.id}")
    except Exception as e:
        logger.error(f"Error during startup recovery: {e}")
    
    # Start worker
    app.state.execution_worker_task = asyncio.create_task(
        execution_worker(app.state.execution_queue, app.state.memory_cache)
    )
    logger.info("Background execution worker started.")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Fluxa API...")
    
    if hasattr(app.state, "execution_worker_task"):
        app.state.execution_worker_task.cancel()
        try:
            await asyncio.gather(app.state.execution_worker_task, return_exceptions=True)
        except asyncio.CancelledError:
            pass
            
    await db_manager.close_db()

app = FastAPI(
    title=settings.app_name,
    description="Fluxa Workflow Automation API",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(auth_router, prefix="/api/v1")
app.include_router(org_router, prefix="/api/v1")
app.include_router(wf_router, prefix="/api/v1")
