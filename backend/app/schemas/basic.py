from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from enum import Enum

class EnvironmentMode(str, Enum):
    DEVELOPMENT = "Development"
    STAGING = "Staging"
    PRODUCTION = "Production"

class OrganizationSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    name: str
    slug: str
    environment_mode: EnvironmentMode

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

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Password cannot be empty")
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    is_verified: bool

class WorkflowCreate(BaseModel):
    organization_id: Optional[str] = "org-enterprise-01"
    name: Optional[str] = "Untitled Workflow"
    description: Optional[str] = None
    formatVersion: Optional[int] = 1
    engineVersion: Optional[int] = 1
    nodeRegistryVersion: Optional[int] = 1
    workflowVersion: Optional[int] = 1
    metadata: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None

class WorkflowResponse(BaseModel):
    id: str
    organization_id: str = "org-enterprise-01"
    name: str
    description: Optional[str] = None
    current_version: str = "v1"
    published_version: Optional[str] = None
    status: str = "Draft"
    formatVersion: int = 1
    engineVersion: int = 1
    nodeRegistryVersion: int = 1
    workflowVersion: int = 1
    metadata: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = {}
    nodes: Optional[List[Dict[str, Any]]] = []
    edges: Optional[List[Dict[str, Any]]] = []

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
    error: Optional[str] = None

class VersionCreate(BaseModel):
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    settings: Dict[str, Any] = {}

class VersionResponse(BaseModel):
    id: str
    workflow_id: str
    version: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    settings: Dict[str, Any]
    created_by: str

