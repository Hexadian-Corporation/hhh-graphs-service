"""Integration-test fixtures: real MongoDB via testcontainers, real FastAPI app."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hexadian_auth_common.fastapi import (
    JWTAuthDependency,
    _stub_jwt_auth,
    register_exception_handlers,
)
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo import MongoClient
from pymongo.collection import Collection
from testcontainers.mongodb import MongoDbContainer

from src.application.ports.outbound.maps_client import MapsClient
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
    """Session-scoped sync MongoClient for direct DB operations (cleanup, index tests)."""
    client: MongoClient = MongoClient(mongo_container.get_connection_url())
    yield client
    client.close()


@pytest.fixture(scope="session")
def collection(mongo_client: MongoClient) -> Collection:
    """Session-scoped sync MongoDB collection for direct DB operations."""
    return mongo_client["hhh_graphs_test"]["graphs"]


@pytest.fixture(scope="session")
def motor_collection(mongo_container: MongoDbContainer) -> Generator[AsyncIOMotorCollection, None, None]:
    """Session-scoped async motor collection for the repository."""
    motor_client = AsyncIOMotorClient(mongo_container.get_connection_url())
    yield motor_client["hhh_graphs_test"]["graphs"]
    motor_client.close()


@pytest.fixture(scope="session")
def maps_mock() -> AsyncMock:
    """Session-scoped MapsClient mock. Configured per-test in generation tests."""
    return AsyncMock(spec=MapsClient)


@pytest.fixture(scope="session")
def graph_service(motor_collection: AsyncIOMotorCollection, maps_mock: AsyncMock) -> GraphServiceImpl:
    """Session-scoped graph service wired to real repo + mock maps client."""
    repo = MongoGraphRepository(motor_collection)
    return GraphServiceImpl(repository=repo, maps_client=maps_mock)


@pytest.fixture(autouse=True)
def clean_db(
    collection: Collection,
    graph_service: GraphServiceImpl,
    maps_mock: AsyncMock,
) -> Generator[None, None, None]:
    """Wipe the graphs collection, reset mock, and clear caches before each test."""
    collection.delete_many({})
    maps_mock.reset_mock()
    graph_service._invalidate_cache()
    yield


@pytest.fixture(scope="session")
def client(graph_service: GraphServiceImpl) -> Generator[TestClient, None, None]:
    """Session-scoped TestClient wired to real repository + service."""
    jwt_auth = JWTAuthDependency(secret=TEST_JWT_SECRET, algorithm=TEST_JWT_ALGORITHM)

    init_router(graph_service)

    app = FastAPI()
    app.dependency_overrides[_stub_jwt_auth] = jwt_auth
    register_exception_handlers(app)
    app.include_router(router)

    with TestClient(app) as tc:
        yield tc
