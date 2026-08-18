import pytest
import asyncio
import os
os.environ["FLUXA_SYSTEM_BOOTSTRAP"] = "true"
os.environ["TESTING"] = "True"
os.environ["JWT_SECRET"] = "test_jwt_secret_must_be_at_least_32_characters_long_for_security"
os.environ["CREDENTIAL_ENCRYPTION_KEY"] = "test_cred_key_must_be_at_least_32_characters_long_for_security"
from httpx import AsyncClient
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie
from app.main import app
from app.core.database import db_manager
from app.models.user import User
from app.models.organization import Organization
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.models.execution import Execution
from app.models.node_execution import NodeExecution
from app.models.credential import Credential
from unittest.mock import AsyncMock

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session", autouse=True)
def init_db():
    # Setup mock Mongo Client
    client = AsyncMongoMockClient()
    client.append_metadata = None
    db = client["fluxa_test_db"]
    
    # Patch list_collection_names to strip 'authorizedCollections' (unsupported by mongomock)
    orig_list_collection_names = db.list_collection_names
    async def patched_list_collection_names(*args, **kwargs):
        return await orig_list_collection_names(*args)
    db.list_collection_names = patched_list_collection_names
    
    # Initialize beanie with the mock database
    asyncio.run(
        init_beanie(
            database=db,
            document_models=[
                User, Organization, Workflow, WorkflowVersion, Execution, NodeExecution, Credential
            ]
        )
    )
    
    # Mock db_manager's connect_db and close_db so the app doesn't attempt real connections
    db_manager.client = client
    
    async def mock_connect_db(*args, **kwargs):
        pass
    async def mock_close_db(*args, **kwargs):
        pass
        
    db_manager.connect_db = mock_connect_db
    db_manager.close_db = mock_close_db
    
    yield

@pytest.fixture(autouse=True)
def mock_execution_service():
    mock_service = AsyncMock()
    mock_service.start_execution.return_value = "mock-run-id"
    mock_service.pause_execution.return_value = None
    mock_service.resume_execution.return_value = None
    mock_service.cancel_execution.return_value = None
    mock_service.terminate_execution.return_value = None
    
    # Override on the app state
    from app.core.cache.memory import MemoryCache
    app.state.memory_cache = MemoryCache()
    app.state.execution_service = mock_service
    return mock_service

@pytest.fixture
async def client():
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

