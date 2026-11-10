"""Pytest configuration and async test client fixtures using mongomock."""

import asyncio
import os
os.environ.update(APP_ENV="test", PAYMENT_MODE="mock", DEBUG="false", ALLOW_MOCK_DATABASE="true",
                  SECRET_KEY="isolated-test-key-not-used-outside-test-process-2026")
import pytest
import mongomock
from httpx import AsyncClient, ASGITransport

from app.core.database import db_manager
from app.db.collections import ALL_COLLECTIONS
from app.db.indexes import create_all_indexes
from app.db.seed import seed_database
from app.main import app


class AsyncMockCollection:
    """Wrapper around mongomock collection to support async/await methods like PyMongo Async."""
    def __init__(self, sync_col):
        self._col = sync_col

    async def find_one(self, *args, **kwargs):
        return self._col.find_one(*args, **kwargs)

    def find(self, *args, **kwargs):
        cursor = self._col.find(*args, **kwargs)
        return AsyncMockCursor(cursor)

    async def insert_one(self, *args, **kwargs):
        return self._col.insert_one(*args, **kwargs)

    async def insert_many(self, *args, **kwargs):
        return self._col.insert_many(*args, **kwargs)

    async def update_one(self, *args, **kwargs):
        return self._col.update_one(*args, **kwargs)

    async def update_many(self, *args, **kwargs):
        return self._col.update_many(*args, **kwargs)

    async def find_one_and_update(self, *args, **kwargs):
        return self._col.find_one_and_update(*args, **kwargs)

    async def find_one_and_delete(self, *args, **kwargs):
        if hasattr(self._col, "find_one_and_delete"):
            return self._col.find_one_and_delete(*args, **kwargs)
        doc = self._col.find_one(*args, **kwargs)
        if doc:
            self._col.delete_one({"_id": doc["_id"]})
        return doc

    async def delete_one(self, *args, **kwargs):
        return self._col.delete_one(*args, **kwargs)

    async def delete_many(self, *args, **kwargs):
        return self._col.delete_many(*args, **kwargs)

    async def count_documents(self, *args, **kwargs):
        return self._col.count_documents(*args, **kwargs)

    async def distinct(self, *args, **kwargs):
        return self._col.distinct(*args, **kwargs)

    async def create_index(self, *args, **kwargs):
        try:
            return self._col.create_index(*args, **kwargs)
        except Exception:
            return None

    def aggregate(self, *args, **kwargs):
        res = self._col.aggregate(*args, **kwargs)
        return AsyncMockCursor(res)


class AsyncMockCursor:
    def __init__(self, sync_cursor):
        self._cursor = sync_cursor

    def skip(self, n):
        if hasattr(self._cursor, "skip"):
            self._cursor.skip(n)
        return self

    def limit(self, n):
        if hasattr(self._cursor, "limit"):
            self._cursor.limit(n)
        return self

    def sort(self, *args, **kwargs):
        if hasattr(self._cursor, "sort"):
            self._cursor.sort(*args, **kwargs)
        return self

    async def to_list(self, length=None):
        items = list(self._cursor)
        if length is not None:
            return items[:length]
        return items


class AsyncMockDatabase:
    def __init__(self):
        self._client = mongomock.MongoClient()
        self._db = self._client["tour_guide_test"]

    def __getitem__(self, name):
        return AsyncMockCollection(self._db[name])

    async def list_collection_names(self):
        return list(self._db.list_collection_names())

    async def create_collection(self, name):
        return AsyncMockCollection(self._db.create_collection(name))


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_test_db(tmp_path):
    """Initializes in-memory test database with seeded collections."""
    mock_db = AsyncMockDatabase()
    db_manager.db = mock_db
    db_manager.is_connected = True
    db_manager.is_mock = True

    # Isolate generated/uploaded media from user data.
    from app.core.config import settings
    from pathlib import Path
    from app.services.audio_service import audio_service
    previous_media = settings.MEDIA_STORAGE_DIR
    settings.MEDIA_STORAGE_DIR = str(tmp_path)
    (tmp_path / "audio").mkdir()
    (tmp_path / "images").mkdir()
    # Fixtures use real test bytes; runtime must never fabricate missing audio.
    (tmp_path / "audio" / "poi_test_01_vi.mp3").write_bytes(b"ID3" + b"review-audio" * 30)
    (tmp_path / "audio" / "poi_test_02_vi.mp3").write_bytes(b"ID3" + b"review-audio" * 30)
    await seed_database(mock_db)
    yield mock_db
    settings.MEDIA_STORAGE_DIR = previous_media


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers={"Origin": "http://test"}) as ac:
        yield ac
