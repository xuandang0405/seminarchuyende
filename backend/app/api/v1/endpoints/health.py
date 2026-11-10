from fastapi import APIRouter, Response
from app.core.database import db_manager
from app.core.database import get_database
from app.core.config import settings

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check(response: Response):
    db = get_database()
    db_status = "disconnected"
    if db is not None:
        try:
            if not db_manager.is_mock:
                await db.client.admin.command("ping")
            db_status = "connected"
        except Exception:
            db_status = "error"

    healthy = db_status == "connected"
    if not healthy:
        response.status_code = 503
    return {
        "status": "healthy" if healthy else "unhealthy",
        "mock_database": db_manager.is_mock,
        "project": settings.PROJECT_NAME,
        "database": {
            "name": settings.DATABASE_NAME,
            "status": db_status
        }
    }
