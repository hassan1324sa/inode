from fastapi import APIRouter
from app.core.database import db_manager

router = APIRouter()

@router.get("/health")
async def health_check():
    health_status = {
        "status": "healthy",
        "services": {
            "mongodb": "unknown"
        }
    }
    
    # Check MongoDB
    try:
        if db_manager.client:
            await db_manager.client.admin.command('ping')
            health_status["services"]["mongodb"] = "healthy"
        else:
            health_status["services"]["mongodb"] = "disconnected"
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["services"]["mongodb"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    return health_status
