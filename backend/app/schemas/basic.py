from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from enum import Enum

CURRENT_SCHEMA_VERSION = "v1"
CURRENT_FORMAT_VERSION = 1
CURRENT_ENGINE_VERSION = 1
CURRENT_NODE_REGISTRY_VERSION = 1
CURRENT_WORKFLOW_VERSION = 1

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
    organization_id: Optional[str] = None
    name: Optional[str] = "Untitled Workflow"
    description: Optional[str] = None
    formatVersion: Optional[int] = CURRENT_FORMAT_VERSION
    engineVersion: Optional[int] = CURRENT_ENGINE_VERSION
    nodeRegistryVersion: Optional[int] = CURRENT_NODE_REGISTRY_VERSION
    workflowVersion: Optional[int] = CURRENT_WORKFLOW_VERSION
    metadata: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None

class WorkflowResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    current_version: str = CURRENT_SCHEMA_VERSION
    published_version: Optional[str] = None
    status: str = "Draft"
    formatVersion: int = CURRENT_FORMAT_VERSION
    engineVersion: int = CURRENT_ENGINE_VERSION
    nodeRegistryVersion: int = CURRENT_NODE_REGISTRY_VERSION
    workflowVersion: int = CURRENT_WORKFLOW_VERSION
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

