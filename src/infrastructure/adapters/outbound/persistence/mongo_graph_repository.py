from bson import ObjectId
from pymongo.collection import Collection

from src.application.ports.outbound.graph_repository import GraphRepository
from src.domain.models.graph import Graph
from src.infrastructure.adapters.outbound.persistence.graph_persistence_mapper import GraphPersistenceMapper


class MongoGraphRepository(GraphRepository):

    def __init__(self, collection: Collection) -> None:
        self._collection = collection

    def save(self, graph: Graph) -> Graph:
        doc = GraphPersistenceMapper.to_document(graph)
        if graph.id:
            self._collection.replace_one({"_id": ObjectId(graph.id)}, doc, upsert=True)
            return graph
        result = self._collection.insert_one(doc)
        graph.id = str(result.inserted_id)
        return graph

    def find_by_id(self, graph_id: str) -> Graph | None:
        doc = self._collection.find_one({"_id": ObjectId(graph_id)})
        if doc is None:
            return None
        return GraphPersistenceMapper.to_domain(doc)

    def find_all(self) -> list[Graph]:
        return [GraphPersistenceMapper.to_domain(doc) for doc in self._collection.find()]

    def delete(self, graph_id: str) -> bool:
        result = self._collection.delete_one({"_id": ObjectId(graph_id)})
        return result.deleted_count > 0
