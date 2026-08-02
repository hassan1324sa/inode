from fastapi import APIRouter, HTTPException, Request
from app.schemas.basic import (
    OrganizationCreate, OrganizationResponse, UserCreate, UserResponse,
    WorkflowCreate, WorkflowResponse, ExecutionCreate, ExecutionResponse,
    VersionCreate, VersionResponse
)
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

async def build_workflow_response(wf: Workflow) -> WorkflowResponse:
    wv = await WorkflowVersion.find_one(WorkflowVersion.workflow_id == str(wf.id))
    nodes = wv.nodes if wv and wv.nodes else []
    edges = wv.edges if wv and wv.edges else []
    variables = wv.settings.get("variables", {}) if wv and wv.settings else {}
    metadata = {
        "id": str(wf.id),
        "name": wf.name,
        "description": wf.description or "",
        "tags": ["Enterprise", "AI", "Automation"],
        "createdAt": "2026-08-01T20:00:00Z",
        "updatedAt": "2026-08-01T20:00:00Z"
    }
    return WorkflowResponse(
        id=str(wf.id),
        organization_id=wf.organization_id,
        name=wf.name,
        description=wf.description,
        current_version=wf.current_version,
        published_version=wf.published_version,
        status=wf.status,
        formatVersion=1,
        engineVersion=1,
        nodeRegistryVersion=1,
        workflowVersion=1,
        metadata=metadata,
        variables=variables,
        nodes=nodes,
        edges=edges
    )

@wf_router.post("/", response_model=WorkflowResponse)
async def create_workflow(wf_data: WorkflowCreate, request: Request):
    wf_name = wf_data.name
    wf_desc = wf_data.description
    if wf_data.metadata and isinstance(wf_data.metadata, dict):
        wf_name = wf_data.metadata.get("name", wf_name)
        wf_desc = wf_data.metadata.get("description", wf_desc)

    wf = Workflow(
        organization_id=wf_data.organization_id or "org-enterprise-01",
        name=wf_name or "Untitled Workflow",
        description=wf_desc,
        current_version="v1",
        status="Draft"
    )
    await wf.insert()
    
    if wf_data.nodes or wf_data.edges:
        wv = WorkflowVersion(
            workflow_id=str(wf.id),
            version="v1",
            nodes=wf_data.nodes or [],
            edges=wf_data.edges or [],
            settings={"variables": wf_data.variables or {}},
            created_by="system"
        )
        await wv.insert()
    
    await request.app.state.memory_cache.delete("workflows:all")
    return await build_workflow_response(wf)

@wf_router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(request: Request):
    cache = request.app.state.memory_cache
    cached_data = await cache.get("workflows:all")
    if cached_data is not None:
        return cached_data
        
    wfs = await Workflow.find_all().to_list()
    result = [await build_workflow_response(wf) for wf in wfs]
    
    await cache.set("workflows:all", result, ttl=settings.cache.ttl)
    return result

from bson import ObjectId

