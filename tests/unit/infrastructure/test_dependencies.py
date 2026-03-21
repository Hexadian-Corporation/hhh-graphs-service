from unittest.mock import MagicMock, patch

from src.infrastructure.config.dependencies import AppModule
from src.infrastructure.config.settings import Settings


class TestAppModuleIndexes:
    def test_indexes_created_on_configure(self) -> None:
        settings = Settings(jwt_secret="test-secret", mongo_uri="mongodb://localhost:27017", mongo_db="test_db")

        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)

        with patch("src.infrastructure.config.dependencies.MongoClient", return_value=mock_client):
            module = AppModule(settings)
            module.configure()

        mock_collection.create_index.assert_any_call([("name", 1)])
        mock_collection.create_index.assert_any_call([("nodes.location_id", 1)])
        mock_collection.create_index.assert_any_call("hash", unique=True, sparse=True)
        assert mock_collection.create_index.call_count == 3

    def test_maps_client_bound_with_configured_url(self) -> None:
        settings = Settings(
            jwt_secret="test-secret",
            mongo_uri="mongodb://localhost:27017",
            mongo_db="test_db",
            maps_service_url="http://maps:8003",
        )

        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)

        with (
            patch("src.infrastructure.config.dependencies.MongoClient", return_value=mock_client),
            patch("src.infrastructure.config.dependencies.HttpMapsClient") as mock_http_maps_client,
        ):
            module = AppModule(settings)
            module.configure()

        call_kwargs = mock_http_maps_client.call_args
        assert call_kwargs.kwargs["base_url"] == "http://maps:8003"
        assert "client" in call_kwargs.kwargs
