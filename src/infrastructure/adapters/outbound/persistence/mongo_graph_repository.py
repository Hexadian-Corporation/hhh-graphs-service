from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection

from src.application.ports.outbound.graph_repository import GraphRepository
from src.domain.models.graph import Graph
from src.infrastructure.adapters.outbound.persistence.graph_persistence_mapper import GraphPersistenceMapper


class MongoGraphRepository(GraphRepository):
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

    @staticmethod
    def _to_object_id(value: str) -> ObjectId | None:
        try:
            return ObjectId(value)
        except InvalidId:
            return None

    async def save(self, graph: Graph) -> Graph:
        doc = GraphPersistenceMapper.to_document(graph)
        if graph.id:
            oid = self._to_object_id(graph.id)
            if oid is None:
                return graph
            await self._collection.replace_one({"_id": oid}, doc, upsert=True)
            return graph
        result = await self._collection.insert_one(doc)
        graph.id = str(result.inserted_id)
        return graph

    async def find_by_id(self, graph_id: str) -> Graph | None:
        oid = self._to_object_id(graph_id)
        if oid is None:
            return None
        doc = await self._collection.find_one({"_id": oid})
        if doc is None:
            return None
        return GraphPersistenceMapper.to_domain(doc)

    async def find_all(self) -> list[Graph]:
        return [GraphPersistenceMapper.to_domain(doc) async for doc in self._collection.find()]

    async def delete(self, graph_id: str) -> bool:
        oid = self._to_object_id(graph_id)
        if oid is None:
            return False
        result = await self._collection.delete_one({"_id": oid})
        return result.deleted_count > 0

    async def find_by_hash(self, hash_value: str) -> Graph | None:
        doc = await self._collection.find_one({"hash": hash_value})
        if doc is None:
            return None
        return GraphPersistenceMapper.to_domain(doc)

    async def mark_stale_by_location_ids(self, location_ids: list[str], reason: str, since: datetime) -> int:
        result = await self._collection.update_many(
            {"nodes.location_id": {"$in": location_ids}},
            {"$set": {"stale": True, "stale_reason": reason, "stale_since": since}},
        )
        return result.modified_count
