"""Tests for src.main create_app() wiring."""

import os
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from hexadian_auth_common.fastapi import JWTAuthDependency, _stub_jwt_auth

SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"  # gitleaks:allow


def _make_mock_mongo() -> MagicMock:
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_client.__getitem__ = MagicMock(return_value=mock_db)
    mock_collection = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)
    return mock_client


class TestCreateApp:
    def test_returns_fastapi_app(self) -> None:
        mock_client = _make_mock_mongo()
        with (
            patch.dict(os.environ, {"HHH_GRAPHS_JWT_SECRET": SECRET}),
            patch("src.infrastructure.config.dependencies.MongoClient", return_value=mock_client),
        ):
            from src.main import create_app

            app = create_app()

        assert isinstance(app, FastAPI)

    def test_overrides_stub_auth_with_jwt_dependency(self) -> None:
        mock_client = _make_mock_mongo()
        with (
            patch.dict(os.environ, {"HHH_GRAPHS_JWT_SECRET": SECRET}),
            patch("src.infrastructure.config.dependencies.MongoClient", return_value=mock_client),
        ):
            from src.main import create_app

            app = create_app()

        assert _stub_jwt_auth in app.dependency_overrides
        assert isinstance(app.dependency_overrides[_stub_jwt_auth], JWTAuthDependency)

    def test_health_endpoint_is_public(self) -> None:
        mock_client = _make_mock_mongo()
        with (
            patch.dict(os.environ, {"HHH_GRAPHS_JWT_SECRET": SECRET}),
            patch("src.infrastructure.config.dependencies.MongoClient", return_value=mock_client),
        ):
            from src.main import create_app

            app = create_app()
            client = TestClient(app)
            resp = client.get("/health")

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
