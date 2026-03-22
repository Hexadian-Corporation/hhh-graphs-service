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


class TestMarkStaleByLocationIds:
    async def test_calls_update_many_with_correct_filter(self) -> None:
        from datetime import UTC, datetime

        collection = AsyncMock()
        update_result = AsyncMock()
        update_result.modified_count = 2
        collection.update_many.return_value = update_result
        repo = MongoGraphRepository(collection=collection)

        since = datetime(2026, 1, 1, tzinfo=UTC)
        result = await repo.mark_stale_by_location_ids(
            location_ids=["loc1", "loc2"],
            reason="data_import",
            since=since,
        )

        assert result == 2
        collection.update_many.assert_called_once_with(
            {"nodes.location_id": {"$in": ["loc1", "loc2"]}},
            {"$set": {"stale": True, "stale_reason": "data_import", "stale_since": since}},
        )

    async def test_returns_zero_when_no_matching_graphs(self) -> None:
        collection = AsyncMock()
        update_result = AsyncMock()
        update_result.modified_count = 0
        collection.update_many.return_value = update_result
        repo = MongoGraphRepository(collection=collection)

        from datetime import UTC, datetime

        result = await repo.mark_stale_by_location_ids(
            location_ids=["unknown"],
            reason="data_import",
            since=datetime.now(UTC),
        )

        assert result == 0
