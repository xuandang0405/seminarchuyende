"""Database initialization, collections creation, index setup and seeding entrypoint.

Can be run via:
    python -m app.db.init_db
"""

import asyncio
import logging
from app.core.config import settings
from app.core.database import db_manager, connect_to_mongo, close_mongo_connection
from app.db.collections import ALL_COLLECTIONS
from app.db.indexes import create_all_indexes
from app.db.seed import seed_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")


async def init_database():
    """Initializes collections, indexes and seed data."""
    logger.info("Initializing TourVoice database schema...")
    await connect_to_mongo()

    db = db_manager.db
    if db is None or not db_manager.is_connected:
        logger.error("Cannot initialize database: Not connected to MongoDB.")
        return

    # Check and create missing collections
    existing_collections = await db.list_collection_names()
    logger.info(f"Existing collections ({len(existing_collections)}): {existing_collections}")

    for coll_name in ALL_COLLECTIONS:
        if coll_name not in existing_collections:
            try:
                await db.create_collection(coll_name)
                logger.info(f"Created collection: '{coll_name}'")
            except Exception as e:
                logger.warning(f"Collection '{coll_name}' could not be created or already exists: {e}")

    # Create Indexes
    await create_all_indexes(db)

    # Seed initial data
    await seed_database(db)

    logger.info("TourVoice database initialization finished successfully!")


if __name__ == "__main__":
    asyncio.run(init_database())
