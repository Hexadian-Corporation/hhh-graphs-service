"""Tests for JWT authentication on graph router endpoints."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from src.domain.models.graph import Edge, Graph, Node

SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"  # gitleaks:allow


def _make_token(permissions: list[str] | None = None, expired: bool = False) -> str:
    claims: dict = {
        "sub": "user-1",
        "username": "testuser",
        "permissions": permissions or [],
        "exp": int(time.time()) + (-10 if expired else 300),
    }
    return pyjwt.encode(claims, SECRET, algorithm="HS256")


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _sample_graph() -> Graph:
    return Graph(
        id="abc123",
        name="TestGraph",
        nodes=[Node(location_id="loc1", label="A"), Node(location_id="loc2", label="B")],
        edges=[Edge(source_id="loc1", target_id="loc2", distance=100.0, travel_type="quantum", travel_time_seconds=30)],
    )


def _graph_payload() -> dict:
    return {
        "name": "TestGraph",
        "nodes": [
            {"location_id": "loc1", "label": "A"},
            {"location_id": "loc2", "label": "B"},
        ],
        "edges": [
            {
                "source_id": "loc1",
                "target_id": "loc2",
                "distance": 100.0,
                "travel_type": "quantum",
                "travel_time_seconds": 30,
            }
        ],
    }


@pytest.fixture()
def mock_graph_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def client(mock_graph_service: AsyncMock) -> TestClient:
    with patch("src.infrastructure.config.dependencies.MongoClient"):
        from src.infrastructure.adapters.inbound.api.graph_router import init_router
        from src.infrastructure.config.settings import Settings

        settings = Settings(jwt_secret=SECRET, mongo_uri="mongodb://localhost:27017", mongo_db="test_db")

        from fastapi import FastAPI
        from hexadian_auth_common.fastapi import (
            JWTAuthDependency,
            _stub_jwt_auth,
            register_exception_handlers,
        )

        from src.infrastructure.adapters.inbound.api.graph_router import router

        app = FastAPI()
        jwt_auth = JWTAuthDependency(secret=settings.jwt_secret, algorithm=settings.jwt_algorithm)
        app.dependency_overrides[_stub_jwt_auth] = jwt_auth
        register_exception_handlers(app)

        init_router(mock_graph_service)
        app.include_router(router)

        @app.get("/health")
        def health() -> dict:
            return {"status": "ok"}

        yield TestClient(app)


class TestHealthEndpoint:
    def test_health_is_public(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestAuthenticationRequired:
    """All /graphs/ endpoints return 401 without a token."""

    def test_create_graph_requires_auth(self, client: TestClient) -> None:
        resp = client.post("/graphs/", json=_graph_payload())
        assert resp.status_code == 401

    def test_generate_graph_requires_auth(self, client: TestClient) -> None:
        resp = client.post("/graphs/generate", json={"location_ids": ["loc1"]})
        assert resp.status_code == 401

    def test_get_graph_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/graphs/abc123")
        assert resp.status_code == 401

    def test_list_graphs_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/graphs/")
        assert resp.status_code == 401

    def test_delete_graph_requires_auth(self, client: TestClient) -> None:
        resp = client.delete("/graphs/abc123")
        assert resp.status_code == 401


class TestExpiredToken:
    def test_expired_token_returns_401(self, client: TestClient) -> None:
        token = _make_token(permissions=["hhh:graphs:read"], expired=True)
        resp = client.get("/graphs/", headers=_auth_header(token))
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()


class TestInvalidToken:
    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        resp = client.get("/graphs/", headers={"Authorization": "Bearer invalid-token"})
        assert resp.status_code == 401


class TestInsufficientPermissions:
    """Endpoints return 403 when the token lacks the required permission."""

    def test_create_graph_requires_write_permission(self, client: TestClient) -> None:
        token = _make_token(permissions=["hhh:graphs:read"])
        resp = client.post("/graphs/", json=_graph_payload(), headers=_auth_header(token))
        assert resp.status_code == 403

    def test_generate_graph_requires_write_permission(self, client: TestClient) -> None:
        token = _make_token(permissions=["hhh:graphs:read"])
        resp = client.post("/graphs/generate", json={"location_ids": ["loc1"]}, headers=_auth_header(token))
        assert resp.status_code == 403

    def test_get_graph_requires_read_permission(self, client: TestClient) -> None:
        token = _make_token(permissions=["hhh:graphs:write"])
        resp = client.get("/graphs/abc123", headers=_auth_header(token))
        assert resp.status_code == 403

    def test_list_graphs_requires_read_permission(self, client: TestClient) -> None:
        token = _make_token(permissions=["hhh:graphs:write"])
        resp = client.get("/graphs/", headers=_auth_header(token))
        assert resp.status_code == 403

    def test_delete_graph_requires_delete_permission(self, client: TestClient) -> None:
        token = _make_token(permissions=["hhh:graphs:read"])
        resp = client.delete("/graphs/abc123", headers=_auth_header(token))
        assert resp.status_code == 403


class TestAuthorizedAccess:
    """Endpoints succeed with valid token and correct permissions."""

    def test_create_graph_with_write_permission(self, client: TestClient, mock_graph_service: AsyncMock) -> None:
        mock_graph_service.create.return_value = _sample_graph()
        token = _make_token(permissions=["hhh:graphs:write"])
        resp = client.post("/graphs/", json=_graph_payload(), headers=_auth_header(token))
        assert resp.status_code == 201
        assert resp.json()["name"] == "TestGraph"

    def test_get_graph_with_read_permission(self, client: TestClient, mock_graph_service: AsyncMock) -> None:
        mock_graph_service.get.return_value = _sample_graph()
        token = _make_token(permissions=["hhh:graphs:read"])
        resp = client.get("/graphs/abc123", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["name"] == "TestGraph"

    def test_list_graphs_with_read_permission(self, client: TestClient, mock_graph_service: AsyncMock) -> None:
        mock_graph_service.list_all.return_value = [_sample_graph()]
        token = _make_token(permissions=["hhh:graphs:read"])
        resp = client.get("/graphs/", headers=_auth_header(token))
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_delete_graph_with_delete_permission(self, client: TestClient, mock_graph_service: AsyncMock) -> None:
        mock_graph_service.delete.return_value = None
        token = _make_token(permissions=["hhh:graphs:delete"])
        resp = client.delete("/graphs/abc123", headers=_auth_header(token))
        assert resp.status_code == 204

    def test_generate_graph_with_write_permission(self, client: TestClient, mock_graph_service: AsyncMock) -> None:
        mock_graph_service.generate.return_value = _sample_graph()
        token = _make_token(permissions=["hhh:graphs:write"])
        resp = client.post("/graphs/generate", json={"location_ids": ["loc1", "loc2"]}, headers=_auth_header(token))
        assert resp.status_code == 201
        assert resp.json()["name"] == "TestGraph"

    def test_generate_graph_value_error_returns_400(self, client: TestClient, mock_graph_service: AsyncMock) -> None:
        mock_graph_service.generate.side_effect = ValueError("No locations found for the given IDs")
        token = _make_token(permissions=["hhh:graphs:write"])
        resp = client.post("/graphs/generate", json={"location_ids": ["loc1"]}, headers=_auth_header(token))
        assert resp.status_code == 400
        assert "No locations found" in resp.json()["detail"]


class TestCacheControlHeaders:
    """GET endpoints include Cache-Control header."""

    def test_get_graph_has_cache_control(self, client: TestClient, mock_graph_service: AsyncMock) -> None:
        mock_graph_service.get.return_value = _sample_graph()
        token = _make_token(permissions=["hhh:graphs:read"])
        resp = client.get("/graphs/abc123", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.headers["Cache-Control"] == "max-age=3600"

    def test_list_graphs_has_cache_control(self, client: TestClient, mock_graph_service: AsyncMock) -> None:
        mock_graph_service.list_all.return_value = [_sample_graph()]
        token = _make_token(permissions=["hhh:graphs:read"])
        resp = client.get("/graphs/", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.headers["Cache-Control"] == "max-age=3600"
