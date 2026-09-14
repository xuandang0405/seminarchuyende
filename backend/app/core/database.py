import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger("uvicorn")


class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None


db_manager = Database()


async def connect_to_mongo():
    connection_str = settings.mongodb_connection_string
    # Mask password for secure logging
    masked_url = connection_str
    if "@" in connection_str:
        prefix = connection_str.split("@")[0]
        suffix = connection_str.split("@")[1]
        if ":" in prefix:
            protocol_user = prefix.rsplit(":", 1)[0]
            masked_url = f"{protocol_user}:****@{suffix}"

    logger.info(f"Connecting to MongoDB at {masked_url}...")
    try:
        db_manager.client = AsyncIOMotorClient(
            connection_str,
            serverSelectionTimeoutMS=5000
        )
        db_manager.db = db_manager.client[settings.DATABASE_NAME]
        # Ping server to verify connection
        await db_manager.client.admin.command("ping")
        logger.info(f"Connected successfully to MongoDB database: '{settings.DATABASE_NAME}'")
    except Exception as e:
        logger.warning(
            f"Could not connect to MongoDB ({e}). "
            "The app will start, but database operations will fail until MongoDB is accessible."
        )


async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    if db_manager.client:
        db_manager.client.close()
        logger.info("MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    return db_manager.db
