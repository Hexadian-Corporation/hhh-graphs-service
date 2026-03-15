from unittest.mock import MagicMock

import pytest

from src.application.services.graph_service_impl import GraphServiceImpl
from src.domain.exceptions.graph_exceptions import GraphNotFoundError
from src.domain.models.graph import Graph, Node


@pytest.fixture
def mock_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(mock_repo: MagicMock) -> GraphServiceImpl:
    return GraphServiceImpl(repository=mock_repo)


def _make_graph(graph_id: str = "abc123", name: str = "TestGraph") -> Graph:
    return Graph(id=graph_id, name=name, nodes=[Node(location_id="loc1", label="A")])


class TestCreate:
    def test_create_delegates_to_repository(self, service: GraphServiceImpl, mock_repo: MagicMock) -> None:
        graph = _make_graph(graph_id=None)
        saved = _make_graph(graph_id="new_id")
        mock_repo.save.return_value = saved

        result = service.create(graph)

        mock_repo.save.assert_called_once_with(graph)
        assert result.id == "new_id"

    def test_create_invalidates_cache(self, service: GraphServiceImpl, mock_repo: MagicMock) -> None:
        mock_repo.find_all.return_value = [_make_graph()]
        service.list_all()
        assert mock_repo.find_all.call_count == 1

        mock_repo.save.return_value = _make_graph()
        service.create(_make_graph())

        # Cache was invalidated, so list_all should call repo again
        mock_repo.find_all.return_value = [_make_graph(), _make_graph(graph_id="new")]
        service.list_all()
        assert mock_repo.find_all.call_count == 2


class TestGet:
    def test_get_returns_graph(self, service: GraphServiceImpl, mock_repo: MagicMock) -> None:
        graph = _make_graph()
        mock_repo.find_by_id.return_value = graph

        result = service.get("abc123")

        assert result.id == "abc123"
        mock_repo.find_by_id.assert_called_once_with("abc123")

    def test_get_raises_when_not_found(self, service: GraphServiceImpl, mock_repo: MagicMock) -> None:
        mock_repo.find_by_id.return_value = None

        with pytest.raises(GraphNotFoundError):
            service.get("missing")

    def test_get_caches_result(self, service: GraphServiceImpl, mock_repo: MagicMock) -> None:
        graph = _make_graph()
        mock_repo.find_by_id.return_value = graph

        service.get("abc123")
        service.get("abc123")

        # Repository should only be called once due to cache
        mock_repo.find_by_id.assert_called_once()

    def test_get_cache_invalidated_by_create(self, service: GraphServiceImpl, mock_repo: MagicMock) -> None:
        graph = _make_graph()
        mock_repo.find_by_id.return_value = graph

        service.get("abc123")
        assert mock_repo.find_by_id.call_count == 1

        mock_repo.save.return_value = _make_graph()
        service.create(_make_graph())

        service.get("abc123")
        assert mock_repo.find_by_id.call_count == 2

    def test_get_cache_invalidated_by_delete(self, service: GraphServiceImpl, mock_repo: MagicMock) -> None:
        graph = _make_graph()
        mock_repo.find_by_id.return_value = graph

        service.get("abc123")
        assert mock_repo.find_by_id.call_count == 1

        mock_repo.delete.return_value = True
        service.delete("abc123")

        service.get("abc123")
        assert mock_repo.find_by_id.call_count == 2


class TestListAll:
    def test_list_all_returns_graphs(self, service: GraphServiceImpl, mock_repo: MagicMock) -> None:
        graphs = [_make_graph(), _make_graph(graph_id="def456")]
        mock_repo.find_all.return_value = graphs

        result = service.list_all()

        assert len(result) == 2
        mock_repo.find_all.assert_called_once()

    def test_list_all_caches_result(self, service: GraphServiceImpl, mock_repo: MagicMock) -> None:
        mock_repo.find_all.return_value = [_make_graph()]

        service.list_all()
        service.list_all()

        mock_repo.find_all.assert_called_once()

    def test_list_all_cache_invalidated_by_delete(self, service: GraphServiceImpl, mock_repo: MagicMock) -> None:
        mock_repo.find_all.return_value = [_make_graph()]
        service.list_all()
        assert mock_repo.find_all.call_count == 1

        mock_repo.delete.return_value = True
        service.delete("abc123")

        service.list_all()
        assert mock_repo.find_all.call_count == 2


class TestDelete:
    def test_delete_delegates_to_repository(self, service: GraphServiceImpl, mock_repo: MagicMock) -> None:
        mock_repo.delete.return_value = True

        service.delete("abc123")

        mock_repo.delete.assert_called_once_with("abc123")

    def test_delete_raises_when_not_found(self, service: GraphServiceImpl, mock_repo: MagicMock) -> None:
        mock_repo.delete.return_value = False

        with pytest.raises(GraphNotFoundError):
            service.delete("missing")
