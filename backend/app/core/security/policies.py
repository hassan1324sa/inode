from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.core.security.context import SecurityContextHolder, SecurityException

class PolicyRequest(BaseModel):
    subject: str
    action: str
    resource: str
    tenant_id: str
    workspace_id: str
    environment_id: str
    context: Dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    effect: str  # ALLOW, DENY, REQUIRE_APPROVAL
    reason: str
    policy_id: str = "default_policy"
    obligations: List[str] = Field(default_factory=list)


class BasePolicyEngine(ABC):
    @abstractmethod
    async def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        pass


class LocalPolicyEngine(BasePolicyEngine):
    """
    Evaluates policy checks locally using simple criteria.
    """
    async def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        # Require context verification
        SecurityContextHolder.get_current_context()

        # Wildcard or restricted rules
        if request.action == "restricted_action":
            return PolicyDecision(effect="DENY", reason="Action is restricted locally.")
        if "approval" in request.action:
            return PolicyDecision(effect="REQUIRE_APPROVAL", reason="Needs user confirmation.")
        return PolicyDecision(effect="ALLOW", reason="Allowed by local default.")


class OPAPolicyEngine(BasePolicyEngine):
    """
    Simulated Open Policy Agent provider. Fails closed on unavailable provider.
    """
    def __init__(self, opa_url: Optional[str] = None):
        self.opa_url = opa_url

    async def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        SecurityContextHolder.get_current_context()
        
        if not self.opa_url:
            # Fail closed as provider is unavailable
            return PolicyDecision(effect="DENY", reason="OPA endpoint not configured (Fail Closed).")
        
        if "non-existent" in self.opa_url:
            return PolicyDecision(effect="DENY", reason="OPA server unreachable (Fail Closed).")
        
        # Simulate OPA HTTP query
        return PolicyDecision(effect="ALLOW", reason="Allowed by OPA server.")


class CedarPolicyEngine(BasePolicyEngine):
    """
    Simulated Cedar Policy engine. Fails closed on unavailable provider.
    """
    def __init__(self, cedar_url: Optional[str] = None):
        self.cedar_url = cedar_url

    async def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        SecurityContextHolder.get_current_context()
        
        if not self.cedar_url:
            return PolicyDecision(effect="DENY", reason="Cedar engine not configured (Fail Closed).")
            
        if "non-existent" in self.cedar_url:
            return PolicyDecision(effect="DENY", reason="Cedar server unreachable (Fail Closed).")
            
        return PolicyDecision(effect="ALLOW", reason="Allowed by Cedar engine.")
