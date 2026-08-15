from fastapi import APIRouter, HTTPException, Request
from app.schemas.basic import (
    OrganizationCreate, OrganizationResponse, UserCreate, UserResponse,
    WorkflowCreate, WorkflowResponse, ExecutionCreate, ExecutionResponse,
    VersionCreate, VersionResponse, OrganizationSettingsUpdate
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
    # Check if user already exists
    existing_user = await User.find_one(User.email == user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    from app.core.security.password import hash_password
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
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

from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    email: str
    password: str
    organization_id: Optional[str] = None

@auth_router.post("/login")
async def login(req: LoginRequest):
    if not req.email or not req.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
        
    user = await User.find_one(User.email == req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    from app.core.security.password import verify_password
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    # Resolve organization_id
    org_id = req.organization_id
    if org_id:
        from bson import ObjectId
        try:
            org_oid = ObjectId(org_id)
            org = await Organization.get(org_oid)
        except Exception:
            org = await Organization.find_one(Organization.slug == org_id)
        if not org:
            raise HTTPException(status_code=400, detail="Requested organization not found")
    else:
        org = await Organization.find_one(Organization.owner_id == str(user.id))
        if not org:
            org = Organization(
                name=f"{user.name}'s Org" if user.name else "My Personal Org",
                slug=f"personal-org-{user.id}",
                owner_id=str(user.id),
                plan="free",
                settings={"environment_mode": "Development"},
                limits={"max_workflows": 10, "max_executions_daily": 1000}
            )
            await org.insert()
            
    import hashlib
    from datetime import datetime, timezone, timedelta
    from app.core.security.jwt import create_access_token, create_refresh_token
    from app.models.user import RefreshTokenRecord

    token = create_access_token(
        user_id=str(user.id),
        organization_id=str(org.id)
    )
    refresh_token, jti = create_refresh_token(user_id=str(user.id))
    
    # Hash refresh token
    token_hash = hashlib.sha256(refresh_token.encode('utf-8')).hexdigest()
    
    # Store token record
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    new_record = RefreshTokenRecord(
        jti=jti,
        token_hash=token_hash,
        created_at=now,
        expires_at=now + timedelta(days=7)
    )
    
    # Ensure refresh_token_records list is initialized
    if getattr(user, 'refresh_token_records', None) is None:
        user.refresh_token_records = []
    user.refresh_token_records.append(new_record)
    
    # Prune expired/revoked records
    user.refresh_token_records = [
        rec for rec in user.refresh_token_records
        if rec.expires_at > now
    ]
    
    await user.save()

    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


class RefreshRequest(BaseModel):
    refresh_token: str
    organization_id: Optional[str] = None

@auth_router.post("/refresh/")
async def refresh_token_endpoint(req: RefreshRequest):
    import hashlib
    from datetime import datetime, timezone, timedelta
    from jose import jwt, JWTError
    from app.core.security.jwt import create_access_token, create_refresh_token
    from app.models.user import RefreshTokenRecord
    
    # 1. Decode JWT & check basic syntax/type/expiration
    try:
        payload = jwt.decode(
            req.refresh_token,
            settings.jwt.secret,
            algorithms=[settings.jwt.algorithm],
            options={"require_exp": True, "require_iat": True}
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        jti = payload.get("jti")
        if not user_id or not jti:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
        
    # 2. Retrieve user
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    # 3. Hash the incoming token to compare
    incoming_hash = hashlib.sha256(req.refresh_token.encode('utf-8')).hexdigest()
    
    # 4. Find matching active record in user.refresh_token_records
    matched_record = None
    if getattr(user, 'refresh_token_records', None):
        for rec in user.refresh_token_records:
            if rec.jti == jti:
                matched_record = rec
                break
                
    if not matched_record:
        raise HTTPException(status_code=401, detail="Refresh token not recognized")
        
    if matched_record.revoked_at is not None:
        # Token has been revoked! Revoke all tokens for security (reuse detection)
        for rec in user.refresh_token_records:
            rec.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await user.save()
        raise HTTPException(status_code=401, detail="Refresh token already revoked or reused")
        
    if matched_record.token_hash != incoming_hash:
        raise HTTPException(status_code=401, detail="Invalid token signature")
        
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if matched_record.expires_at < now:
        raise HTTPException(status_code=401, detail="Refresh token expired")
        
    # 5. Revoke old token
    matched_record.revoked_at = now
    
    # 6. Resolve organization
    org_id = req.organization_id
    if org_id:
        from bson import ObjectId
        try:
            org_oid = ObjectId(org_id)
            org = await Organization.get(org_oid)
        except Exception:
            org = await Organization.find_one(Organization.slug == org_id)
        if not org:
            raise HTTPException(status_code=400, detail="Requested organization not found")
    else:
        org = await Organization.find_one(Organization.owner_id == str(user.id))
        if not org:
            org = await Organization.find_one(Organization.slug == "my-personal-org")
            
    # 7. Generate new tokens
    new_access_token = create_access_token(
        user_id=str(user.id),
        organization_id=str(org.id) if org else "my-personal-org"
    )
    new_refresh_token, new_jti = create_refresh_token(user_id=str(user.id))
    new_hash = hashlib.sha256(new_refresh_token.encode('utf-8')).hexdigest()
    
    new_record = RefreshTokenRecord(
        jti=new_jti,
        token_hash=new_hash,
        created_at=now,
        expires_at=now + timedelta(days=7)
    )
    user.refresh_token_records.append(new_record)
    
    # Prune expired/revoked records
    user.refresh_token_records = [
        rec for rec in user.refresh_token_records
        if rec.expires_at > now
    ]
    
    await user.save()
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


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

@org_router.get("/{org_id}", response_model=OrganizationResponse)
async def get_org(org_id: str):
    from bson import ObjectId
    try:
        org_oid = ObjectId(org_id)
        org = await Organization.get(org_oid)
    except Exception:
        org = await Organization.find_one(Organization.slug == org_id)
        
    if not org:
        # Prepopulate default org if none exists so the app doesn't break
        org = await Organization.find_one(Organization.slug == "my-personal-org")
        if not org:
            org = Organization(
                name="My Personal Org",
                slug="my-personal-org",
                owner_id="system",
                plan="free",
                settings={"environment_mode": "Development"},
                limits={"max_workflows": 10, "max_executions_daily": 1000}
            )
            await org.insert()
            
    return OrganizationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        plan=org.plan,
        settings=org.settings,
        limits=org.limits
    )

@org_router.put("/{org_id}", response_model=OrganizationResponse)
async def update_org_settings(org_id: str, org_data: OrganizationSettingsUpdate, request: Request):
    from app.core.security.context import SecurityContextHolder
    try:
        ctx = SecurityContextHolder.get_current_context()
    except Exception:
        ctx = None
        
    # Security/Tenant check: Mismatch is forbidden
    if ctx and ctx.organization_id and ctx.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied: organization mismatch")
        
    from bson import ObjectId
    try:
        org_oid = ObjectId(org_id)
        org = await Organization.get(org_oid)
    except Exception:
        org = await Organization.find_one(Organization.slug == org_id)
        
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    org.name = org_data.name
    org.slug = org_data.slug
    org.settings["environment_mode"] = org_data.environment_mode.value
    await org.save()
    
    await request.app.state.memory_cache.delete("organizations:all")
    return OrganizationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        plan=org.plan,
        settings=org.settings,
        limits=org.limits
    )

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
    from app.core.security.context import SecurityContextHolder
    ctx = SecurityContextHolder.get_current_context()
    if not ctx or not ctx.organization_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    wf_name = wf_data.name
    wf_desc = wf_data.description
    if wf_data.metadata and isinstance(wf_data.metadata, dict):
        wf_name = wf_data.metadata.get("name", wf_name)
        wf_desc = wf_data.metadata.get("description", wf_desc)

    wf = Workflow(
        organization_id=ctx.organization_id,
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
    
    await request.app.state.memory_cache.delete(f"workflows:all:{ctx.organization_id}")
    return await build_workflow_response(wf)

@wf_router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(request: Request):
    from app.core.security.context import SecurityContextHolder
    ctx = SecurityContextHolder.get_current_context()
    if not ctx or not ctx.organization_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    cache = request.app.state.memory_cache
    cache_key = f"workflows:all:{ctx.organization_id}"
    cached_data = await cache.get(cache_key)
    if cached_data is not None:
        return cached_data
        
    wfs = await Workflow.find(Workflow.organization_id == ctx.organization_id).to_list()
    result = [await build_workflow_response(wf) for wf in wfs]
    
    await cache.set(cache_key, result, ttl=settings.cache.ttl)
    return result

from bson import ObjectId

@wf_router.get("/{wf_id}", response_model=WorkflowResponse)
async def get_workflow(wf_id: str, request: Request):
    from app.core.security.context import SecurityContextHolder
    ctx = SecurityContextHolder.get_current_context()
    if not ctx or not ctx.organization_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        wf_oid = ObjectId(wf_id)
        wf = await Workflow.get(wf_oid)
    except Exception:
        wf = await Workflow.find_one(Workflow.name == wf_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.organization_id != ctx.organization_id:
        raise HTTPException(status_code=403, detail="Access denied: organization mismatch")
    return await build_workflow_response(wf)

@wf_router.put("/{wf_id}", response_model=WorkflowResponse)
async def update_workflow(wf_id: str, wf_data: WorkflowCreate, request: Request):
    from app.core.security.context import SecurityContextHolder
    ctx = SecurityContextHolder.get_current_context()
    if not ctx or not ctx.organization_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        wf_oid = ObjectId(wf_id)
        wf = await Workflow.get(wf_oid)
    except Exception:
        wf = await Workflow.find_one(Workflow.name == wf_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.organization_id != ctx.organization_id:
        raise HTTPException(status_code=403, detail="Access denied: organization mismatch")

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

    await request.app.state.memory_cache.delete(f"workflows:all:{ctx.organization_id}")
    return await build_workflow_response(wf)

@wf_router.delete("/{wf_id}")
async def delete_workflow(wf_id: str, request: Request):
    from app.core.security.context import SecurityContextHolder
    ctx = SecurityContextHolder.get_current_context()
    if not ctx or not ctx.organization_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        wf_oid = ObjectId(wf_id)
        wf = await Workflow.get(wf_oid)
    except Exception:
        wf = await Workflow.find_one(Workflow.name == wf_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.organization_id != ctx.organization_id:
        raise HTTPException(status_code=403, detail="Access denied: organization mismatch")

    await wf.delete()
    await request.app.state.memory_cache.delete(f"workflows:all:{ctx.organization_id}")
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
    from app.core.security.context import SecurityContextHolder
    ctx = SecurityContextHolder.get_current_context()
    if not ctx or not ctx.organization_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        wf_oid = ObjectId(wf_id)
        wf = await Workflow.get(wf_oid)
    except Exception:
        wf = await Workflow.find_one(Workflow.name == wf_id)
        
    if not wf:
        wf = await Workflow.find_one(Workflow.id == wf_id)
        
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    if wf.organization_id != ctx.organization_id:
        raise HTTPException(status_code=403, detail="Access denied: organization mismatch")
        
    # Fetch current version nodes and edges
    wf_version = await WorkflowVersion.find_one(
        WorkflowVersion.workflow_id == str(wf.id),
        WorkflowVersion.version == wf.current_version
    )
    nodes = wf_version.nodes if wf_version else []
    edges = wf_version.edges if wf_version else []

    # Run Graph Validation before starting any execution or Temporal client
    from app.core.execution.validation import GraphValidator, WorkflowValidationError
    try:
        GraphValidator.validate_graph(nodes, edges)
    except WorkflowValidationError as ve:
        raise HTTPException(
            status_code=400,
            detail={
                "message": str(ve),
                "errors": ve.errors
            }
        )


    new_exec = Execution(
        workflow_id=str(wf.id),
        workflow_version_id=wf.current_version,
        organization_id=wf.organization_id,
        status=ExecutionStatus.QUEUED,
        trigger_type=exec_data.trigger_type,
        started_at=None,
        nodes_snapshot=[],
        edges_snapshot=[],
        metadata={
            "workspace_id": ctx.workspace_id,
            "environment_id": ctx.environment_id,
            "project_id": ctx.project_id,
            "user_id": ctx.user_id,
            "correlation_id": SecurityContextHolder.get_correlation_id() or ctx.correlation_id,
            "permissions": ctx.permissions
        }
    )
    await new_exec.insert()
    
    # Trigger execution using ExecutionService
    try:
        await request.app.state.execution_service.start_execution(
            execution_id=str(new_exec.id),
            workflow_definition_id=wf_id,
            tenant_id=wf.organization_id,
            nodes=nodes,
            edges=edges
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

from fastapi import WebSocket, WebSocketDisconnect
from typing import Optional
from app.core.execution.live_debug import LiveExecutionStreamManager, ReplayEngine, DiffEngine, EventStore

debug_router = APIRouter(prefix="/debug", tags=["Debug"])

@debug_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    execution_id: str,
    tenant_id: str,
    last_sequence: int = 0,
    token: Optional[str] = None
):
    # Authentication check
    if not token:
        await websocket.close(code=1008)
        return
        
    try:
        from app.core.security.jwt import decode_access_token
        ctx = decode_access_token(token)
    except Exception:
        await websocket.close(code=1008)
        return

    try:
        from app.models.execution import Execution
        from bson import ObjectId
        exec_obj = await Execution.get(ObjectId(execution_id))
        if exec_obj:
            tenant_id = exec_obj.organization_id
            from app.core.settings import settings
            is_dev = settings.env == "development"
            if not is_dev and ctx.organization_id != tenant_id:
                await websocket.close(code=1008)
                return
        else:
            if ctx.organization_id != tenant_id:
                await websocket.close(code=1008)
                return
    except Exception:
        if ctx.organization_id != tenant_id:
            await websocket.close(code=1008)
            return
        
    await websocket.accept()

    
    # Connect client
    connected = await LiveExecutionStreamManager.connect(
        websocket=websocket,
        execution_id=execution_id,
        tenant_id=tenant_id,
        last_sequence=last_sequence
    )
    if not connected:
        await websocket.close(code=1008)
        return
        
    try:
        while True:
            # Keep socket alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        LiveExecutionStreamManager.disconnect(websocket, execution_id)

@debug_router.post("/executions/{execution_id}/replay")
async def replay_execution(execution_id: str, tenant_id: str):
    try:
        res = await ReplayEngine.trigger_replay(execution_id, tenant_id)
        return res
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@debug_router.post("/executions/{execution_id}/restart")
async def restart_execution(execution_id: str, from_node_id: str, tenant_id: str):
    try:
        res = await ReplayEngine.trigger_restart(execution_id, from_node_id, tenant_id)
        return res
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@debug_router.post("/executions/diff")
async def diff_executions(execution_id_a: str, execution_id_b: str, tenant_id: str):
    snap_a = await EventStore.get_snapshot(execution_id_a)
    snap_b = await EventStore.get_snapshot(execution_id_b)
    if not snap_a or not snap_b:
        raise HTTPException(status_code=404, detail="Execution snapshot not found")
        
    if snap_a.tenant_id != tenant_id or snap_b.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied: tenant mismatch")
        
    return DiffEngine.diff_executions(snap_a, snap_b)


from pydantic import BaseModel

class CredentialRequest(BaseModel):
    name: str
    provider: str
    value: str

@debug_router.get("/models")
async def get_model_catalog():
    openrouter_models = [
        {"id": "openrouter/auto", "name": "OpenRouter Auto Router"}
    ]
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            res = await client.get("https://openrouter.ai/api/v1/models", timeout=5.0)
            if res.status_code == 200:
                data = res.json()
                fetched = []
                for m in data.get("data", []):
                    fetched.append({
                        "id": m.get("id"),
                        "name": m.get("name") or m.get("id")
                    })
                if fetched:
                    openrouter_models = fetched
    except Exception:
        # Fallback if connection fails
        pass

    return {
        "providers": [
            {"id": "google", "name": "Google Gemini", "icon": "Cpu"},
            {"id": "openai", "name": "OpenAI", "icon": "Cpu"},
            {"id": "anthropic", "name": "Anthropic", "icon": "Cpu"},
            {"id": "openrouter", "name": "OpenRouter", "icon": "Cpu"}
        ],
        "models": {
            "google": [
                {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
                {"id": "google/gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
                {"id": "google/gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
                {"id": "google/gemini-1.5-pro", "name": "Gemini 1.5 Pro"}
            ],
            "openai": [
                {"id": "openai/gpt-4o", "name": "GPT-4o"},
                {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini"}
            ],
            "anthropic": [
                {"id": "anthropic/claude-3-5-sonnet", "name": "Claude 3.5 Sonnet"},
                {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku"}
            ],
            "openrouter": openrouter_models
        }
    }


@debug_router.post("/credentials")
async def create_credential(cred: CredentialRequest):
    from app.core.security.context import SecurityContextHolder
    try:
        ctx = SecurityContextHolder.get_current_context()
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing valid Bearer token")

    from app.core.security.secrets import VaultSecretProvider
    provider = VaultSecretProvider()
    
    # Store credential
    ref = await provider.put(cred.name, cred.value)
    
    # Return metadata only
    return {
        "credential_id": cred.name,
        "provider": cred.provider
    }

@debug_router.get("/credentials")
async def list_credentials():
    from app.core.security.context import SecurityContextHolder
    from app.core.security.secrets import VaultSecretProvider
    try:
        ctx = SecurityContextHolder.get_current_context()
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing valid Bearer token")
        
    org_id = ctx.organization_id
    prefix = f"{org_id}/"
    keys = []
    
    # 1. Load from MongoDB
    from app.models.credential import Credential
    db_creds = await Credential.find({"organization_id": org_id}).to_list()
    db_keys = [c.provider for c in db_creds]
    
    # 2. Merge with in-memory keys
    for path in VaultSecretProvider._store.keys():
        if path.startswith(prefix):
            cred_id = path.replace(prefix, "")
            tenant_path = f"{org_id}/{cred_id}"
            if tenant_path not in VaultSecretProvider._revoked_paths:
                if cred_id not in db_keys:
                    keys.append(cred_id)
                    
    all_keys = list(set(db_keys + keys))
    return {"credentials": [{"credential_id": k} for k in all_keys]}

@debug_router.delete("/credentials/{credential_id}")
async def delete_credential(credential_id: str):
    from app.core.security.context import SecurityContextHolder
    from app.core.security.secrets import VaultSecretProvider
    
    ctx = SecurityContextHolder.get_current_context()
    if not ctx or not ctx.organization_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    provider = VaultSecretProvider()
    if not provider.exists(credential_id):
        raise HTTPException(status_code=404, detail="Credential not found")
        
    await provider.revoke(credential_id)
    return {"credential_id": credential_id, "status": "revoked"}

@debug_router.put("/credentials/{credential_id}")
async def rotate_credential(credential_id: str, cred: CredentialRequest):
    from app.core.security.context import SecurityContextHolder
    from app.core.security.secrets import VaultSecretProvider
    
    ctx = SecurityContextHolder.get_current_context()
    if not ctx or not ctx.organization_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    provider = VaultSecretProvider()
    if not provider.exists(credential_id):
        raise HTTPException(status_code=404, detail="Credential not found")
        
    await provider.rotate(credential_id, cred.value)
    return {"credential_id": credential_id, "status": "rotated"}


class InstallRequest(BaseModel):
    package_name: str

pkg_router = APIRouter(prefix="/packages", tags=["Packages"])

def ensure_marketplace_populated():
    from app.core.packages import PackageMarketplace, PackageManifest
    if not PackageMarketplace.list_packages():
        defaults = [
            PackageManifest(
                name="@fluxa/core-extensions",
                version="1.2.0",
                author="Fluxa Official",
                publisher="fluxa-official",
                description="Extended logic nodes including Regex matching, Date formatting, and UUID generators.",
                engines={"fluxa": ">=1.0.0"}
            ),
            PackageManifest(
                name="@fluxa/openai-vision",
                version="2.0.1",
                author="AI Community",
                publisher="fluxa-official",
                description="Vision-capable image analysis and OCR nodes for OpenAI GPT-4o.",
                engines={"fluxa": ">=1.0.0"}
            ),
            PackageManifest(
                name="@fluxa/salesforce-crm",
                version="1.0.4",
                author="Enterprise Team",
                publisher="fluxa-official",
                description="Connectors for Salesforce CRM accounts, leads, and opportunity triggers.",
                engines={"fluxa": ">=1.0.0"}
            ),
            PackageManifest(
                name="@fluxa/aws-s3",
                version="1.1.0",
                author="CloudOps",
                publisher="fluxa-official",
                description="Upload, download, and stream buckets directly from AWS S3 compatible storage.",
                engines={"fluxa": ">=1.0.0"}
            )
        ]
        for pkg in defaults:
            PackageMarketplace.publish(pkg)

@pkg_router.get("/")
async def list_packages():
    from app.core.security.context import SecurityContextHolder
    from app.models.organization import Organization
    from app.core.packages import PackageMarketplace
    from bson import ObjectId
    
    ctx = SecurityContextHolder.get_current_context()
    if not ctx or not ctx.organization_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # ctx.organization_id is a MongoDB ObjectId string — look up by id first, slug as fallback
    try:
        org = await Organization.get(ObjectId(ctx.organization_id))
    except Exception:
        org = await Organization.find_one(Organization.slug == ctx.organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    ensure_marketplace_populated()
    installed = org.settings.get("installed_packages", {})
    
    available = PackageMarketplace.list_packages()
    result = []
    for pkg in available:
        inst_meta = installed.get(pkg.name)
        result.append({
            "id": pkg.name,
            "name": pkg.name,
            "version": pkg.version,
            "author": pkg.author or "Unknown",
            "description": pkg.description or "",
            "installed": inst_meta is not None,
            "installed_metadata": inst_meta,
            "category": "AI" if "vision" in pkg.name else "Utilities" if "core" in pkg.name else "Communication" if "salesforce" in pkg.name else "Files"
        })
    return result

@pkg_router.post("/install")
async def install_package(req_data: InstallRequest):
    from app.core.security.context import SecurityContextHolder
    from app.models.organization import Organization
    from app.core.packages import PackageMarketplace
    from bson import ObjectId
    
    ctx = SecurityContextHolder.get_current_context()
    if not ctx or not ctx.organization_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        org = await Organization.get(ObjectId(ctx.organization_id))
    except Exception:
        org = await Organization.find_one(Organization.slug == ctx.organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    ensure_marketplace_populated()
    
    report = PackageMarketplace.install(
        req_data.package_name,
        runtime_engines={"fluxa": "1.3.0"}
    )
    if not report.success:
        raise HTTPException(status_code=400, detail=report.error_message or "Installation failed")
        
    installed = org.settings.get("installed_packages", {})
    
    installed[req_data.package_name] = {
        "version": PackageMarketplace.get_package(req_data.package_name).version,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "status": "installed"
    }
    org.settings["installed_packages"] = installed
    await org.save()
    
    return {"status": "installed", "package_name": req_data.package_name, "installed_metadata": installed[req_data.package_name]}

@pkg_router.post("/uninstall")
async def uninstall_package(req_data: InstallRequest):
    from app.core.security.context import SecurityContextHolder
    from app.models.organization import Organization
    from app.core.packages import PackageMarketplace
    
    ctx = SecurityContextHolder.get_current_context()
    if not ctx or not ctx.organization_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    try:
        from bson import ObjectId
        org = await Organization.get(ObjectId(ctx.organization_id))
    except Exception:
        org = await Organization.find_one(Organization.slug == ctx.organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    ensure_marketplace_populated()
    
    installed = org.settings.get("installed_packages", {})
    if req_data.package_name not in installed:
        raise HTTPException(status_code=400, detail="Package is not installed")
        
    for inst_name in list(installed.keys()):
        if inst_name == req_data.package_name:
            continue
        manifest = PackageMarketplace.get_package(inst_name)
        if manifest:
            for dep_str in manifest.dependencies:
                dep_name = dep_str.split(">=")[0].split("<=")[0].split("==")[0].strip()
                if dep_name == req_data.package_name:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot uninstall '{req_data.package_name}' because installed package '{inst_name}' depends on it."
                    )
                    
    del installed[req_data.package_name]
    org.settings["installed_packages"] = installed
    await org.save()
    
    return {"status": "uninstalled", "package_name": req_data.package_name}


telegram_router = APIRouter(prefix="/webhooks/telegram", tags=["Webhooks"])

@telegram_router.post("")
async def telegram_webhook(update: dict, request: Request):
    message = update.get("message")
    if not message:
        return {"status": "ignored"}
        
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "")
    user_info = message.get("from", {})
    
    from bson import ObjectId
    # Find all active workflow versions that have a telegram_trigger node
    versions = await WorkflowVersion.find(
        {"nodes": {"$elemMatch": {"type": "telegram_trigger"}}}
    ).to_list()
    
    triggered_count = 0
    for wv in versions:
        # Check commandFilter or allowedChatId in node configuration
        trigger_node = next((n for n in wv.nodes if n["type"] == "telegram_trigger"), None)
        if not trigger_node:
            continue
            
        node_data = trigger_node.get("data", {})
        allowed_chat_id = node_data.get("allowedChatId")
        command_filter = node_data.get("commandFilter")
        
        # Verify allowed chat ID
        if allowed_chat_id and str(chat_id) != str(allowed_chat_id):
            continue
            
        # Verify command filter (e.g. "/run")
        if command_filter and not text.startswith(command_filter):
            continue
            
        # Find corresponding Workflow
        wf = await Workflow.get(ObjectId(wv.workflow_id))
        if not wf:
            continue
            
        from app.core.security.context import SecurityContextHolder
        # Start execution
        new_exec = Execution(
            workflow_id=str(wf.id),
            workflow_version_id=wf.current_version,
            organization_id=wf.organization_id,
            status=ExecutionStatus.QUEUED,
            trigger_type="webhook",
            started_at=None,
            nodes_snapshot=[],
            edges_snapshot=[],
            metadata={
                "workspace_id": "default",
                "environment_id": "default",
                "project_id": "default",
                "user_id": f"telegram_{chat_id}",
                "correlation_id": f"telegram-{chat_id}-{datetime.now(timezone.utc).timestamp()}",
                "permissions": ["*"]
            },
            variables={
                "telegram_message": text,
                "telegram_chat_id": chat_id,
                "telegram_user": user_info
            }
        )
        await new_exec.insert()
        
        try:
            await request.app.state.execution_service.start_execution(
                execution_id=str(new_exec.id),
                workflow_definition_id=str(wf.id),
                tenant_id=wf.organization_id,
                nodes=wv.nodes,
                edges=wv.edges
            )
            triggered_count += 1
        except Exception as e:
            new_exec.status = ExecutionStatus.FAILED
            new_exec.error = f"Failed to start execution: {str(e)}"
            await new_exec.save()
            
    return {"status": "processed", "triggered": triggered_count}



