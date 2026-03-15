from unittest.mock import MagicMock, patch

from src.infrastructure.config.dependencies import AppModule
from src.infrastructure.config.settings import Settings


class TestAppModuleIndexes:
    def test_indexes_created_on_configure(self) -> None:
        settings = Settings(mongo_uri="mongodb://localhost:27017", mongo_db="test_db")

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
        assert mock_collection.create_index.call_count == 2
