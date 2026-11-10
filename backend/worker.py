"""Run separately: python worker.py. Shares MongoDB queue and media with the API."""
import asyncio
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.services.localization_worker import run_job_loop

async def main():
    settings.validate_runtime()
    await connect_to_mongo()
    try:
        await run_job_loop()
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