@wf_router.get("/{wf_id}", response_model=WorkflowResponse)
async def get_workflow(wf_id: str, request: Request):
    try:
        wf_oid = ObjectId(wf_id)
        wf = await Workflow.get(wf_oid)
    except Exception:
        wf = await Workflow.find_one(Workflow.name == wf_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return await build_workflow_response(wf)

@wf_router.put("/{wf_id}", response_model=WorkflowResponse)
async def update_workflow(wf_id: str, wf_data: WorkflowCreate, request: Request):
    try:
        wf_oid = ObjectId(wf_id)
        wf = await Workflow.get(wf_oid)
    except Exception:
        wf = await Workflow.find_one(Workflow.name == wf_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf_data.name:
        wf.name = wf_data.name
    if wf_data.description is not None:
        wf.description = wf_data.description
    if wf_data.metadata and isinstance(wf_data.metadata, dict):
        wf.name = wf_data.metadata.get("name", wf.name)
        wf.description = wf_data.metadata.get("description", wf.description)
    await wf.save()

    wv = await WorkflowVersion.find_one(WorkflowVersion.workflow_id == str(wf.id))
    if wv:
        if wf_data.nodes is not None:
            wv.nodes = wf_data.nodes
        if wf_data.edges is not None:
            wv.edges = wf_data.edges
        if wf_data.variables is not None:
            wv.settings["variables"] = wf_data.variables
        await wv.save()
    elif wf_data.nodes or wf_data.edges:
        wv = WorkflowVersion(
            workflow_id=str(wf.id),
            version="v1",
            nodes=wf_data.nodes or [],
            edges=wf_data.edges or [],
            settings={"variables": wf_data.variables or {}},
            created_by="system"
        )
        await wv.insert()

    await request.app.state.memory_cache.delete("workflows:all")
    return await build_workflow_response(wf)

@wf_router.delete("/{wf_id}")
async def delete_workflow(wf_id: str, request: Request):
    try:
        wf_oid = ObjectId(wf_id)
        wf = await Workflow.get(wf_oid)
    except Exception:
        wf = await Workflow.find_one(Workflow.name == wf_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await wf.delete()
    await request.app.state.memory_cache.delete("workflows:all")
    return {"message": "Workflow deleted successfully"}


@wf_router.post("/{wf_id}/versions", response_model=VersionResponse)
async def create_version(wf_id: str, request: Request, version_data: VersionCreate = VersionCreate()):
    try:
        wf_oid = ObjectId(wf_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workflow ID")
        
    wf = await Workflow.get(wf_oid)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    # Increment version string (e.g., v1 -> v2)
    curr_num = int(wf.current_version.lstrip("v")) if wf.current_version.startswith("v") else 1
    new_version_str = f"v{curr_num + 1}"
    wf.current_version = new_version_str
    await wf.save()
    
    wf_version = WorkflowVersion(
        workflow_id=wf_id,
        version=new_version_str,
        nodes=version_data.nodes,
        edges=version_data.edges,
        settings=version_data.settings,
        created_by="system"
    )
    await wf_version.insert()
    
    await request.app.state.memory_cache.delete("workflows:all")
    await request.app.state.memory_cache.delete(f"workflow:{wf_id}")
    await request.app.state.memory_cache.delete(f"workflow_version:{new_version_str}")
    
    return VersionResponse(
        id=str(wf_version.id),
        workflow_id=wf_version.workflow_id,
        version=wf_version.version,
        nodes=wf_version.nodes,
        edges=wf_version.edges,
        settings=wf_version.settings,
        created_by=wf_version.created_by
    )

@wf_router.get("/{wf_id}/versions/latest", response_model=VersionResponse)
async def get_latest_version(wf_id: str):
    try:
        wf_oid = ObjectId(wf_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workflow ID")
        
    wf = await Workflow.get(wf_oid)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    wf_version = await WorkflowVersion.find_one(
        WorkflowVersion.workflow_id == wf_id,
        WorkflowVersion.version == wf.current_version
    )
    if not wf_version:
        # Fallback empty default version if none created yet
        return VersionResponse(
            id="default",
            workflow_id=wf_id,
            version=wf.current_version,
            nodes=[],
            edges=[],
            settings={},
            created_by="system"
        )
        
    return VersionResponse(
        id=str(wf_version.id),
        workflow_id=wf_version.workflow_id,
        version=wf_version.version,
        nodes=wf_version.nodes,
        edges=wf_version.edges,
        settings=wf_version.settings,
        created_by=wf_version.created_by
    )


@wf_router.post("/{wf_id}/execute", response_model=ExecutionResponse)
async def execute_workflow(wf_id: str, exec_data: ExecutionCreate, request: Request):
    try:
        wf_oid = ObjectId(wf_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workflow ID")
        
    wf = await Workflow.get(wf_oid)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    # Fetch current version nodes
    wf_version = await WorkflowVersion.find_one(
        WorkflowVersion.workflow_id == wf_id,
        WorkflowVersion.version == wf.current_version
    )
    nodes = wf_version.nodes if wf_version else []

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
    
    # Trigger execution using ExecutionService
    try:
        await request.app.state.execution_service.start_execution(
            execution_id=str(new_exec.id),
            workflow_definition_id=wf_id,
            tenant_id=wf.organization_id,
            nodes=nodes
        )
    except Exception as e:
        new_exec.status = ExecutionStatus.FAILED
        new_exec.error = f"Failed to start Temporal workflow: {str(e)}"
        await new_exec.save()
        raise HTTPException(status_code=500, detail=str(e))
    
    await request.app.state.memory_cache.delete(f"workflow_executions:{wf_id}")
    
    return ExecutionResponse(
        id=str(new_exec.id),
        workflow_id=new_exec.workflow_id,
        workflow_version_id=new_exec.workflow_version_id,
        status=new_exec.status.value,
        started_at=new_exec.started_at,
        duration=new_exec.duration,
        trigger_type=new_exec.trigger_type,
        error=new_exec.error
    )

@wf_router.post("/{wf_id}/executions/{exec_id}/pause")
async def pause_execution(wf_id: str, exec_id: str, request: Request):
    try:
        await request.app.state.execution_service.pause_execution(exec_id)
        return {"message": "Pause signal sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@wf_router.post("/{wf_id}/executions/{exec_id}/resume")
async def resume_execution(wf_id: str, exec_id: str, request: Request):
    try:
        await request.app.state.execution_service.resume_execution(exec_id)
        return {"message": "Resume signal sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@wf_router.post("/{wf_id}/executions/{exec_id}/cancel")
async def cancel_execution(wf_id: str, exec_id: str, request: Request):
    try:
        await request.app.state.execution_service.cancel_execution(exec_id)
        return {"message": "Cancellation request sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            trigger_type=ex.trigger_type,
            error=ex.error
        )
        for ex in executions
    ]
    
    await cache.set(f"workflow_executions:{wf_id}", result, ttl=settings.cache.ttl)
    return result
