from fastapi import APIRouter
from app.core.database import get_database
from app.core.config import settings

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check():
    db = get_database()
    db_status = "disconnected"
    if db is not None:
        try:
            await db.client.admin.command("ping")
            db_status = "connected"
        except Exception:
            db_status = "error"

    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "database": {
            "name": settings.DATABASE_NAME,
            "status": db_status
        }
    }
