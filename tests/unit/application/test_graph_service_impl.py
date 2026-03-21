from unittest.mock import AsyncMock

import pytest

from src.application.ports.outbound.maps_client import DistanceData, LocationData
from src.application.services.graph_service_impl import GraphServiceImpl
from src.domain.exceptions.graph_exceptions import GraphNotFoundError
from src.domain.models.graph import Edge, Graph, Node


@pytest.fixture
def mock_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_maps_client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(mock_repo: AsyncMock, mock_maps_client: AsyncMock) -> GraphServiceImpl:
    return GraphServiceImpl(repository=mock_repo, maps_client=mock_maps_client)


def _make_graph(graph_id: str = "abc123", name: str = "TestGraph") -> Graph:
    return Graph(id=graph_id, name=name, nodes=[Node(location_id="loc1", label="A")])


class TestCacheTTL:
    def test_cache_ttl_is_3600(self, service: GraphServiceImpl) -> None:
        assert service._graph_cache.ttl == 3600
        assert service._list_cache.ttl == 3600


class TestCreate:
    async def test_create_delegates_to_repository(self, service: GraphServiceImpl, mock_repo: AsyncMock) -> None:
        graph = _make_graph(graph_id=None)
        saved = _make_graph(graph_id="new_id")
        mock_repo.save.return_value = saved

        result = await service.create(graph)

        mock_repo.save.assert_called_once_with(graph)
        assert result.id == "new_id"

    async def test_create_invalidates_cache(self, service: GraphServiceImpl, mock_repo: AsyncMock) -> None:
        mock_repo.find_all.return_value = [_make_graph()]
        await service.list_all()
        assert mock_repo.find_all.call_count == 1

        mock_repo.save.return_value = _make_graph()
        await service.create(_make_graph())

        # Cache was invalidated, so list_all should call repo again
        mock_repo.find_all.return_value = [_make_graph(), _make_graph(graph_id="new")]
        await service.list_all()
        assert mock_repo.find_all.call_count == 2


class TestGet:
    async def test_get_returns_graph(self, service: GraphServiceImpl, mock_repo: AsyncMock) -> None:
        graph = _make_graph()
        mock_repo.find_by_id.return_value = graph

        result = await service.get("abc123")

        assert result.id == "abc123"
        mock_repo.find_by_id.assert_called_once_with("abc123")

    async def test_get_raises_when_not_found(self, service: GraphServiceImpl, mock_repo: AsyncMock) -> None:
        mock_repo.find_by_id.return_value = None

        with pytest.raises(GraphNotFoundError):
            await service.get("missing")

    async def test_get_caches_result(self, service: GraphServiceImpl, mock_repo: AsyncMock) -> None:
        graph = _make_graph()
        mock_repo.find_by_id.return_value = graph

        await service.get("abc123")
        await service.get("abc123")

        # Repository should only be called once due to cache
        mock_repo.find_by_id.assert_called_once()

    async def test_get_cache_invalidated_by_create(self, service: GraphServiceImpl, mock_repo: AsyncMock) -> None:
        graph = _make_graph()
        mock_repo.find_by_id.return_value = graph

        await service.get("abc123")
        assert mock_repo.find_by_id.call_count == 1

        mock_repo.save.return_value = _make_graph()
        await service.create(_make_graph())

        await service.get("abc123")
        assert mock_repo.find_by_id.call_count == 2

    async def test_get_cache_invalidated_by_delete(self, service: GraphServiceImpl, mock_repo: AsyncMock) -> None:
        graph = _make_graph()
        mock_repo.find_by_id.return_value = graph

        await service.get("abc123")
        assert mock_repo.find_by_id.call_count == 1

        mock_repo.delete.return_value = True
        await service.delete("abc123")

        await service.get("abc123")
        assert mock_repo.find_by_id.call_count == 2


