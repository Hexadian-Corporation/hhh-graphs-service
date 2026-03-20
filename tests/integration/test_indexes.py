"""Integration tests for MongoDB indexes on the graphs collection."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from testcontainers.mongodb import MongoDbContainer

from src.infrastructure.config.dependencies import AppModule
from src.infrastructure.config.settings import Settings

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fresh_collection(mongo_client: MongoClient) -> Generator[Collection, None, None]:
    """Function-scoped fresh collection with no custom indexes (only _id_)."""
    col = mongo_client["hhh_graphs_index_test"]["graphs"]
    col.drop()
    yield col
    col.drop()


@pytest.fixture()
def indexed_collection(fresh_collection: Collection) -> Collection:
    """Fresh collection with all indexes applied (same as AppModule.configure())."""
    fresh_collection.create_index([("name", ASCENDING)])
    fresh_collection.create_index([("nodes.location_id", ASCENDING)])
    fresh_collection.create_index("hash", unique=True, sparse=True)
    return fresh_collection


# ---------------------------------------------------------------------------
# TestGraphIndexes
# ---------------------------------------------------------------------------


class TestGraphIndexes:
    """Verify index properties on the graphs collection."""

    def test_all_expected_indexes_are_created(self, indexed_collection: Collection) -> None:
        index_info = indexed_collection.index_information()
        # index_info values contain a "key" list of (field, direction) tuples; [0][0] is the field name.
        index_key_fields = {v["key"][0][0] for k, v in index_info.items() if k != "_id_"}
        assert "name" in index_key_fields
        assert "nodes.location_id" in index_key_fields
        assert "hash" in index_key_fields

    def test_default_id_index_exists(self, indexed_collection: Collection) -> None:
        index_info = indexed_collection.index_information()
        assert "_id_" in index_info

    def test_index_names(self, indexed_collection: Collection) -> None:
        index_info = indexed_collection.index_information()
        assert "name_1" in index_info
        assert "nodes.location_id_1" in index_info
        assert "hash_1" in index_info

    def test_name_index_key_is_ascending(self, indexed_collection: Collection) -> None:
        index_info = indexed_collection.index_information()
        assert index_info["name_1"]["key"] == [("name", ASCENDING)]

    def test_nodes_location_id_index_key_is_ascending(self, indexed_collection: Collection) -> None:
        index_info = indexed_collection.index_information()
        assert index_info["nodes.location_id_1"]["key"] == [("nodes.location_id", ASCENDING)]

    def test_hash_index_is_unique(self, indexed_collection: Collection) -> None:
        index_info = indexed_collection.index_information()
        assert index_info["hash_1"].get("unique") is True

    def test_hash_index_is_sparse(self, indexed_collection: Collection) -> None:
        index_info = indexed_collection.index_information()
        assert index_info["hash_1"].get("sparse") is True

    def test_hash_index_key_is_ascending(self, indexed_collection: Collection) -> None:
        index_info = indexed_collection.index_information()
        assert index_info["hash_1"]["key"] == [("hash", ASCENDING)]

    def test_sparse_hash_index_allows_multiple_docs_without_hash(self, indexed_collection: Collection) -> None:
        """sparse=True means multiple documents with a missing hash field are allowed."""
        indexed_collection.insert_many([{"name": "a"}, {"name": "b"}])
        assert indexed_collection.count_documents({}) == 2

    def test_create_indexes_twice_is_idempotent(self, fresh_collection: Collection) -> None:
        """Calling create_index() for the same index twice must not raise."""
        for _ in range(2):
            fresh_collection.create_index([("name", ASCENDING)])
            fresh_collection.create_index([("nodes.location_id", ASCENDING)])
            fresh_collection.create_index("hash", unique=True, sparse=True)

        index_info = fresh_collection.index_information()
        # Exactly 4 indexes: _id_ + 3 custom ones
        assert len(index_info) == 4


# ---------------------------------------------------------------------------
# TestIndexCreation
# ---------------------------------------------------------------------------


class TestIndexCreation:
    """Verify that indexes are created when AppModule is configured or app starts."""

    def test_app_module_creates_indexes(self, mongo_container: MongoDbContainer) -> None:
        """AppModule.configure() creates all indexes on the target collection."""
        settings = Settings(
            jwt_secret="test-secret",
            mongo_uri=mongo_container.get_connection_url(),
            mongo_db="hhh_graphs_module_test",
        )

        client: MongoClient = MongoClient(settings.mongo_uri)
        try:
            client[settings.mongo_db].drop_collection("graphs")

            module = AppModule(settings)
            module.configure()

            index_info = client[settings.mongo_db]["graphs"].index_information()
            assert "name_1" in index_info
            assert "nodes.location_id_1" in index_info
            assert "hash_1" in index_info
        finally:
            client[settings.mongo_db].drop_collection("graphs")
            client.close()

    def test_app_startup_creates_all_indexes(
        self, mongo_container: MongoDbContainer, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Full app startup (module import) creates all indexes via AppModule."""
        import sys

        import src.infrastructure.adapters.inbound.api.graph_router as gr_module

        connection_url = mongo_container.get_connection_url()
        monkeypatch.setenv("HHH_GRAPHS_MONGO_URI", connection_url)
        monkeypatch.setenv("HHH_GRAPHS_MONGO_DB", "hhh_graphs_startup_test")
        monkeypatch.setenv("HEXADIAN_AUTH_JWT_SECRET", "test-secret")
        # Prevent the module-level create_app() from mutating the shared router state
        # (init_router sets a module-level global used by other integration tests).
        monkeypatch.setattr(gr_module, "init_router", lambda _: None)

        # Remove any cached copy so the module-level ``app = create_app()`` re-runs
        # with our patched environment variables.
        sys.modules.pop("src.main", None)

        client: MongoClient = MongoClient(connection_url)
        try:
            client["hhh_graphs_startup_test"].drop_collection("graphs")

            import src.main  # noqa: F401 -- triggers module-level app = create_app()

            index_info = client["hhh_graphs_startup_test"]["graphs"].index_information()
            assert "name_1" in index_info
            assert "nodes.location_id_1" in index_info
            assert "hash_1" in index_info
        finally:
            sys.modules.pop("src.main", None)
            client["hhh_graphs_startup_test"].drop_collection("graphs")
            client.close()
