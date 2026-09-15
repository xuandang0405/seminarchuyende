from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database


class BaseRepository:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name

    @property
    def db(self) -> AsyncIOMotorDatabase:
        db = get_database()
        if db is None:
            raise RuntimeError("Database connection is not initialized")
        return db

    @property
    def collection(self):
        return self.db[self.collection_name]

    async def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"_id": doc_id})

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one(query)

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
        return await cursor.to_list(length=limit)

    async def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        return await self.collection.count_documents(query or {})

    async def insert_one(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        await self.collection.insert_one(doc)
        return doc

    async def update_by_id(self, doc_id: str, update_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        await self.collection.update_one({"_id": doc_id}, {"$set": update_dict})
        return await self.get_by_id(doc_id)

    async def delete_by_id(self, doc_id: str) -> bool:
        result = await self.collection.delete_one({"_id": doc_id})
        return result.deleted_count > 0