class TestListAll:
    async def test_list_all_returns_graphs(self, service: GraphServiceImpl, mock_repo: AsyncMock) -> None:
        graphs = [_make_graph(), _make_graph(graph_id="def456")]
        mock_repo.find_all.return_value = graphs

        result = await service.list_all()

        assert len(result) == 2
        mock_repo.find_all.assert_called_once()

    async def test_list_all_caches_result(self, service: GraphServiceImpl, mock_repo: AsyncMock) -> None:
        mock_repo.find_all.return_value = [_make_graph()]

        await service.list_all()
        await service.list_all()

        mock_repo.find_all.assert_called_once()

    async def test_list_all_cache_invalidated_by_delete(self, service: GraphServiceImpl, mock_repo: AsyncMock) -> None:
        mock_repo.find_all.return_value = [_make_graph()]
        await service.list_all()
        assert mock_repo.find_all.call_count == 1

        mock_repo.delete.return_value = True
        await service.delete("abc123")

        await service.list_all()
        assert mock_repo.find_all.call_count == 2


class TestDelete:
    async def test_delete_delegates_to_repository(self, service: GraphServiceImpl, mock_repo: AsyncMock) -> None:
        mock_repo.delete.return_value = True

        await service.delete("abc123")

        mock_repo.delete.assert_called_once_with("abc123")

    async def test_delete_raises_when_not_found(self, service: GraphServiceImpl, mock_repo: AsyncMock) -> None:
        mock_repo.delete.return_value = False

        with pytest.raises(GraphNotFoundError):
            await service.delete("missing")


class TestResolveTreeAndSystem:
    def test_single_ancestor_returns_tree_and_system(self) -> None:
        ancestors = [LocationData(id="arcl1", name="ARC-L1", location_type="station", parent_id="stanton")]
        tree, system_id = GraphServiceImpl._resolve_tree_and_system(ancestors)
        assert tree == ["arcl1"]
        assert system_id == "stanton"

    def test_deep_hierarchy_returns_all_non_system_ids(self) -> None:
        ancestors = [
            LocationData(id="area18", name="Area 18", location_type="city", parent_id="arccorp"),
            LocationData(id="arccorp", name="ArcCorp", location_type="planet", parent_id="stanton"),
        ]
        tree, system_id = GraphServiceImpl._resolve_tree_and_system(ancestors)
        assert tree == ["area18", "arccorp"]
        assert system_id == "stanton"

    def test_system_node_excluded(self) -> None:
        ancestors = [
            LocationData(id="arcl1", name="ARC-L1", location_type="station", parent_id="stanton"),
            LocationData(id="stanton", name="Stanton", location_type="system", parent_id=None),
        ]
        tree, system_id = GraphServiceImpl._resolve_tree_and_system(ancestors)
        assert tree == ["arcl1"]
        assert system_id == "stanton"

    def test_empty_ancestors_returns_none_system(self) -> None:
        tree, system_id = GraphServiceImpl._resolve_tree_and_system([])
        assert tree == []
        assert system_id is None


class TestMergeGraphs:
    def test_merge_single_graph_returns_same(self) -> None:
        g = Graph(nodes=[Node(location_id="a", label="A")], edges=[Edge(source_id="a", target_id="b", distance=1.0)])
        merged = GraphServiceImpl._merge_graphs([g])
        assert len(merged.nodes) == 1
        assert len(merged.edges) == 1

    def test_merge_deduplicates_nodes_by_location_id(self) -> None:
        g1 = Graph(nodes=[Node(location_id="a", label="A"), Node(location_id="b", label="B")])
        g2 = Graph(nodes=[Node(location_id="b", label="B"), Node(location_id="c", label="C")])
        merged = GraphServiceImpl._merge_graphs([g1, g2])
        ids = {n.location_id for n in merged.nodes}
        assert ids == {"a", "b", "c"}

    def test_merge_deduplicates_edges_by_source_target(self) -> None:
        edge = Edge(source_id="a", target_id="b", distance=10.0, travel_type="quantum")
        g1 = Graph(edges=[edge])
        g2 = Graph(edges=[Edge(source_id="a", target_id="b", distance=10.0, travel_type="quantum")])
        merged = GraphServiceImpl._merge_graphs([g1, g2])
        assert len(merged.edges) == 1

    def test_merge_empty_list_returns_empty_graph(self) -> None:
        merged = GraphServiceImpl._merge_graphs([])
        assert merged.nodes == []
        assert merged.edges == []

    def test_merge_keeps_first_edge_for_same_key(self) -> None:
        e1 = Edge(source_id="a", target_id="b", distance=10.0, travel_type="quantum")
        e2 = Edge(source_id="a", target_id="b", distance=99.0, travel_type="scm")
        g1 = Graph(edges=[e1])
        g2 = Graph(edges=[e2])
        merged = GraphServiceImpl._merge_graphs([g1, g2])
        assert merged.edges[0].distance == 10.0


