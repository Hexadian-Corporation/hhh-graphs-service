from unittest.mock import MagicMock

import pytest

from src.application.ports.outbound.maps_client import DistanceData, LocationData
from src.application.services.graph_service_impl import GraphServiceImpl
from src.domain.exceptions.graph_exceptions import GraphNotFoundError
from src.domain.models.graph import Graph, Node


@pytest.fixture
def mock_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_maps_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(mock_repo: MagicMock, mock_maps_client: MagicMock) -> GraphServiceImpl:
    return GraphServiceImpl(repository=mock_repo, maps_client=mock_maps_client)


def _make_graph(graph_id: str = "abc123", name: str = "TestGraph") -> Graph:
    return Graph(id=graph_id, name=name, nodes=[Node(location_id="loc1", label="A")])


class TestCacheTTL:
    def test_cache_ttl_is_3600(self, service: GraphServiceImpl) -> None:
        assert service._graph_cache.ttl == 3600
        assert service._list_cache.ttl == 3600


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


class TestGenerate:
    @pytest.fixture
    def locations(self) -> list[LocationData]:
        return [
            LocationData(id="loc1", name="Location A", location_type="station"),
            LocationData(id="loc2", name="Location B", location_type="station"),
        ]

    @pytest.fixture
    def distances(self) -> list[DistanceData]:
        return [
            DistanceData(
                from_location_id="loc1",
                to_location_id="loc2",
                distance=100.0,
                travel_type="quantum",
            ),
        ]

    def test_generate_creates_new_graph(
        self,
        service: GraphServiceImpl,
        mock_repo: MagicMock,
        mock_maps_client: MagicMock,
        locations: list[LocationData],
        distances: list[DistanceData],
    ) -> None:
        mock_maps_client.get_locations.return_value = locations
        mock_maps_client.get_distances_for_locations.return_value = distances
        mock_repo.find_by_hash.return_value = None
        saved_graph = _make_graph(graph_id="new_id", name="distance-graph-2n-1e")
        mock_repo.save.return_value = saved_graph

        result = service.generate(["loc1", "loc2"])

        mock_maps_client.get_locations.assert_called_once_with(["loc1", "loc2"])
        mock_maps_client.get_distances_for_locations.assert_called_once_with(["loc1", "loc2"])
        mock_repo.find_by_hash.assert_called_once()
        mock_repo.save.assert_called_once()
        assert result.id == "new_id"

    def test_generate_returns_existing_graph_when_hash_matches(
        self,
        service: GraphServiceImpl,
        mock_repo: MagicMock,
        mock_maps_client: MagicMock,
        locations: list[LocationData],
        distances: list[DistanceData],
    ) -> None:
        mock_maps_client.get_locations.return_value = locations
        mock_maps_client.get_distances_for_locations.return_value = distances
        existing_graph = _make_graph(graph_id="existing_id")
        mock_repo.find_by_hash.return_value = existing_graph

        result = service.generate(["loc1", "loc2"])

        assert result.id == "existing_id"
        mock_repo.save.assert_not_called()

    def test_generate_raises_when_no_locations_found(
        self,
        service: GraphServiceImpl,
        mock_maps_client: MagicMock,
    ) -> None:
        mock_maps_client.get_locations.return_value = []

        with pytest.raises(ValueError, match="No locations found"):
            service.generate(["loc1", "loc2"])

    def test_generate_builds_correct_nodes_and_edges(
        self,
        service: GraphServiceImpl,
        mock_repo: MagicMock,
        mock_maps_client: MagicMock,
        locations: list[LocationData],
        distances: list[DistanceData],
    ) -> None:
        mock_maps_client.get_locations.return_value = locations
        mock_maps_client.get_distances_for_locations.return_value = distances
        mock_repo.find_by_hash.return_value = None
        mock_repo.save.side_effect = lambda g: g

        result = service.generate(["loc1", "loc2"])

        assert len(result.nodes) == 2
        assert result.nodes[0].location_id == "loc1"
        assert result.nodes[0].label == "Location A"
        assert result.nodes[1].location_id == "loc2"
        assert result.nodes[1].label == "Location B"
        assert len(result.edges) == 1
        assert result.edges[0].source_id == "loc1"
        assert result.edges[0].target_id == "loc2"
        assert result.edges[0].distance == 100.0
        assert result.edges[0].travel_type == "quantum"
        assert result.edges[0].travel_time_seconds == 0.0

    def test_generate_sets_auto_name(
        self,
        service: GraphServiceImpl,
        mock_repo: MagicMock,
        mock_maps_client: MagicMock,
        locations: list[LocationData],
        distances: list[DistanceData],
    ) -> None:
        mock_maps_client.get_locations.return_value = locations
        mock_maps_client.get_distances_for_locations.return_value = distances
        mock_repo.find_by_hash.return_value = None
        mock_repo.save.side_effect = lambda g: g

        result = service.generate(["loc1", "loc2"])

        assert result.name == "distance-graph-2n-1e"

    def test_generate_invalidates_cache_on_new_graph(
        self,
        service: GraphServiceImpl,
        mock_repo: MagicMock,
        mock_maps_client: MagicMock,
        locations: list[LocationData],
        distances: list[DistanceData],
    ) -> None:
        # Pre-populate list cache
        mock_repo.find_all.return_value = [_make_graph()]
        service.list_all()
        assert mock_repo.find_all.call_count == 1

        # Generate a new graph (no hash match)
        mock_maps_client.get_locations.return_value = locations
        mock_maps_client.get_distances_for_locations.return_value = distances
        mock_repo.find_by_hash.return_value = None
        mock_repo.save.side_effect = lambda g: g

        service.generate(["loc1", "loc2"])

        # Cache was invalidated, so list_all should call repo again
        mock_repo.find_all.return_value = [_make_graph(), _make_graph(graph_id="new")]
        service.list_all()
        assert mock_repo.find_all.call_count == 2

    def test_generate_does_not_invalidate_cache_on_existing_graph(
        self,
        service: GraphServiceImpl,
        mock_repo: MagicMock,
        mock_maps_client: MagicMock,
        locations: list[LocationData],
        distances: list[DistanceData],
    ) -> None:
        # Pre-populate list cache
        mock_repo.find_all.return_value = [_make_graph()]
        service.list_all()
        assert mock_repo.find_all.call_count == 1

        # Generate returns existing graph (hash match)
        mock_maps_client.get_locations.return_value = locations
        mock_maps_client.get_distances_for_locations.return_value = distances
        mock_repo.find_by_hash.return_value = _make_graph(graph_id="existing_id")

        service.generate(["loc1", "loc2"])

        # Cache NOT invalidated, so list_all should still use cache
        service.list_all()
        assert mock_repo.find_all.call_count == 1
