"""In-memory Async Database implementation using mongomock for testing and resilient fallback."""

import mongomock


class AsyncMockCollection:
    """Wrapper around mongomock collection to support async/await methods matching PyMongo Async."""
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

    async def delete_one(self, *args, **kwargs):
        return self._col.delete_one(*args, **kwargs)

    async def delete_many(self, *args, **kwargs):
        return self._col.delete_many(*args, **kwargs)

    async def count_documents(self, *args, **kwargs):
        return self._col.count_documents(*args, **kwargs)

    async def create_index(self, *args, **kwargs):
        try:
            return self._col.create_index(*args, **kwargs)
        except Exception:
            return None

    async def distinct(self, *args, **kwargs):
        return self._col.distinct(*args, **kwargs)

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
    def __init__(self, db_name="tour_guide"):
        self._client = mongomock.MongoClient()
        self._db = self._client[db_name]

    def __getitem__(self, name):
        return AsyncMockCollection(self._db[name])

    async def list_collection_names(self):
        return list(self._db.list_collection_names())

    async def create_collection(self, name):
        return AsyncMockCollection(self._db.create_collection(name))