class TestGenerate:
    """Tests for pairwise graph composition with two-level hash caching (#41)."""

    def _setup_same_system_pair(self, mock_maps_client: AsyncMock, mock_repo: AsyncMock) -> None:
        """Configure mocks for a basic same-system pair (loc1, loc2 in Stanton)."""
        mock_maps_client.get_location_ancestors.side_effect = [
            [LocationData(id="loc1", name="Location A", location_type="station", parent_id="stanton")],
            [LocationData(id="loc2", name="Location B", location_type="station", parent_id="stanton")],
        ]
        mock_maps_client.get_distances_for_locations.return_value = [
            DistanceData(from_location_id="loc1", to_location_id="loc2", distance=100.0, travel_type="quantum"),
        ]
        mock_repo.find_by_hash.return_value = None
        mock_repo.save.side_effect = lambda g: g

    # --- Level 1: Full-request hash ---

    async def test_level1_hit_returns_cached_graph(
        self, service: GraphServiceImpl, mock_repo: AsyncMock, mock_maps_client: AsyncMock
    ) -> None:
        existing = _make_graph(graph_id="cached_id")
        mock_repo.find_by_hash.return_value = existing

        result = await service.generate(["loc1", "loc2"])

        assert result.id == "cached_id"
        mock_repo.find_by_hash.assert_called_once()
        mock_repo.save.assert_not_called()
        mock_maps_client.get_location_ancestors.assert_not_called()

    async def test_level1_hit_does_not_invalidate_cache(self, service: GraphServiceImpl, mock_repo: AsyncMock) -> None:
        mock_repo.find_all.return_value = [_make_graph()]
        await service.list_all()
        assert mock_repo.find_all.call_count == 1

        mock_repo.find_by_hash.return_value = _make_graph(graph_id="cached")
        await service.generate(["loc1", "loc2"])

        await service.list_all()
        assert mock_repo.find_all.call_count == 1

    # --- Level 2: Pairwise hash ---

    async def test_level2_hit_reuses_cached_pair(
        self, service: GraphServiceImpl, mock_repo: AsyncMock, mock_maps_client: AsyncMock
    ) -> None:
        from src.domain.services.graph_hasher import compute_hash

        cached_pair = Graph(
            id="pair_cached",
            nodes=[Node(location_id="loc1", label="A"), Node(location_id="loc2", label="B")],
            edges=[Edge(source_id="loc1", target_id="loc2", distance=100.0, travel_type="quantum")],
        )
        # Pre-populate the in-memory L2 cache
        service._pairwise_cache[compute_hash(["loc1", "loc2"])] = cached_pair
        mock_repo.find_by_hash.return_value = None  # L1 miss
        mock_repo.save.side_effect = lambda g: g

        await service.generate(["loc1", "loc2"])

        mock_maps_client.get_location_ancestors.assert_not_called()
        assert mock_repo.save.call_count == 1  # only merged graph saved

    async def test_level2_partial_hit_only_generates_missing_pairs(
        self, service: GraphServiceImpl, mock_repo: AsyncMock, mock_maps_client: AsyncMock
    ) -> None:
        from src.domain.services.graph_hasher import compute_hash

        cached_pair_ab = Graph(
            id="pair_ab",
            nodes=[Node(location_id="loc1", label="A"), Node(location_id="loc2", label="B")],
            edges=[Edge(source_id="loc1", target_id="loc2", distance=100.0)],
        )
        # Pre-populate the in-memory L2 cache for the (loc1, loc2) pair
        service._pairwise_cache[compute_hash(["loc1", "loc2"])] = cached_pair_ab
        mock_repo.find_by_hash.return_value = None  # L1 miss only
        mock_maps_client.get_location_ancestors.side_effect = [
            [LocationData(id="loc1", name="A", location_type="station", parent_id="stanton")],
            [LocationData(id="loc3", name="C", location_type="station", parent_id="stanton")],
            [LocationData(id="loc2", name="B", location_type="station", parent_id="stanton")],
            [LocationData(id="loc3", name="C", location_type="station", parent_id="stanton")],
        ]
        mock_maps_client.get_distances_for_locations.side_effect = [
            [DistanceData(from_location_id="loc1", to_location_id="loc3", distance=200.0, travel_type="quantum")],
            [DistanceData(from_location_id="loc2", to_location_id="loc3", distance=150.0, travel_type="quantum")],
        ]
        mock_repo.save.side_effect = lambda g: g

        await service.generate(["loc1", "loc2", "loc3"])

        # Ancestors called 4 times (2 pairs × 2 locations each, skipping cached pair)
        assert mock_maps_client.get_location_ancestors.call_count == 4
        # save called 1 time: only merged (pairwise not persisted)
        assert mock_repo.save.call_count == 1

    # --- Same-system pair ---

    async def test_same_system_pair_generates_graph(
        self, service: GraphServiceImpl, mock_repo: AsyncMock, mock_maps_client: AsyncMock
    ) -> None:
        self._setup_same_system_pair(mock_maps_client, mock_repo)

        await service.generate(["loc1", "loc2"])

        assert mock_repo.find_by_hash.call_count == 1  # full hash only (L2 is in-memory)
        assert mock_maps_client.get_location_ancestors.call_count == 2
        mock_maps_client.get_wormhole_distances.assert_not_called()
        assert mock_repo.save.call_count == 1  # only merged (pairwise not persisted)

    async def test_same_system_pair_correct_nodes_and_edges(
        self, service: GraphServiceImpl, mock_repo: AsyncMock, mock_maps_client: AsyncMock
    ) -> None:
        self._setup_same_system_pair(mock_maps_client, mock_repo)

        result = await service.generate(["loc1", "loc2"])

        node_ids = {n.location_id for n in result.nodes}
        assert node_ids == {"loc1", "loc2"}
        assert len(result.edges) == 1
        assert result.edges[0].source_id == "loc1"
        assert result.edges[0].target_id == "loc2"
        assert result.edges[0].distance == 100.0
        assert result.edges[0].travel_type == "quantum"
        assert result.edges[0].travel_time_seconds == 0.0

    async def test_deep_hierarchy_includes_intermediate_nodes(
        self, service: GraphServiceImpl, mock_repo: AsyncMock, mock_maps_client: AsyncMock
    ) -> None:
        """tree(Area18) = [Area18, ArcCorp], tree(ARC-L1) = [ARC-L1] → 3 nodes."""
        mock_repo.find_by_hash.return_value = None
        mock_maps_client.get_location_ancestors.side_effect = [
            [
                LocationData(id="area18", name="Area 18", location_type="city", parent_id="arccorp"),
                LocationData(id="arccorp", name="ArcCorp", location_type="planet", parent_id="stanton"),
            ],
            [LocationData(id="arcl1", name="ARC-L1", location_type="station", parent_id="stanton")],
        ]
        mock_maps_client.get_distances_for_locations.return_value = [
            DistanceData(from_location_id="area18", to_location_id="arccorp", distance=600.0, travel_type="scm"),
            DistanceData(from_location_id="arccorp", to_location_id="arcl1", distance=3e9, travel_type="quantum"),
        ]
        mock_repo.save.side_effect = lambda g: g

        result = await service.generate(["area18", "arcl1"])

        node_ids = {n.location_id for n in result.nodes}
        assert node_ids == {"area18", "arccorp", "arcl1"}
        assert len(result.edges) == 2

    # --- Cross-system pair ---

    async def test_cross_system_pair_adds_gateway_nodes(
        self, service: GraphServiceImpl, mock_repo: AsyncMock, mock_maps_client: AsyncMock
    ) -> None:
        mock_repo.find_by_hash.return_value = None
        mock_maps_client.get_location_ancestors.side_effect = [
            [LocationData(id="loc1", name="Loc A", location_type="station", parent_id="stanton")],
            [LocationData(id="loc3", name="Loc C", location_type="station", parent_id="pyro")],
        ]
        mock_maps_client.get_wormhole_distances.return_value = [
            DistanceData(from_location_id="sp-gw", to_location_id="ps-gw", distance=300.0, travel_type="wormhole"),
        ]
        mock_maps_client.get_locations.side_effect = [
            [
                LocationData(id="sp-gw", name="Stanton-Pyro GW", location_type="gateway", parent_id="stanton"),
                LocationData(id="ps-gw", name="Pyro-Stanton GW", location_type="gateway", parent_id="pyro"),
            ],
            [
                LocationData(id="stanton", name="Stanton", location_type="system", parent_id=None),
                LocationData(id="pyro", name="Pyro", location_type="system", parent_id=None),
            ],
        ]
        mock_maps_client.get_distances_for_locations.return_value = [
            DistanceData(from_location_id="loc1", to_location_id="sp-gw", distance=50.0, travel_type="quantum"),
            DistanceData(from_location_id="sp-gw", to_location_id="ps-gw", distance=300.0, travel_type="wormhole"),
            DistanceData(from_location_id="ps-gw", to_location_id="loc3", distance=80.0, travel_type="quantum"),
        ]
        mock_repo.save.side_effect = lambda g: g

        result = await service.generate(["loc1", "loc3"])

        mock_maps_client.get_wormhole_distances.assert_called_once()
        node_ids = {n.location_id for n in result.nodes}
        assert {"loc1", "loc3", "sp-gw", "ps-gw"} <= node_ids
        assert len(result.edges) == 3

    # --- Merge & deduplication ---

    async def test_merged_graph_deduplicates_nodes(
        self, service: GraphServiceImpl, mock_repo: AsyncMock, mock_maps_client: AsyncMock
    ) -> None:
        mock_repo.find_by_hash.return_value = None

        def anc(loc_id: str, name: str) -> list[LocationData]:
            return [LocationData(id=loc_id, name=name, location_type="station", parent_id="stanton")]

        mock_maps_client.get_location_ancestors.side_effect = [
            anc("loc1", "A"),
            anc("loc2", "B"),  # pair (loc1, loc2)
            anc("loc1", "A"),
            anc("loc3", "C"),  # pair (loc1, loc3)
            anc("loc2", "B"),
            anc("loc3", "C"),  # pair (loc2, loc3)
        ]
        mock_maps_client.get_distances_for_locations.side_effect = [
            [DistanceData(from_location_id="loc1", to_location_id="loc2", distance=100.0, travel_type="quantum")],
            [DistanceData(from_location_id="loc1", to_location_id="loc3", distance=200.0, travel_type="quantum")],
            [DistanceData(from_location_id="loc2", to_location_id="loc3", distance=150.0, travel_type="quantum")],
        ]
        mock_repo.save.side_effect = lambda g: g

        result = await service.generate(["loc1", "loc2", "loc3"])

        node_ids = {n.location_id for n in result.nodes}
        assert node_ids == {"loc1", "loc2", "loc3"}
        assert len(result.edges) == 3

    async def test_edge_dedup_across_pairs(
        self, service: GraphServiceImpl, mock_repo: AsyncMock, mock_maps_client: AsyncMock
    ) -> None:
        """Edge (loc1 → parent) appears in two pairs — merged graph keeps one copy."""
        mock_repo.find_by_hash.return_value = None
        mock_maps_client.get_location_ancestors.side_effect = [
            [
                LocationData(id="loc1", name="A", location_type="city", parent_id="planet"),
                LocationData(id="planet", name="Planet", location_type="planet", parent_id="stanton"),
            ],
            [LocationData(id="loc2", name="B", location_type="station", parent_id="stanton")],
            [
                LocationData(id="loc1", name="A", location_type="city", parent_id="planet"),
                LocationData(id="planet", name="Planet", location_type="planet", parent_id="stanton"),
            ],
            [LocationData(id="loc3", name="C", location_type="station", parent_id="stanton")],
            [LocationData(id="loc2", name="B", location_type="station", parent_id="stanton")],
            [LocationData(id="loc3", name="C", location_type="station", parent_id="stanton")],
        ]
        common_edge = DistanceData(from_location_id="loc1", to_location_id="planet", distance=50.0, travel_type="scm")
        mock_maps_client.get_distances_for_locations.side_effect = [
            [common_edge, DistanceData(from_location_id="planet", to_location_id="loc2", distance=200.0)],
            [common_edge, DistanceData(from_location_id="planet", to_location_id="loc3", distance=300.0)],
            [DistanceData(from_location_id="loc2", to_location_id="loc3", distance=400.0)],
        ]
        mock_repo.save.side_effect = lambda g: g

        result = await service.generate(["loc1", "loc2", "loc3"])

        edge_keys = [(e.source_id, e.target_id) for e in result.edges]
        assert len(edge_keys) == len(set(edge_keys))

    # --- Naming & hash ---

    async def test_merged_graph_named_correctly(
        self, service: GraphServiceImpl, mock_repo: AsyncMock, mock_maps_client: AsyncMock
    ) -> None:
        self._setup_same_system_pair(mock_maps_client, mock_repo)
        result = await service.generate(["loc1", "loc2"])
        assert result.name == "distance-graph-2n-1e"

    async def test_merged_graph_has_full_request_hash(
        self, service: GraphServiceImpl, mock_repo: AsyncMock, mock_maps_client: AsyncMock
    ) -> None:
        self._setup_same_system_pair(mock_maps_client, mock_repo)
        result = await service.generate(["loc1", "loc2"])

        from src.domain.services.graph_hasher import compute_hash

        assert result.hash == compute_hash(["loc1", "loc2"])

    async def test_merged_graph_persisted_with_full_hash(
        self, service: GraphServiceImpl, mock_repo: AsyncMock, mock_maps_client: AsyncMock
    ) -> None:
        self._setup_same_system_pair(mock_maps_client, mock_repo)
        saved_graphs: list[Graph] = []
        mock_repo.save.side_effect = lambda g: (saved_graphs.append(g), g)[1]

        await service.generate(["loc1", "loc2"])

        from src.domain.services.graph_hasher import compute_hash

        full_hash = compute_hash(["loc1", "loc2"])
        assert len(saved_graphs) == 1  # only merged graph persisted
        assert saved_graphs[0].hash == full_hash

    # --- Error handling ---

    async def test_generate_single_id_creates_single_node_graph(
        self, service: GraphServiceImpl, mock_repo: AsyncMock, mock_maps_client: AsyncMock
    ) -> None:
        mock_repo.find_by_hash.return_value = None
        mock_maps_client.get_locations.return_value = [
            LocationData(id="loc1", name="Single", location_type="station", parent_id="stanton")
        ]
        mock_repo.save.side_effect = lambda g: g

        result = await service.generate(["loc1"])

        assert len(result.nodes) == 1
        assert result.nodes[0].location_id == "loc1"
        assert result.edges == []

    async def test_generate_raises_with_empty_list(self, service: GraphServiceImpl) -> None:
        with pytest.raises(ValueError):
            await service.generate([])

    # --- Cache invalidation ---

    async def test_generate_invalidates_cache_on_new_graph(
        self, service: GraphServiceImpl, mock_repo: AsyncMock, mock_maps_client: AsyncMock
    ) -> None:
        mock_repo.find_all.return_value = [_make_graph()]
        await service.list_all()
        assert mock_repo.find_all.call_count == 1

        self._setup_same_system_pair(mock_maps_client, mock_repo)
        await service.generate(["loc1", "loc2"])

        mock_repo.find_all.return_value = [_make_graph(), _make_graph(graph_id="new")]
        await service.list_all()
        assert mock_repo.find_all.call_count == 2
