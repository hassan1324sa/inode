from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.settings import settings
from app.core.database import db_manager
from app.core.cache.memory import MemoryCache
from app.core.execution.service import ExecutionService
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
    app.state.execution_service = ExecutionService()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Fluxa API...")
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
