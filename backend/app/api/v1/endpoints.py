from fastapi import APIRouter, HTTPException, Request
from app.schemas.basic import OrganizationCreate, OrganizationResponse, UserCreate, UserResponse, WorkflowCreate, WorkflowResponse, ExecutionCreate, ExecutionResponse
from typing import List
from datetime import datetime, timezone
import json

from app.models.user import User
from app.models.organization import Organization
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.models.execution import Execution
from app.models.enums import ExecutionStatus
from app.core.settings import settings

auth_router = APIRouter(prefix="/auth", tags=["Auth"])

@auth_router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, request: Request):
    user = User(
        email=user_data.email,
        password_hash=user_data.password, # In real app, hash this
        name=user_data.name,
        is_verified=True
    )
    await user.insert()
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        is_verified=user.is_verified
    )

@auth_router.post("/login")
async def login():
    return {"access_token": "mock_token", "token_type": "bearer"}

org_router = APIRouter(prefix="/organizations", tags=["Organizations"])

@org_router.post("/", response_model=OrganizationResponse)
async def create_org(org_data: OrganizationCreate, request: Request):
    org = Organization(
        name=org_data.name,
        slug=org_data.slug,
        owner_id=org_data.owner_id,
        plan="free",
        settings={},
        limits={"max_workflows": 10, "max_executions_daily": 1000}
    )
    await org.insert()
    
    # Invalidate cache
    await request.app.state.memory_cache.delete("organizations:all")
    
    return OrganizationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        plan=org.plan,
        settings=org.settings,
        limits=org.limits
    )

@org_router.get("/", response_model=List[OrganizationResponse])
async def list_orgs(request: Request):
    cache = request.app.state.memory_cache
    cached_data = await cache.get("organizations:all")
    if cached_data is not None:
        return cached_data
        
    orgs = await Organization.find_all().to_list()
    result = [
        OrganizationResponse(
            id=str(org.id),
            name=org.name,
            slug=org.slug,
            plan=org.plan,
            settings=org.settings,
            limits=org.limits
        )
        for org in orgs
    ]
    
    # Store plain pydantic models or dicts in cache, we'll store the dict representation
    # Actually FastAPI automatically converts returned Pydantic models, but for cache we should store raw dicts
    await cache.set("organizations:all", result, ttl=settings.cache.ttl)
    return result

wf_router = APIRouter(prefix="/workflows", tags=["Workflows"])

@wf_router.post("/", response_model=WorkflowResponse)
async def create_workflow(wf_data: WorkflowCreate, request: Request):
    wf = Workflow(
        organization_id=wf_data.organization_id,
        name=wf_data.name,
        description=wf_data.description,
        current_version="v1",
        status="Draft"
    )
    await wf.insert()
    
    await request.app.state.memory_cache.delete("workflows:all")
    
    return WorkflowResponse(
        id=str(wf.id),
        organization_id=wf.organization_id,
        name=wf.name,
        description=wf.description,
        current_version=wf.current_version,
        published_version=wf.published_version,
        status=wf.status
    )

@wf_router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(request: Request):
    cache = request.app.state.memory_cache
    cached_data = await cache.get("workflows:all")
    if cached_data is not None:
        return cached_data
        
    wfs = await Workflow.find_all().to_list()
    result = [
        WorkflowResponse(
            id=str(wf.id),
            organization_id=wf.organization_id,
            name=wf.name,
            description=wf.description,
            current_version=wf.current_version,
            published_version=wf.published_version,
            status=wf.status
        )
        for wf in wfs
    ]
    
    await cache.set("workflows:all", result, ttl=settings.cache.ttl)
    return result

from bson import ObjectId

@wf_router.post("/{wf_id}/versions")
async def create_version(wf_id: str, request: Request):
    try:
        wf_oid = ObjectId(wf_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workflow ID")
        
    wf = await Workflow.get(wf_oid)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    new_version_str = "v2" # Naive version bump for demo
    wf.current_version = new_version_str
    await wf.save()
    
    wf_version = WorkflowVersion(
        workflow_id=wf_id,
        version=new_version_str,
        nodes=[{
            "id": "node-1",
            "name": "Set Test Var",
            "type": "set_variable",
            "variable_name": "test_var",
            "variable_value": 42
        }],
        edges=[],
        created_by="system"
    )
    await wf_version.insert()
    
    await request.app.state.memory_cache.delete("workflows:all")
    await request.app.state.memory_cache.delete(f"workflow:{wf_id}")
    await request.app.state.memory_cache.delete(f"workflow_version:{new_version_str}")
    
    return {"message": "Version created successfully", "version": new_version_str}

@wf_router.post("/{wf_id}/execute", response_model=ExecutionResponse)
async def execute_workflow(wf_id: str, exec_data: ExecutionCreate, request: Request):
    try:
        wf_oid = ObjectId(wf_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workflow ID")
        
    wf = await Workflow.get(wf_oid)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    new_exec = Execution(
        workflow_id=wf_id,
        workflow_version_id=wf.current_version,
        organization_id=wf.organization_id,
        status=ExecutionStatus.QUEUED,
        trigger_type=exec_data.trigger_type,
        started_at=None,
        nodes_snapshot=[],
        edges_snapshot=[]
    )
    await new_exec.insert()
    
    # Enqueue
    await request.app.state.execution_queue.put(str(new_exec.id))
    
    await request.app.state.memory_cache.delete(f"workflow_executions:{wf_id}")
    
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
async def list_executions(wf_id: str, request: Request):
    cache = request.app.state.memory_cache
    cached_data = await cache.get(f"workflow_executions:{wf_id}")
    if cached_data is not None:
        return cached_data
        
    executions = await Execution.find(Execution.workflow_id == wf_id).to_list()
    result = [
        ExecutionResponse(
            id=str(ex.id),
            workflow_id=ex.workflow_id,
            workflow_version_id=ex.workflow_version_id,
            status=ex.status.value,
            started_at=ex.started_at,
            duration=ex.duration,
            trigger_type=ex.trigger_type
        )
        for ex in executions
    ]
    
    await cache.set(f"workflow_executions:{wf_id}", result, ttl=settings.cache.ttl)
    return result
