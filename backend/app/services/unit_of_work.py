"""Run related MongoDB writes atomically; in-memory fallback is test/dev only."""
from fastapi import HTTPException
from app.core.config import settings
from app.core.database import db_manager, get_database


async def run_transaction(operation):
    if db_manager.is_mock and settings.is_development:
        return await operation(None)
    try:
        async with get_database().client.start_session() as session:
            return await session.with_transaction(operation)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, "Không thể hoàn tất thay đổi. Dữ liệu chưa được commit; vui lòng thử lại.") from exc
