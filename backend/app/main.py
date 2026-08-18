from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from app.core.settings import settings
from app.core.database import db_manager
from app.core.cache.memory import MemoryCache
from app.core.execution.service import ExecutionService
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException, RequestValidationError
from app.core.security.context import SecurityException
import logging

from app.models.user import User
from app.models.organization import Organization
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.models.execution import Execution
from app.models.node_execution import NodeExecution
from app.models.credential import Credential
from app.models.enums import ExecutionStatus

from app.api.v1.health import router as health_router
from app.api.v1.endpoints import auth_router, org_router, wf_router, debug_router, pkg_router, telegram_router
from app.core.execution.live_debug import LiveExecutionStreamManager

import re

class SecretRedactionFilter(logging.Filter):
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = re.sub(
                r'(?i)(password|secret|token|authorization|key)["\']?\s*[:=]\s*["\']?[^\s"\'},]+["\']?',
                r'\1" : "***"',
                record.msg
            )
        return True

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
for handler in logging.root.handlers:
    handler.addFilter(SecretRedactionFilter())
logger.addFilter(SecretRedactionFilter())

# ---------------------------------------------------------------------------
# Security Middleware — defined BEFORE it is referenced by app.add_middleware
# ---------------------------------------------------------------------------

class SecurityContextASGIMiddleware:
    """
    ASGI middleware that validates Bearer JWT tokens on every non-public request.
    Runs INSIDE the CORS middleware so that 401 responses still carry correct
    Access-Control-Allow-Origin headers.
    """

    # Paths that do NOT require a Bearer token
    PUBLIC_PREFIXES = [
        "/api/v1/health",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/v1/webhooks/telegram",
    ]

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from app.core.security.context import SecurityContextHolder
        from app.core.security.jwt import decode_access_token
        import uuid
        import json

        headers = {
            k.decode("utf-8").lower(): v.decode("utf-8")
            for k, v in scope.get("headers", [])
        }

        # Generate / propagate a correlation ID for every request
        correlation_id = headers.get("x-correlation-id", "").strip() or f"corr-{uuid.uuid4()}"

        SecurityContextHolder.clear_context()
        SecurityContextHolder.set_correlation_id(correlation_id)

        path = scope.get("path", "")
        method = scope.get("method", "")

        # Pass preflight OPTIONS requests straight through so CORS works
        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        # Public routes — no token required
        if any(path.startswith(p) for p in self.PUBLIC_PREFIXES):
            await self._call_with_correlation(scope, receive, send, correlation_id)
            return

        # All other routes — require Bearer token
        auth_header = headers.get("authorization", "")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            await self._send_401(
                send,
                "Missing or invalid authorization header",
                "Authorization header must be Bearer token",
            )
            return

        token = auth_header[7:].strip()
        try:
            ctx = decode_access_token(token)
            ctx.correlation_id = correlation_id
            SecurityContextHolder.set_context(ctx)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(f"JWT Validation failed: {exc}")
            await self._send_401(
                send,
                "Invalid or expired JWT token",
                "Please log in again."
            )
            return

        await self._call_with_correlation(scope, receive, send, correlation_id)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    async def _send_401(self, send, message: str, detail: str):
        import json
        body = json.dumps(
            {
                "statusCode": 401,
                "code": "UNAUTHORIZED",
                "message": message,
                "detail": detail,
            }
        ).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("utf-8")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})

    async def _call_with_correlation(self, scope, receive, send, correlation_id: str):
        """Wrap send to inject X-Correlation-ID into every response."""

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers_list = list(message.get("headers", []))
                headers_list.append(
                    (b"x-correlation-id", correlation_id.encode("utf-8"))
                )
                message = {**message, "headers": headers_list}
            await send(message)

        await self.app(scope, receive, send_wrapper)


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up iNode API...")
    try:
        await db_manager.connect_db(
            document_models=[
                User,
                Organization,
                Workflow,
                WorkflowVersion,
                Execution,
                NodeExecution,
                Credential,
            ]
        )
        logger.info("MongoDB connected and Beanie initialized.")
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        logger.warning("Starting API without database connection (for /docs preview only)")

    app.state.memory_cache = MemoryCache()
    app.state.execution_service = ExecutionService()

    await LiveExecutionStreamManager.initialize()

    try:
        from app.core.execution.durable_store import MongoDBEventStore
        await MongoDBEventStore.setup_indexes()
    except Exception as e:
        logger.warning(f"Could not setup EventStore indexes: {e}")

    yield

    logger.info("Shutting down iNode API...")
    await db_manager.close_db()


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    description="iNode Workflow Automation API",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

def _error_code(status_code: int) -> str:
    mapping = {400: "VALIDATION_ERROR", 401: "UNAUTHORIZED", 403: "FORBIDDEN",
               404: "NOT_FOUND", 409: "CONFLICT"}
    return mapping.get(status_code, "SERVER_ERROR" if status_code >= 500 else "API_ERROR")


@app.exception_handler(SecurityException)
async def security_exception_handler(request, exc: SecurityException):
    msg = str(exc)
    return JSONResponse(
        status_code=401,
        content={"statusCode": 401, "code": "UNAUTHORIZED", "message": msg, "detail": msg},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    msg = str(exc.detail) if exc.detail else "HTTP Exception occurred"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "statusCode": exc.status_code,
            "code": _error_code(exc.status_code),
            "message": msg,
            "detail": msg,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        safe_err = dict(err)
        if "ctx" in safe_err and isinstance(safe_err["ctx"], dict):
            safe_err["ctx"] = {
                k: str(v) if isinstance(v, Exception) else v
                for k, v in safe_err["ctx"].items()
            }
        errors.append(safe_err)
    return JSONResponse(
        status_code=400,
        content={
            "statusCode": 400,
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "detail": errors,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc: Exception):
    logger.exception("Unhandled exception occurred: %s", str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "statusCode": 500,
            "code": "SERVER_ERROR",
            "message": "Internal Server Error",
            "detail": "An internal server error occurred."
        },
    )


# ---------------------------------------------------------------------------
# Middleware stack
# Note: Starlette adds middleware in LIFO order, so the LAST add_middleware call
# wraps outermost. We want:
#   CORS (outermost) → Security → Route handler
# Therefore register Security first, then CORS.
# ---------------------------------------------------------------------------

app.add_middleware(SecurityContextASGIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(auth_router, prefix="/api/v1")
app.include_router(org_router, prefix="/api/v1")
app.include_router(wf_router, prefix="/api/v1")
app.include_router(debug_router, prefix="/api/v1")
app.include_router(pkg_router, prefix="/api/v1")
app.include_router(telegram_router, prefix="/api/v1")
