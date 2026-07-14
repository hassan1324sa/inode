from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class OrganizationCreate(BaseModel):
    name: str
    slug: str
    owner_id: str

class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    settings: Dict[str, Any]
    limits: Dict[str, int]

class UserCreate(BaseModel):
    email: str
    password: str
    name: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    is_verified: bool

class WorkflowCreate(BaseModel):
    organization_id: str
    name: str
    description: Optional[str] = None

class WorkflowResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    current_version: str
    published_version: Optional[str]
    status: str

class ExecutionCreate(BaseModel):
    trigger_type: str = "Manual"
    inputs: Dict[str, Any] = {}

class ExecutionResponse(BaseModel):
    id: str
    workflow_id: str
    workflow_version_id: str
    status: str
    started_at: Optional[str]
    duration: Optional[float]
    trigger_type: str
