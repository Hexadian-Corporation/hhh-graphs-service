from unittest.mock import MagicMock

import pytest

from src.application.ports.outbound.maps_client import LocationData
from src.domain.services.tree_builder import build_tree


@pytest.fixture
def mock_maps_client() -> MagicMock:
    return MagicMock()


class TestDeepHierarchy:
    def test_two_level_hierarchy(self, mock_maps_client: MagicMock) -> None:
        mock_maps_client.get_location_ancestors.return_value = [
            LocationData(id="a18-uuid", name="Area 18", location_type="city", parent_id="arc-uuid"),
            LocationData(id="arc-uuid", name="ArcCorp", location_type="planet", parent_id="stan-uuid"),
        ]

        result = build_tree("a18-uuid", mock_maps_client)

        assert result == ["a18-uuid", "arc-uuid"]
        mock_maps_client.get_location_ancestors.assert_called_once_with("a18-uuid")

    def test_three_level_hierarchy(self, mock_maps_client: MagicMock) -> None:
        mock_maps_client.get_location_ancestors.return_value = [
            LocationData(id="shop-uuid", name="Shop", location_type="shop", parent_id="a18-uuid"),
            LocationData(id="a18-uuid", name="Area 18", location_type="city", parent_id="arc-uuid"),
            LocationData(id="arc-uuid", name="ArcCorp", location_type="planet", parent_id="stan-uuid"),
        ]

        result = build_tree("shop-uuid", mock_maps_client)

        assert result == ["shop-uuid", "a18-uuid", "arc-uuid"]


class TestDirectChildOfStar:
    def test_lagrange_station(self, mock_maps_client: MagicMock) -> None:
        mock_maps_client.get_location_ancestors.return_value = [
            LocationData(id="arcl1-uuid", name="ARC-L1", location_type="station", parent_id="stan-uuid"),
        ]

        result = build_tree("arcl1-uuid", mock_maps_client)

        assert result == ["arcl1-uuid"]

    def test_gateway(self, mock_maps_client: MagicMock) -> None:
        mock_maps_client.get_location_ancestors.return_value = [
            LocationData(id="sp-gw-uuid", name="Stanton-Pyro GW", location_type="gateway", parent_id="stan-uuid"),
        ]

        result = build_tree("sp-gw-uuid", mock_maps_client)

        assert result == ["sp-gw-uuid"]


class TestStarItself:
    def test_star_returns_empty(self, mock_maps_client: MagicMock) -> None:
        mock_maps_client.get_location_ancestors.return_value = []

        result = build_tree("stan-uuid", mock_maps_client)

        assert result == []


class TestSystemFiltering:
    def test_system_node_excluded_if_present(self, mock_maps_client: MagicMock) -> None:
        """Safety: if the API accidentally includes a system node, it's filtered out."""
        mock_maps_client.get_location_ancestors.return_value = [
            LocationData(id="arcl1-uuid", name="ARC-L1", location_type="station", parent_id="stan-uuid"),
            LocationData(id="stan-uuid", name="Stanton", location_type="system", parent_id=None),
        ]

        result = build_tree("arcl1-uuid", mock_maps_client)

        assert result == ["arcl1-uuid"]

    def test_node_with_none_parent_excluded(self, mock_maps_client: MagicMock) -> None:
        """Safety: nodes with parent_id=None are excluded (likely system roots)."""
        mock_maps_client.get_location_ancestors.return_value = [
            LocationData(id="arcl1-uuid", name="ARC-L1", location_type="station", parent_id="stan-uuid"),
            LocationData(id="orphan-uuid", name="Orphan", location_type="unknown", parent_id=None),
        ]

        result = build_tree("arcl1-uuid", mock_maps_client)

        assert result == ["arcl1-uuid"]


class TestInputIsFirstElement:
    def test_first_element_is_input_location(self, mock_maps_client: MagicMock) -> None:
        mock_maps_client.get_location_ancestors.return_value = [
            LocationData(id="a18-uuid", name="Area 18", location_type="city", parent_id="arc-uuid"),
            LocationData(id="arc-uuid", name="ArcCorp", location_type="planet", parent_id="stan-uuid"),
        ]

        result = build_tree("a18-uuid", mock_maps_client)

        assert result[0] == "a18-uuid"
