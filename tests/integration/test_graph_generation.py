"""Integration tests for graph generation and hash deduplication (real MongoDB, mocked Maps client)."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from pymongo.collection import Collection

from src.application.ports.outbound.maps_client import DistanceData, LocationData
from tests.auth_helpers import make_auth_header

_WRITE = make_auth_header("hhh:graphs:write")
_READ = make_auth_header("hhh:graphs:read")

# ---------------------------------------------------------------------------
# Fake location / distance data returned by the mocked Maps client
# ---------------------------------------------------------------------------
_LOC_A = LocationData(id="loc-a", name="Lorville", location_type="city", parent_id="stanton")
_LOC_B = LocationData(id="loc-b", name="Area18", location_type="city", parent_id="stanton")
_LOC_C = LocationData(id="loc-c", name="New Babbage", location_type="city", parent_id="stanton")

_DIST_AB = DistanceData(from_location_id="loc-a", to_location_id="loc-b", distance=42.5, travel_type="quantum")
_DIST_BA = DistanceData(from_location_id="loc-b", to_location_id="loc-a", distance=42.5, travel_type="quantum")
_DIST_AC = DistanceData(from_location_id="loc-a", to_location_id="loc-c", distance=30.0, travel_type="quantum")
_DIST_BC = DistanceData(from_location_id="loc-b", to_location_id="loc-c", distance=25.0, travel_type="quantum")


def _configure_mock(
    mock: MagicMock,
    locations: list[LocationData],
    distances: list[DistanceData],
) -> None:
    """Set up the MapsClient mock to return the given locations and distances."""
    loc_dict = {loc.id: loc for loc in locations}
    mock.get_location_ancestors.side_effect = lambda loc_id: [loc_dict[loc_id]] if loc_id in loc_dict else []
    mock.get_distances_for_locations.return_value = distances
    mock.get_locations.return_value = locations


# ---------------------------------------------------------------------------
# TestGraphGenerate
# ---------------------------------------------------------------------------
class TestGraphGenerate:
    """POST /graphs/generate with valid location_ids → graph with nodes and edges."""

    def test_creates_graph_with_nodes_and_edges(self, client: TestClient, maps_mock: MagicMock) -> None:
        _configure_mock(maps_mock, [_LOC_A, _LOC_B], [_DIST_AB, _DIST_BA])

        resp = client.post(
            "/graphs/generate",
            json={"location_ids": ["loc-a", "loc-b"]},
            headers=_WRITE,
        )

        assert resp.status_code == 201
        body = resp.json()
        assert len(body["nodes"]) == 2
        assert len(body["edges"]) == 2
        assert body["_id"] is not None

    def test_maps_client_called_for_locations_and_distances(self, client: TestClient, maps_mock: MagicMock) -> None:
        _configure_mock(maps_mock, [_LOC_A, _LOC_B], [_DIST_AB])

        client.post(
            "/graphs/generate",
            json={"location_ids": ["loc-a", "loc-b"]},
            headers=_WRITE,
        )

        assert maps_mock.get_location_ancestors.call_count == 2
        maps_mock.get_distances_for_locations.assert_called_once_with(["loc-a", "loc-b"])

    def test_edges_have_source_target_and_distance(self, client: TestClient, maps_mock: MagicMock) -> None:
        _configure_mock(maps_mock, [_LOC_A, _LOC_B], [_DIST_AB])

        resp = client.post(
            "/graphs/generate",
            json={"location_ids": ["loc-a", "loc-b"]},
            headers=_WRITE,
        )

        edge = resp.json()["edges"][0]
        assert edge["source_id"] == "loc-a"
        assert edge["target_id"] == "loc-b"
        assert edge["distance"] == 42.5

    def test_nodes_correspond_to_location_ids(self, client: TestClient, maps_mock: MagicMock) -> None:
        _configure_mock(maps_mock, [_LOC_A, _LOC_B], [_DIST_AB])

        resp = client.post(
            "/graphs/generate",
            json={"location_ids": ["loc-a", "loc-b"]},
            headers=_WRITE,
        )

        node_ids = {n["location_id"] for n in resp.json()["nodes"]}
        assert node_ids == {"loc-a", "loc-b"}

    def test_generates_deterministic_hash(self, client: TestClient, maps_mock: MagicMock) -> None:
        _configure_mock(maps_mock, [_LOC_A, _LOC_B], [_DIST_AB])

        resp = client.post(
            "/graphs/generate",
            json={"location_ids": ["loc-a", "loc-b"]},
            headers=_WRITE,
        )

        body = resp.json()
        assert body["hash"] != ""
        assert len(body["hash"]) == 64  # SHA-256 hex digest

    def test_no_real_http_calls_to_maps_service(self, client: TestClient, maps_mock: MagicMock) -> None:
        """The mock prevents any real HTTP call to maps-service."""
        _configure_mock(maps_mock, [_LOC_A, _LOC_B], [_DIST_AB])

        resp = client.post(
            "/graphs/generate",
            json={"location_ids": ["loc-a", "loc-b"]},
            headers=_WRITE,
        )

        assert resp.status_code == 201
        # get_location_ancestors called twice (once per location), get_distances_for_locations once
        assert maps_mock.get_location_ancestors.call_count == 2
        assert maps_mock.get_distances_for_locations.call_count == 1


# ---------------------------------------------------------------------------
# TestGraphHashDeduplication
# ---------------------------------------------------------------------------
class TestGraphHashDeduplication:
    """Hash-based deduplication: same inputs → same graph, different → new graph."""

    def test_same_location_ids_return_same_graph(self, client: TestClient, maps_mock: MagicMock) -> None:
        _configure_mock(maps_mock, [_LOC_A, _LOC_B], [_DIST_AB])
        payload = {"location_ids": ["loc-a", "loc-b"]}

        resp1 = client.post("/graphs/generate", json=payload, headers=_WRITE)
        resp2 = client.post("/graphs/generate", json=payload, headers=_WRITE)

        assert resp1.json()["_id"] == resp2.json()["_id"]
        assert resp1.json()["hash"] == resp2.json()["hash"]

    def test_different_location_ids_create_different_graph(self, client: TestClient, maps_mock: MagicMock) -> None:
        # First generation: A + B
        _configure_mock(maps_mock, [_LOC_A, _LOC_B], [_DIST_AB])
        resp1 = client.post(
            "/graphs/generate",
            json={"location_ids": ["loc-a", "loc-b"]},
            headers=_WRITE,
        )

        # Second generation: A + C (different mock data)
        _configure_mock(maps_mock, [_LOC_A, _LOC_C], [_DIST_AC])
        resp2 = client.post(
            "/graphs/generate",
            json={"location_ids": ["loc-a", "loc-c"]},
            headers=_WRITE,
        )

        assert resp1.json()["_id"] != resp2.json()["_id"]
        assert resp1.json()["hash"] != resp2.json()["hash"]

    def test_only_one_graph_in_db_after_two_identical_generations(
        self, client: TestClient, maps_mock: MagicMock, collection: Collection
    ) -> None:
        _configure_mock(maps_mock, [_LOC_A, _LOC_B], [_DIST_AB])
        payload = {"location_ids": ["loc-a", "loc-b"]}

        client.post("/graphs/generate", json=payload, headers=_WRITE)
        client.post("/graphs/generate", json=payload, headers=_WRITE)

        assert collection.count_documents({}) == 1

    def test_two_graphs_in_db_after_different_generations(
        self, client: TestClient, maps_mock: MagicMock, collection: Collection
    ) -> None:
        # First generation
        _configure_mock(maps_mock, [_LOC_A, _LOC_B], [_DIST_AB])
        client.post(
            "/graphs/generate",
            json={"location_ids": ["loc-a", "loc-b"]},
            headers=_WRITE,
        )

        # Second generation with different data
        _configure_mock(maps_mock, [_LOC_A, _LOC_C], [_DIST_AC])
        client.post(
            "/graphs/generate",
            json={"location_ids": ["loc-a", "loc-c"]},
            headers=_WRITE,
        )

        assert collection.count_documents({}) == 2


# ---------------------------------------------------------------------------
# TestGraphGenerateEdgeCases
# ---------------------------------------------------------------------------
class TestGraphGenerateEdgeCases:
    """Edge cases for POST /graphs/generate."""

    def test_empty_location_ids_returns_400(self, client: TestClient, maps_mock: MagicMock) -> None:
        maps_mock.get_locations.return_value = []

        resp = client.post(
            "/graphs/generate",
            json={"location_ids": []},
            headers=_WRITE,
        )

        assert resp.status_code == 400

    def test_single_location_id_creates_graph_without_edges(self, client: TestClient, maps_mock: MagicMock) -> None:
        _configure_mock(maps_mock, [_LOC_A], [])

        resp = client.post(
            "/graphs/generate",
            json={"location_ids": ["loc-a"]},
            headers=_WRITE,
        )

        assert resp.status_code == 201
        body = resp.json()
        assert len(body["nodes"]) == 1
        assert body["nodes"][0]["location_id"] == "loc-a"
        assert body["edges"] == []

    def test_two_locations_with_no_distances(self, client: TestClient, maps_mock: MagicMock) -> None:
        _configure_mock(maps_mock, [_LOC_A, _LOC_B], [])

        resp = client.post(
            "/graphs/generate",
            json={"location_ids": ["loc-a", "loc-b"]},
            headers=_WRITE,
        )

        assert resp.status_code == 201
        body = resp.json()
        assert len(body["nodes"]) == 2
        assert body["edges"] == []
