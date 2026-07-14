from fastapi import APIRouter, HTTPException, Request
from app.schemas.basic import OrganizationCreate, OrganizationResponse, UserCreate, UserResponse, WorkflowCreate, WorkflowResponse, ExecutionCreate, ExecutionResponse
from typing import List
import uuid
from datetime import datetime

# In-Memory Database for testing
MOCK_DB = {
    "users": {},
    "organizations": {},
    "workflows": {},
    "executions": {}
}

auth_router = APIRouter(prefix="/auth", tags=["Auth"])
@auth_router.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    user_id = str(uuid.uuid4())
    new_user = {
        "id": user_id,
        "email": user.email,
        "name": user.name,
        "is_verified": True
    }
    MOCK_DB["users"][user_id] = new_user
    return new_user

@auth_router.post("/login")
async def login():
    return {"access_token": "mock_token", "token_type": "bearer"}

org_router = APIRouter(prefix="/organizations", tags=["Organizations"])
@org_router.post("/", response_model=OrganizationResponse)
async def create_org(org: OrganizationCreate):
    org_id = str(uuid.uuid4())
    new_org = {
        "id": org_id,
        "name": org.name,
        "slug": org.slug,
        "plan": "free",
        "settings": {},
        "limits": {"max_workflows": 10, "max_executions_daily": 1000}
    }
    MOCK_DB["organizations"][org_id] = new_org
    return new_org

@org_router.get("/", response_model=List[OrganizationResponse])
async def list_orgs():
    return list(MOCK_DB["organizations"].values())

wf_router = APIRouter(prefix="/workflows", tags=["Workflows"])
@wf_router.post("/", response_model=WorkflowResponse)
async def create_workflow(wf: WorkflowCreate):
    wf_id = str(uuid.uuid4())
    new_wf = {
        "id": wf_id,
        "organization_id": wf.organization_id,
        "name": wf.name,
        "description": wf.description,
        "current_version": "v1",
        "published_version": None,
        "status": "Draft"
    }
    MOCK_DB["workflows"][wf_id] = new_wf
    return new_wf

@wf_router.get("/", response_model=List[WorkflowResponse])
async def list_workflows():
    return list(MOCK_DB["workflows"].values())

@wf_router.post("/{wf_id}/versions")
async def create_version(wf_id: str):
    if wf_id not in MOCK_DB["workflows"]:
        raise HTTPException(status_code=404, detail="Workflow not found")
    MOCK_DB["workflows"][wf_id]["current_version"] = "v2"
    return {"message": "Version created successfully", "version": "v2"}

@wf_router.post("/{wf_id}/execute", response_model=ExecutionResponse)
async def execute_workflow(wf_id: str, exec_data: ExecutionCreate, request: Request):
    if wf_id not in MOCK_DB["workflows"]:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    from app.models.execution import Execution
    from app.models.enums import ExecutionStatus
    
    # We will use the MOCK_DB workflow data for now but persist Execution to Beanie
    # so the ARQ worker can read it.
    new_exec = Execution(
        workflow_id=wf_id,
        workflow_version_id=MOCK_DB["workflows"][wf_id]["current_version"],
        organization_id=MOCK_DB["workflows"][wf_id]["organization_id"],
        status=ExecutionStatus.QUEUED,
        trigger_type=exec_data.trigger_type,
        started_at=datetime.utcnow().isoformat()
    )
    # Save to MongoDB
    await new_exec.insert()
    
    # Enqueue in ARQ using the app state pool
    if hasattr(request.app.state, "redis"):
        await request.app.state.redis.enqueue_job("run_workflow", str(new_exec.id))
    else:
        # Fallback if redis wasn't connected
        pass
    
    return ExecutionResponse(
        id=str(new_exec.id),
        workflow_id=new_exec.workflow_id,
        workflow_version_id=new_exec.workflow_version_id,
        status=new_exec.status.value,
        started_at=new_exec.started_at,
        duration=new_exec.duration,
        trigger_type=new_exec.trigger_type
    )

@wf_router.get("/{wf_id}/executions", response_model=List[ExecutionResponse])
async def list_executions(wf_id: str):
    return [e for e in MOCK_DB["executions"].values() if e["workflow_id"] == wf_id]
