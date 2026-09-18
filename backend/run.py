import os
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    reload_flag = os.environ.get("UVICORN_RELOAD", "false").lower() in ("1", "true")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=reload_flag,
    )
