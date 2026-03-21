from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from src.application.ports.outbound.graph_repository import GraphRepository
from src.domain.models.graph import Graph
from src.infrastructure.adapters.outbound.persistence.graph_persistence_mapper import GraphPersistenceMapper


class MongoGraphRepository(GraphRepository):
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

    async def save(self, graph: Graph) -> Graph:
        doc = GraphPersistenceMapper.to_document(graph)
        if graph.id:
            await self._collection.replace_one({"_id": ObjectId(graph.id)}, doc, upsert=True)
            return graph
        result = await self._collection.insert_one(doc)
        graph.id = str(result.inserted_id)
        return graph

    async def find_by_id(self, graph_id: str) -> Graph | None:
        doc = await self._collection.find_one({"_id": ObjectId(graph_id)})
        if doc is None:
            return None
        return GraphPersistenceMapper.to_domain(doc)

    async def find_all(self) -> list[Graph]:
        return [GraphPersistenceMapper.to_domain(doc) async for doc in self._collection.find()]

    async def delete(self, graph_id: str) -> bool:
        result = await self._collection.delete_one({"_id": ObjectId(graph_id)})
        return result.deleted_count > 0

    async def find_by_hash(self, hash_value: str) -> Graph | None:
        doc = await self._collection.find_one({"hash": hash_value})
        if doc is None:
            return None
        return GraphPersistenceMapper.to_domain(doc)
