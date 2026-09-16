"""Migration 002: Add Google OAuth, Identity, Action Token, and Security Collections/Indexes.

Idempotent migration script that:
1. Creates new collections: auth_identities, auth_action_tokens, oauth_transactions.
2. Applies required unique, compound, and TTL indexes.
3. Records migration status in schema_migrations collection.
"""

import asyncio
import logging
from datetime import datetime, timezone
from pymongo.asynchronous.database import AsyncDatabase
from app.core.database import db_manager, connect_to_mongo
from app.db.collections import (
    COLLECTION_AUTH_IDENTITIES,
    COLLECTION_AUTH_ACTION_TOKENS,
    COLLECTION_OAUTH_TRANSACTIONS,
    COLLECTION_AUTH_SESSIONS,
    COLLECTION_SCHEMA_MIGRATIONS,
)

logger = logging.getLogger("uvicorn")
MIGRATION_VERSION = "002_auth_google_security"


async def apply_migration(db: AsyncDatabase) -> bool:
    """Applies migration 002 idempotently."""
    logger.info(f"Checking migration '{MIGRATION_VERSION}'...")
    
    # Check if already executed
    existing = await db[COLLECTION_SCHEMA_MIGRATIONS].find_one({"version": MIGRATION_VERSION})
    if existing and existing.get("status") == "COMPLETED":
        logger.info(f"Migration '{MIGRATION_VERSION}' already completed. Skipping.")
        return True

    logger.info(f"Executing migration '{MIGRATION_VERSION}'...")

    # Ensure collections exist
    existing_colls = await db.list_collection_names()
    for coll_name in [COLLECTION_AUTH_IDENTITIES, COLLECTION_AUTH_ACTION_TOKENS, COLLECTION_OAUTH_TRANSACTIONS]:
        if coll_name not in existing_colls:
            try:
                await db.create_collection(coll_name)
                logger.info(f"Created collection '{coll_name}'.")
            except Exception as e:
                logger.warning(f"Could not create collection '{coll_name}': {e}")

    # Indexes for auth_identities
    await db[COLLECTION_AUTH_IDENTITIES].create_index(
        [("provider", 1), ("issuer", 1), ("subject", 1)],
        unique=True,
        name="uq_auth_identities_sub"
    )
    await db[COLLECTION_AUTH_IDENTITIES].create_index(
        [("user_id", 1), ("provider", 1)],
        unique=True,
        name="uq_auth_identities_user_provider"
    )
    await db[COLLECTION_AUTH_IDENTITIES].create_index(
        [("user_id", 1)],
        name="idx_auth_identities_user_id"
    )

    # Indexes for auth_action_tokens
    await db[COLLECTION_AUTH_ACTION_TOKENS].create_index(
        [("token_hash", 1)],
        unique=True,
        name="uq_action_token_hash"
    )
    await db[COLLECTION_AUTH_ACTION_TOKENS].create_index(
        [("user_id", 1), ("purpose", 1), ("consumed_at", 1)],
        name="idx_action_tokens_user_purpose"
    )
    await db[COLLECTION_AUTH_ACTION_TOKENS].create_index(
        [("expires_at", 1)],
        expireAfterSeconds=0,
        name="ttl_action_tokens_expires_at"
    )

    # Indexes for oauth_transactions
    await db[COLLECTION_OAUTH_TRANSACTIONS].create_index(
        [("state", 1)],
        unique=True,
        name="uq_oauth_transactions_state"
    )
    await db[COLLECTION_OAUTH_TRANSACTIONS].create_index(
        [("expires_at", 1)],
        expireAfterSeconds=0,
        name="ttl_oauth_transactions_expires_at"
    )

    # Ensure auth_sessions refresh token hash index
    await db[COLLECTION_AUTH_SESSIONS].create_index(
        [("refresh_token_hash", 1)],
        name="idx_auth_sessions_token_hash"
    )

    # Record migration completed
    await db[COLLECTION_SCHEMA_MIGRATIONS].update_one(
        {"version": MIGRATION_VERSION},
        {
            "$set": {
                "version": MIGRATION_VERSION,
                "description": "Add Google OAuth identities, action tokens, and session indexes",
                "applied_at": datetime.now(timezone.utc),
                "status": "COMPLETED"
            }
        },
        upsert=True
    )
    logger.info(f"Migration '{MIGRATION_VERSION}' applied successfully!")
    return True


if __name__ == "__main__":
    async def main():
        await connect_to_mongo()
        if db_manager.db is not None:
            await apply_migration(db_manager.db)
        else:
            logger.error("Database connection unavailable.")
    asyncio.run(main())
