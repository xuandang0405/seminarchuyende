"""Base Repository for MongoDB Async access.

Provides clean CRUD methods, projection, and pagination.
Uses PyMongo AsyncMongoClient.
"""

from typing import Any, Dict, List, Optional
from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase
from app.core.database import get_database


def build_id_filter(doc_id: Any) -> Dict[str, Any]:
    """
    Safely builds a query for MongoDB _id matching both ObjectId and string formats.
    Prevents 500 errors when database documents use ObjectId while client sends string ID.
    """
    if isinstance(doc_id, ObjectId):
        return {"_id": doc_id}
    if isinstance(doc_id, str):
        if ObjectId.is_valid(doc_id):
            return {"_id": {"$in": [doc_id, ObjectId(doc_id)]}}
        return {"_id": doc_id}
    return {"_id": doc_id}


def serialize_mongo_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Normalizes MongoDB document by ensuring _id is string and id is populated."""
    if not doc:
        return doc
    res = dict(doc)
    if "_id" in res:
        res["_id"] = str(res["_id"])
        if "id" not in res:
            res["id"] = res["_id"]
    return res


class BaseRepository:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    @property
    def db(self) -> AsyncDatabase:
        db = get_database()
        if db is None:
            raise RuntimeError("MongoDB connection is not initialized. Please check network/Atlas status.")
        return db

    @property
    def collection(self):
        return self.db[self.collection_name]

    async def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one(build_id_filter(doc_id))
        return serialize_mongo_doc(doc)

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one(query)
        return serialize_mongo_doc(doc)

    async def list(
        self,
        query: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 50,
        sort: Optional[List[tuple]] = None
    ) -> List[Dict[str, Any]]:
        q = query or {}
        cursor = self.collection.find(q).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)
        items = await cursor.to_list(length=limit)
        return [serialize_mongo_doc(it) for it in items]

    async def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        return await self.collection.count_documents(query or {})

    async def insert_one(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        await self.collection.insert_one(doc)
        return serialize_mongo_doc(doc)

    async def update_by_id(self, doc_id: str, update_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        await self.collection.update_one(build_id_filter(doc_id), {"$set": update_dict})
        return await self.get_by_id(doc_id)

    async def delete_by_id(self, doc_id: str) -> bool:
        result = await self.collection.delete_one(build_id_filter(doc_id))
        return result.deleted_count > 0

    async def aggregate_to_list(self, collection_or_name, pipeline: List[Dict[str, Any]], length: Optional[int] = None) -> List[Dict[str, Any]]:
        import inspect
        col = self.db[collection_or_name] if isinstance(collection_or_name, str) else collection_or_name
        cursor = col.aggregate(pipeline)
        if inspect.isawaitable(cursor):
            cursor = await cursor
        return await cursor.to_list(length=length)

