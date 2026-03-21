from unittest.mock import MagicMock, patch

import pytest

from src.application.ports.outbound.maps_client import DistanceData, LocationData
from src.domain.exceptions.graph_exceptions import LocationNotFoundError, ServiceUnavailableError
from src.infrastructure.adapters.outbound.http.maps_client_impl import HttpMapsClient


def _make_response(status_code: int, json_data: object) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


class TestHttpMapsClientGetLocations:
    def test_returns_location_data_on_200(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        payload = {"_id": "loc1", "name": "Stanton", "location_type": "system", "parent_id": None}
        with patch("httpx.get", return_value=_make_response(200, payload)) as mock_get:
            result = client.get_locations(["loc1"])

        mock_get.assert_called_once_with("http://maps-service/locations/loc1", timeout=10.0)
        assert result == [LocationData(id="loc1", name="Stanton", location_type="system", parent_id=None)]

    def test_skips_non_200_responses(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        with patch("httpx.get", return_value=_make_response(404, {})):
            result = client.get_locations(["missing"])

        assert result == []

    def test_returns_multiple_locations(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        payloads = [
            {"_id": "loc1", "name": "Stanton", "location_type": "system", "parent_id": None},
            {"_id": "loc2", "name": "Hurston", "location_type": "planet", "parent_id": "loc1"},
        ]

        def _side_effect(url: str, timeout: float) -> MagicMock:
            loc_id = url.split("/")[-1]
            payload = next(p for p in payloads if p["_id"] == loc_id)
            return _make_response(200, payload)

        with patch("httpx.get", side_effect=_side_effect):
            result = client.get_locations(["loc1", "loc2"])

        assert len(result) == 2
        assert result[0].id == "loc1"
        assert result[1].id == "loc2"
        assert result[1].parent_id == "loc1"

    def test_trims_trailing_slash_from_base_url(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service/")
        with patch("httpx.get", return_value=_make_response(404, {})) as mock_get:
            client.get_locations(["loc1"])

        mock_get.assert_called_once_with("http://maps-service/locations/loc1", timeout=10.0)

    def test_uses_custom_timeout(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service", timeout=5.0)
        with patch("httpx.get", return_value=_make_response(404, {})) as mock_get:
            client.get_locations(["loc1"])

        mock_get.assert_called_once_with("http://maps-service/locations/loc1", timeout=5.0)

    def test_optional_fields_default_when_absent(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        payload = {"_id": "loc1", "name": "Stanton"}
        with patch("httpx.get", return_value=_make_response(200, payload)):
            result = client.get_locations(["loc1"])

        assert result[0].location_type == ""
        assert result[0].parent_id is None

    def test_empty_list_makes_no_requests(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        with patch("httpx.get") as mock_get:
            result = client.get_locations([])

        mock_get.assert_not_called()
        assert result == []


class TestHttpMapsClientGetDistancesForLocations:
    def test_returns_distance_data_on_200(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        distances_payload = [
            {"from_location_id": "loc1", "to_location_id": "loc2", "distance": 500.0, "travel_type": "quantum"}
        ]
        with patch("httpx.get", return_value=_make_response(200, distances_payload)):
            result = client.get_distances_for_locations(["loc1", "loc2"])

        assert len(result) == 1
        assert result[0] == DistanceData(
            from_location_id="loc1", to_location_id="loc2", distance=500.0, travel_type="quantum"
        )

    def test_deduplicates_symmetric_pairs(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        # loc1 query returns A→B, loc2 query returns B→A (same edge)
        loc1_distances = [
            {"from_location_id": "loc1", "to_location_id": "loc2", "distance": 500.0, "travel_type": "quantum"}
        ]
        loc2_distances = [
            {"from_location_id": "loc2", "to_location_id": "loc1", "distance": 500.0, "travel_type": "quantum"}
        ]

        def _side_effect(url: str, timeout: float) -> MagicMock:
            if url.endswith("loc1/distances"):
                return _make_response(200, loc1_distances)
            return _make_response(200, loc2_distances)

        with patch("httpx.get", side_effect=_side_effect):
            result = client.get_distances_for_locations(["loc1", "loc2"])

        assert len(result) == 1

    def test_filters_out_edges_with_external_endpoints(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        # loc1/distances returns an edge to loc3 which is NOT in the requested set
        distances_payload = [
            {"from_location_id": "loc1", "to_location_id": "loc3", "distance": 999.0, "travel_type": "quantum"}
        ]
        with patch("httpx.get", return_value=_make_response(200, distances_payload)):
            result = client.get_distances_for_locations(["loc1", "loc2"])

        assert result == []

    def test_skips_non_200_responses(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        with patch("httpx.get", return_value=_make_response(500, {})):
            result = client.get_distances_for_locations(["loc1"])

        assert result == []

    def test_optional_travel_type_defaults_to_empty_string(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        distances_payload = [{"from_location_id": "loc1", "to_location_id": "loc2", "distance": 100.0}]
        with patch("httpx.get", return_value=_make_response(200, distances_payload)):
            result = client.get_distances_for_locations(["loc1", "loc2"])

        assert result[0].travel_type == ""

    def test_empty_list_makes_no_requests(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        with patch("httpx.get") as mock_get:
            result = client.get_distances_for_locations([])

        mock_get.assert_not_called()
        assert result == []

    def test_multiple_distinct_edges_returned(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        loc1_distances = [
            {"from_location_id": "loc1", "to_location_id": "loc2", "distance": 100.0, "travel_type": "quantum"},
            {"from_location_id": "loc1", "to_location_id": "loc3", "distance": 200.0, "travel_type": "scm"},
        ]
        loc2_distances: list = []
        loc3_distances: list = []

        def _side_effect(url: str, timeout: float) -> MagicMock:
            if url.endswith("loc1/distances"):
                return _make_response(200, loc1_distances)
            if url.endswith("loc2/distances"):
                return _make_response(200, loc2_distances)
            return _make_response(200, loc3_distances)

        with patch("httpx.get", side_effect=_side_effect):
            result = client.get_distances_for_locations(["loc1", "loc2", "loc3"])

        assert len(result) == 2
        pairs = {(d.from_location_id, d.to_location_id) for d in result}
        assert ("loc1", "loc2") in pairs
        assert ("loc1", "loc3") in pairs


class TestHttpMapsClientGetLocationAncestors:
    def test_returns_ancestor_chain_on_200(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        payload = [
            {"_id": "area18-uuid", "name": "Area 18", "location_type": "city", "parent_id": "arccorp-uuid"},
            {"_id": "arccorp-uuid", "name": "ArcCorp", "location_type": "planet", "parent_id": "stanton-uuid"},
        ]
        with patch("httpx.get", return_value=_make_response(200, payload)) as mock_get:
            result = client.get_location_ancestors("area18-uuid")

        mock_get.assert_called_once_with("http://maps-service/locations/area18-uuid/ancestors", timeout=10.0)
        assert result == [
            LocationData(id="area18-uuid", name="Area 18", location_type="city", parent_id="arccorp-uuid"),
            LocationData(id="arccorp-uuid", name="ArcCorp", location_type="planet", parent_id="stanton-uuid"),
        ]

    def test_returns_single_ancestor_for_star_child(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        payload = [
            {"_id": "arcl1-uuid", "name": "ARC-L1", "location_type": "lagrange_point", "parent_id": "stanton-uuid"}
        ]
        with patch("httpx.get", return_value=_make_response(200, payload)):
            result = client.get_location_ancestors("arcl1-uuid")

        assert len(result) == 1
        assert result[0].id == "arcl1-uuid"

    def test_raises_location_not_found_on_404(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        with (
            patch("httpx.get", return_value=_make_response(404, {"detail": "Not found"})),
            pytest.raises(LocationNotFoundError) as exc_info,
        ):
            client.get_location_ancestors("nonexistent")

        assert exc_info.value.location_id == "nonexistent"

    def test_raises_service_unavailable_on_5xx(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        with (
            patch("httpx.get", return_value=_make_response(503, {})),
            pytest.raises(ServiceUnavailableError) as exc_info,
        ):
            client.get_location_ancestors("area18-uuid")

        assert exc_info.value.service_name == "maps-service"
        assert exc_info.value.status_code == 503

    def test_returns_empty_list_when_no_ancestors(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        with patch("httpx.get", return_value=_make_response(200, [])):
            result = client.get_location_ancestors("star-uuid")

        assert result == []

    def test_optional_fields_default_when_absent(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        payload = [{"_id": "loc1", "name": "SomeLocation"}]
        with patch("httpx.get", return_value=_make_response(200, payload)):
            result = client.get_location_ancestors("loc1")

        assert result[0].location_type == ""
        assert result[0].parent_id is None


class TestHttpMapsClientGetWormholeDistances:
    def test_returns_wormhole_distances_on_200(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        payload = [
            {
                "from_location_id": "stanton-pyro-gw",
                "to_location_id": "pyro-stanton-gw",
                "distance": 300.0,
                "travel_type": "wormhole",
            },
            {
                "from_location_id": "pyro-nyx-gw",
                "to_location_id": "nyx-pyro-gw",
                "distance": 300.0,
                "travel_type": "wormhole",
            },
        ]
        with patch("httpx.get", return_value=_make_response(200, payload)) as mock_get:
            result = client.get_wormhole_distances()

        mock_get.assert_called_once_with(
            "http://maps-service/distances",
            params={"travel_type": "wormhole"},
            timeout=10.0,
        )
        assert len(result) == 2
        assert result[0] == DistanceData(
            from_location_id="stanton-pyro-gw",
            to_location_id="pyro-stanton-gw",
            distance=300.0,
            travel_type="wormhole",
        )

    def test_returns_empty_list_when_no_wormholes(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        with patch("httpx.get", return_value=_make_response(200, [])):
            result = client.get_wormhole_distances()

        assert result == []

    def test_raises_service_unavailable_on_5xx(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        with (
            patch("httpx.get", return_value=_make_response(500, {})),
            pytest.raises(ServiceUnavailableError) as exc_info,
        ):
            client.get_wormhole_distances()

        assert exc_info.value.service_name == "maps-service"
        assert exc_info.value.status_code == 500

    def test_returns_six_records_for_triangle_topology(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        payload = [
            {"from_location_id": "s-p-gw", "to_location_id": "p-s-gw", "distance": 300.0, "travel_type": "wormhole"},
            {"from_location_id": "p-s-gw", "to_location_id": "s-p-gw", "distance": 300.0, "travel_type": "wormhole"},
            {"from_location_id": "p-n-gw", "to_location_id": "n-p-gw", "distance": 300.0, "travel_type": "wormhole"},
            {"from_location_id": "n-p-gw", "to_location_id": "p-n-gw", "distance": 300.0, "travel_type": "wormhole"},
            {"from_location_id": "n-s-gw", "to_location_id": "s-n-gw", "distance": 300.0, "travel_type": "wormhole"},
            {"from_location_id": "s-n-gw", "to_location_id": "n-s-gw", "distance": 300.0, "travel_type": "wormhole"},
        ]
        with patch("httpx.get", return_value=_make_response(200, payload)):
            result = client.get_wormhole_distances()

        assert len(result) == 6

    def test_optional_travel_type_defaults_to_empty_string(self) -> None:
        client = HttpMapsClient(base_url="http://maps-service")
        payload = [{"from_location_id": "a", "to_location_id": "b", "distance": 100.0}]
        with patch("httpx.get", return_value=_make_response(200, payload)):
            result = client.get_wormhole_distances()

        assert result[0].travel_type == ""
