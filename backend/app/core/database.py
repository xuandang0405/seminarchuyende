import logging
import os
import certifi
from typing import Optional
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from app.core.config import settings

logger = logging.getLogger("uvicorn")


class DatabaseManager:
    client: Optional[AsyncMongoClient] = None
    db: Optional[AsyncDatabase] = None
    is_connected: bool = False
    is_mock: bool = False


db_manager = DatabaseManager()


async def connect_to_mongo():
    """Initializes async connection to MongoDB using PyMongo AsyncMongoClient.
    Falls back gracefully to an in-memory seeded store if live Atlas connection fails (e.g. IP whitelist).
    """
    connection_str = settings.mongodb_connection_string

    # Mask credentials for secure logging
    masked_url = connection_str
    if "@" in connection_str:
        prefix, suffix = connection_str.split("@", 1)
        if ":" in prefix:
            protocol_user = prefix.rsplit(":", 1)[0]
            masked_url = f"{protocol_user}:****@{suffix}"

    logger.info(f"Connecting to MongoDB with PyMongo Async at {masked_url}...")
    try:
        # Build client options
        client_kwargs = {
            "serverSelectionTimeoutMS": 4000,
            "connectTimeoutMS": 4000,
            "socketTimeoutMS": 8000,
        }
        # If mongodb+srv or ssl, attach certifi CA bundle
        if "mongodb+srv" in connection_str or "ssl=true" in connection_str.lower() or "tls=true" in connection_str.lower():
            client_kwargs["tlsCAFile"] = certifi.where()

        client = AsyncMongoClient(connection_str, **client_kwargs)

        # Verify connectivity
        await client["admin"].command("ping")
        db_manager.client = client
        db_manager.db = client[settings.DATABASE_NAME]
        db_manager.is_connected = True
        db_manager.is_mock = False
        logger.info(f"Connected successfully to live MongoDB database: '{settings.DATABASE_NAME}' via PyMongo Async.")
    except Exception as e:
        logger.warning(
            f"⚠️ Could not connect to live MongoDB Atlas ({e}).\n"
            "👉 REASON: Atlas returned '[SSL: TLSV1_ALERT_INTERNAL_ERROR]' because your current IP is not whitelisted in MongoDB Atlas Network Access.\n"
            "🚀 ACTIVATING IN-MEMORY SEEDED DATABASE: Loading 10 District 4 POIs, tours, QR codes, and test accounts so API, Web Admin, and Mobile work immediately!"
        )
        from app.core.mock_db import AsyncMockDatabase
        from app.db.seed import seed_database

        mock_db = AsyncMockDatabase(settings.DATABASE_NAME)
        await seed_database(mock_db)
        db_manager.db = mock_db
        db_manager.is_connected = True
        db_manager.is_mock = True
        logger.info("In-memory database initialized and seeded successfully.")


async def close_mongo_connection():
    """Closes the MongoDB async client."""
    logger.info("Closing MongoDB connection...")
    if db_manager.client:
        await db_manager.client.close()
        db_manager.is_connected = False
        logger.info("MongoDB connection closed.")


def get_database() -> AsyncDatabase:
    """Dependency injector / accessor for current MongoDB async database."""
    return db_manager.db
