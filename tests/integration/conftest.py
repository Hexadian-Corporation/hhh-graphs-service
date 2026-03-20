"""Integration-test fixtures: real MongoDB via testcontainers, real FastAPI app."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hexadian_auth_common.fastapi import (
    JWTAuthDependency,
    _stub_jwt_auth,
    register_exception_handlers,
)
from pymongo import MongoClient
from pymongo.collection import Collection
from testcontainers.mongodb import MongoDbContainer

from src.application.services.graph_service_impl import GraphServiceImpl
from src.infrastructure.adapters.inbound.api.graph_router import init_router, router
from src.infrastructure.adapters.outbound.persistence.mongo_graph_repository import (
    MongoGraphRepository,
)
from tests.auth_helpers import TEST_JWT_ALGORITHM, TEST_JWT_SECRET


@pytest.fixture(scope="session")
def mongo_container() -> Generator[MongoDbContainer, None, None]:
    """Start a MongoDB container once per test session."""
    with MongoDbContainer("mongo:7") as container:
        yield container


@pytest.fixture(scope="session")
def mongo_client(mongo_container: MongoDbContainer) -> Generator[MongoClient, None, None]:
    """Session-scoped MongoClient connected to the test container."""
    client: MongoClient = MongoClient(mongo_container.get_connection_url())
    yield client
    client.close()


@pytest.fixture(scope="session")
def collection(mongo_client: MongoClient) -> Collection:
    """Session-scoped MongoDB collection for graphs."""
    return mongo_client["hhh_graphs_test"]["graphs"]


@pytest.fixture(autouse=True)
def clean_db(collection: Collection) -> Generator[None, None, None]:
    """Wipe the graphs collection before each test for isolation."""
    collection.delete_many({})
    yield


@pytest.fixture(scope="session")
def client(collection: Collection) -> Generator[TestClient, None, None]:
    """Session-scoped TestClient wired to real repository + service."""
    # --- Stub MapsClient (not needed for CRUD integration tests) ---
    from unittest.mock import MagicMock

    from src.application.ports.outbound.maps_client import MapsClient

    maps_stub = MagicMock(spec=MapsClient)

    repo = MongoGraphRepository(collection)
    service = GraphServiceImpl(repository=repo, maps_client=maps_stub)

    jwt_auth = JWTAuthDependency(secret=TEST_JWT_SECRET, algorithm=TEST_JWT_ALGORITHM)

    init_router(service)

    app = FastAPI()
    app.dependency_overrides[_stub_jwt_auth] = jwt_auth
    register_exception_handlers(app)
    app.include_router(router)

    yield TestClient(app)
