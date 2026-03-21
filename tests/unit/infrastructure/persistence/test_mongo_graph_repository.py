from unittest.mock import AsyncMock

from bson import ObjectId

from src.domain.models.graph import Graph
from src.infrastructure.adapters.outbound.persistence.mongo_graph_repository import MongoGraphRepository


def _make_doc(hash_value: str = "abc") -> dict:
    return {
        "_id": ObjectId("aaaaaaaaaaaaaaaaaaaaaaaa"),
        "name": "test",
        "hash": hash_value,
        "nodes": [],
        "edges": [],
        "stale": False,
        "stale_reason": None,
        "stale_since": None,
    }


class TestFindByHash:
    async def test_returns_graph_when_found(self) -> None:
        collection = AsyncMock()
        collection.find_one.return_value = _make_doc("deadbeef")
        repo = MongoGraphRepository(collection=collection)

        result = await repo.find_by_hash("deadbeef")

        collection.find_one.assert_called_once_with({"hash": "deadbeef"})
        assert isinstance(result, Graph)
        assert result.hash == "deadbeef"

    async def test_returns_none_when_not_found(self) -> None:
        collection = AsyncMock()
        collection.find_one.return_value = None
        repo = MongoGraphRepository(collection=collection)

        result = await repo.find_by_hash("missing")

        assert result is None
