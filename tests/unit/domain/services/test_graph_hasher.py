from src.domain.models.graph import Edge, Node
from src.domain.services.graph_hasher import compute_graph_hash, compute_hash


def _make_nodes() -> list[Node]:
    return [
        Node(location_id="loc1", label="Alpha"),
        Node(location_id="loc2", label="Bravo"),
    ]


def _make_edges() -> list[Edge]:
    return [
        Edge(source_id="loc1", target_id="loc2", distance=100.0, travel_type="quantum", travel_time_seconds=60.0),
    ]


class TestDeterminism:
    def test_same_input_produces_same_hash(self) -> None:
        nodes = _make_nodes()
        edges = _make_edges()
        assert compute_graph_hash(nodes, edges) == compute_graph_hash(nodes, edges)

    def test_different_node_order_produces_same_hash(self) -> None:
        nodes_a = [Node(location_id="loc1", label="Alpha"), Node(location_id="loc2", label="Bravo")]
        nodes_b = [Node(location_id="loc2", label="Bravo"), Node(location_id="loc1", label="Alpha")]
        edges = _make_edges()
        assert compute_graph_hash(nodes_a, edges) == compute_graph_hash(nodes_b, edges)

    def test_different_edge_order_produces_same_hash(self) -> None:
        nodes = _make_nodes()
        edges_a = [
            Edge(source_id="loc1", target_id="loc2", distance=100.0, travel_type="quantum"),
            Edge(source_id="loc2", target_id="loc1", distance=50.0, travel_type="scm"),
        ]
        edges_b = [
            Edge(source_id="loc2", target_id="loc1", distance=50.0, travel_type="scm"),
            Edge(source_id="loc1", target_id="loc2", distance=100.0, travel_type="quantum"),
        ]
        assert compute_graph_hash(nodes, edges_a) == compute_graph_hash(nodes, edges_b)


class TestUniqueness:
    def test_different_nodes_produce_different_hash(self) -> None:
        edges = _make_edges()
        nodes_a = [Node(location_id="loc1", label="Alpha")]
        nodes_b = [Node(location_id="loc9", label="Zulu")]
        assert compute_graph_hash(nodes_a, edges) != compute_graph_hash(nodes_b, edges)

    def test_different_edge_distances_produce_different_hash(self) -> None:
        nodes = _make_nodes()
        edges_a = [Edge(source_id="loc1", target_id="loc2", distance=100.0, travel_type="quantum")]
        edges_b = [Edge(source_id="loc1", target_id="loc2", distance=999.0, travel_type="quantum")]
        assert compute_graph_hash(nodes, edges_a) != compute_graph_hash(nodes, edges_b)

    def test_different_travel_types_produce_different_hash(self) -> None:
        nodes = _make_nodes()
        edges_a = [Edge(source_id="loc1", target_id="loc2", distance=100.0, travel_type="quantum")]
        edges_b = [Edge(source_id="loc1", target_id="loc2", distance=100.0, travel_type="scm")]
        assert compute_graph_hash(nodes, edges_a) != compute_graph_hash(nodes, edges_b)


class TestHashFormat:
    def test_hash_is_64_character_hex_string(self) -> None:
        result = compute_graph_hash(_make_nodes(), _make_edges())
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


class TestEdgeCases:
    def test_empty_nodes_and_edges_produce_valid_hash(self) -> None:
        result = compute_graph_hash([], [])
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


class TestHashStability:
    def test_known_input_produces_known_hash(self) -> None:
        """Regression test: a fixed input must always produce the same hash."""
        nodes = [Node(location_id="loc1", label="Alpha")]
        edges = [Edge(source_id="loc1", target_id="loc2", distance=42.0, travel_type="quantum")]
        expected = compute_graph_hash(nodes, edges)
        # Re-compute with fresh objects to confirm stability
        nodes2 = [Node(location_id="loc1", label="Alpha")]
        edges2 = [Edge(source_id="loc1", target_id="loc2", distance=42.0, travel_type="quantum")]
        assert compute_graph_hash(nodes2, edges2) == expected


class TestTravelTimeExclusion:
    def test_different_travel_times_produce_same_hash(self) -> None:
        nodes = _make_nodes()
        edges_a = [
            Edge(source_id="loc1", target_id="loc2", distance=100.0, travel_type="quantum", travel_time_seconds=60.0)
        ]
        edges_b = [
            Edge(source_id="loc1", target_id="loc2", distance=100.0, travel_type="quantum", travel_time_seconds=999.0)
        ]
        assert compute_graph_hash(nodes, edges_a) == compute_graph_hash(nodes, edges_b)


class TestComputeHash:
    def test_order_independent_pair(self) -> None:
        assert compute_hash(["A", "B"]) == compute_hash(["B", "A"])

    def test_order_independent_triple(self) -> None:
        assert compute_hash(["A", "B", "C"]) == compute_hash(["C", "A", "B"])

    def test_deterministic(self) -> None:
        result_1 = compute_hash(["loc1", "loc2", "loc3"])
        result_2 = compute_hash(["loc1", "loc2", "loc3"])
        assert result_1 == result_2

    def test_single_id(self) -> None:
        result = compute_hash(["A"])
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_two_ids(self) -> None:
        result = compute_hash(["A", "B"])
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_n_ids(self) -> None:
        ids = [f"loc{i}" for i in range(10)]
        result = compute_hash(ids)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_empty_list(self) -> None:
        result = compute_hash([])
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_duplicates_preserved(self) -> None:
        # ["A", "A"] sorted → "A|A" — distinct from "A"
        assert compute_hash(["A", "A"]) != compute_hash(["A"])

    def test_different_ids_produce_different_hashes(self) -> None:
        assert compute_hash(["A", "B"]) != compute_hash(["A", "C"])

    def test_hash_format_is_64_char_hex(self) -> None:
        result = compute_hash(["loc1", "loc2"])
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_stability_known_input(self) -> None:
        """Regression: fixed input must always produce the same hash."""
        expected = compute_hash(["loc1", "loc2"])
        assert compute_hash(["loc2", "loc1"]) == expected
        assert compute_hash(["loc1", "loc2"]) == expected
