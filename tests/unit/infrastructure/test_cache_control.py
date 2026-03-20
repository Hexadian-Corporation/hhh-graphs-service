"""Tests for Cache-Control headers on graph endpoints."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from src.domain.models.graph import Edge, Graph, Node

SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"  # gitleaks:allow


def _make_token(permissions: list[str]) -> str:
    claims: dict = {
        "sub": "user-1",
        "username": "testuser",
        "permissions": permissions,
        "exp": int(time.time()) + 300,
    }
    return pyjwt.encode(claims, SECRET, algorithm="HS256")


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _sample_graph() -> Graph:
    return Graph(
        id="abc123",
        name="TestGraph",
        nodes=[Node(location_id="loc1", label="A")],
        edges=[Edge(source_id="loc1", target_id="loc2", distance=100.0, travel_type="quantum")],
    )


@pytest.fixture()
def mock_graph_service() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def client(mock_graph_service: MagicMock) -> TestClient:
    with patch("src.infrastructure.config.dependencies.MongoClient"):
        from fastapi import FastAPI
        from hexadian_auth_common.fastapi import (
            JWTAuthDependency,
            _stub_jwt_auth,
            register_exception_handlers,
        )

        from src.infrastructure.adapters.inbound.api.graph_router import init_router, router
        from src.infrastructure.config.settings import Settings

        settings = Settings(jwt_secret=SECRET, mongo_uri="mongodb://localhost:27017", mongo_db="test_db")

        app = FastAPI()
        jwt_auth = JWTAuthDependency(secret=settings.jwt_secret, algorithm=settings.jwt_algorithm)
        app.dependency_overrides[_stub_jwt_auth] = jwt_auth
        register_exception_handlers(app)

        init_router(mock_graph_service)
        app.include_router(router)

        yield TestClient(app)


class TestNoCacheControlOnMutations:
    """POST and DELETE endpoints must NOT include a Cache-Control header."""

    def test_create_graph_has_no_cache_control(self, client: TestClient, mock_graph_service: MagicMock) -> None:
        mock_graph_service.create.return_value = _sample_graph()
        token = _make_token(permissions=["hhh:graphs:write"])
        resp = client.post(
            "/graphs/",
            json={"name": "TestGraph", "nodes": [], "edges": []},
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        assert "Cache-Control" not in resp.headers

    def test_generate_graph_has_no_cache_control(self, client: TestClient, mock_graph_service: MagicMock) -> None:
        mock_graph_service.generate.return_value = _sample_graph()
        token = _make_token(permissions=["hhh:graphs:write"])
        resp = client.post(
            "/graphs/generate",
            json={"location_ids": ["loc1"]},
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        assert "Cache-Control" not in resp.headers

    def test_delete_graph_has_no_cache_control(self, client: TestClient, mock_graph_service: MagicMock) -> None:
        mock_graph_service.delete.return_value = None
        token = _make_token(permissions=["hhh:graphs:delete"])
        resp = client.delete("/graphs/abc123", headers=_auth_header(token))
        assert resp.status_code == 204
        assert "Cache-Control" not in resp.headers
