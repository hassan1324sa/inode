import contextvars
from pydantic import BaseModel, Field
from typing import Optional

class SecurityException(Exception):
    pass


class SecurityContext(BaseModel):
    organization_id: str
    workspace_id: Optional[str] = None
    environment_id: Optional[str] = None
    project_id: Optional[str] = None
    user_id: str
    correlation_id: Optional[str] = None
    permissions: list[str] = Field(default_factory=list)


class SecurityContextHolder:
    _context_var: contextvars.ContextVar[Optional[SecurityContext]] = contextvars.ContextVar(
        "security_context", default=None
    )
    _correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
        "correlation_id", default=None
    )

    @classmethod
    def set_context(cls, context: SecurityContext):
        cls._context_var.set(context)
        if context.correlation_id:
            cls._correlation_id_var.set(context.correlation_id)

    @classmethod
    def set_correlation_id(cls, correlation_id: str):
        cls._correlation_id_var.set(correlation_id)

    @classmethod
    def get_correlation_id(cls) -> Optional[str]:
        return cls._correlation_id_var.get()

    @classmethod
    def clear_context(cls):
        cls._context_var.set(None)
        cls._correlation_id_var.set(None)

    @classmethod
    def get_current_context(cls) -> SecurityContext:
        ctx = cls._context_var.get()
        if ctx is None:
            raise SecurityException("Access Denied: Missing security context (Fail Closed).")
        return ctx
