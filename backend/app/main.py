from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from app.core.settings import settings
from app.core.database import db_manager
from app.core.cache.memory import MemoryCache
from app.core.execution.service import ExecutionService
import logging

from app.models.user import User
from app.models.organization import Organization
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.models.execution import Execution
from app.models.node_execution import NodeExecution
from app.models.enums import ExecutionStatus

from app.api.v1.health import router as health_router
from app.api.v1.endpoints import auth_router, org_router, wf_router, debug_router, pkg_router
from app.core.execution.live_debug import LiveExecutionStreamManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Fluxa API...")
    try:
        await db_manager.connect_db(document_models=[
            User, Organization, Workflow, WorkflowVersion, Execution, NodeExecution
        ])
        logger.info("MongoDB connected and Beanie initialized.")
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        logger.warning("Starting API without database connection (for /docs preview only)")
        
    app.state.memory_cache = MemoryCache()
    app.state.execution_service = ExecutionService()
    
    # Initialize live debugging stream
    await LiveExecutionStreamManager.initialize()
    
    # Setup EventStore indexes
    try:
        from app.core.execution.durable_store import MongoDBEventStore
        await MongoDBEventStore.setup_indexes()
    except Exception as e:
        logger.warning(f"Could not setup EventStore indexes: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Fluxa API...")
    await db_manager.close_db()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.app_name,
    description="Fluxa Workflow Automation API",
    version="1.0.0",
    lifespan=lifespan
)

from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException, RequestValidationError
from app.core.security.context import SecurityException

def get_error_code(status_code: int) -> str:
    if status_code == 400:
        return "VALIDATION_ERROR"
    if status_code == 401:
        return "UNAUTHORIZED"
    if status_code == 403:
        return "FORBIDDEN"
    if status_code == 404:
        return "NOT_FOUND"
    if status_code == 409:
        return "CONFLICT"
    if status_code >= 500:
        return "SERVER_ERROR"
    return "API_ERROR"

@app.exception_handler(SecurityException)
async def security_exception_handler(request, exc: SecurityException):
    msg = str(exc)
    return JSONResponse(
        status_code=401,
        content={
            "statusCode": 401,
            "code": "UNAUTHORIZED",
            "message": msg,
            "detail": msg
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    msg = str(exc.detail) if exc.detail else "HTTP Exception occurred"
    code = get_error_code(exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "statusCode": exc.status_code,
            "code": code,
            "message": msg,
            "detail": msg
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    msg = "Request validation failed"
    errors = []
    for err in exc.errors():
        safe_err = dict(err)
        if "ctx" in safe_err and isinstance(safe_err["ctx"], dict):
            safe_ctx = {}
            for k, v in safe_err["ctx"].items():
                if isinstance(v, Exception):
                    safe_ctx[k] = str(v)
                else:
                    safe_ctx[k] = v
            safe_err["ctx"] = safe_ctx
        errors.append(safe_err)

    return JSONResponse(
        status_code=400,
        content={
            "statusCode": 400,
            "code": "VALIDATION_ERROR",
            "message": msg,
            "detail": errors
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc: Exception):
    msg = "Internal Server Error"
    return JSONResponse(
        status_code=500,
        content={
            "statusCode": 500,
            "code": "SERVER_ERROR",
            "message": msg,
            "detail": str(exc)
        }
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SecurityContextASGIMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            from app.core.security.context import SecurityContextHolder
            from app.core.security.jwt import decode_access_token
            import uuid
            
            headers = {k.decode("utf-8").lower(): v.decode("utf-8") for k, v in scope.get("headers", [])}
            
            # Extract or generate X-Correlation-ID
            correlation_id = headers.get("x-correlation-id", "").strip()
            if not correlation_id:
                correlation_id = f"corr-{uuid.uuid4()}"
            
            SecurityContextHolder.clear_context()
            SecurityContextHolder.set_correlation_id(correlation_id)
            
            path = scope.get("path", "")
            public_endpoints = [
                "/api/v1/health",
                "/api/v1/auth/register",
                "/api/v1/auth/login",
                "/docs",
                "/openapi.json",
                "/redoc"
            ]
            
            if not any(path.startswith(pe) for pe in public_endpoints):
                auth_header = headers.get("authorization", "")
                if not auth_header or not auth_header.startswith("Bearer "):
                    import json
                    response_body = json.dumps({
                        "statusCode": 401,
                        "code": "UNAUTHORIZED",
                        "message": "Missing or invalid authorization header",
                        "detail": "Authorization header must be Bearer token"
                    }).encode("utf-8")
                    await send({
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", str(len(response_body)).encode("utf-8"))
                        ]
                    })
                    await send({
                        "type": "http.response.body",
                        "body": response_body,
                        "more_body": False
                    })
                    return
                token = auth_header[7:].strip()
                try:
                    ctx = decode_access_token(token)
                    ctx.correlation_id = correlation_id
                    SecurityContextHolder.set_context(ctx)
                except Exception as e:
                    import json
                    response_body = json.dumps({
                        "statusCode": 401,
                        "code": "UNAUTHORIZED",
                        "message": "Invalid or expired JWT token",
                        "detail": str(e)
                    }).encode("utf-8")
                    await send({
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", str(len(response_body)).encode("utf-8"))
                        ]
                    })
                    await send({
                        "type": "http.response.body",
                        "body": response_body,
                        "more_body": False
                    })
                    return


            # Wrap send to inject X-Correlation-ID in response headers
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers_list = list(message.get("headers", []))
                    headers_list.append((b"x-correlation-id", correlation_id.encode("utf-8")))
                    message["headers"] = headers_list
                await send(message)

            await self.app(scope, receive, send_wrapper)
            return

        await self.app(scope, receive, send)

app.add_middleware(SecurityContextASGIMiddleware)

app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(auth_router, prefix="/api/v1")
app.include_router(org_router, prefix="/api/v1")
app.include_router(wf_router, prefix="/api/v1")
app.include_router(debug_router, prefix="/api/v1")
app.include_router(pkg_router, prefix="/api/v1")


