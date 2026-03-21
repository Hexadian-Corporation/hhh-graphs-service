from src.application.ports.outbound.maps_client import DistanceData, LocationData
from src.domain.models.cross_system_result import CrossSystemResult
from src.domain.services.system_path_finder import find_cross_system_paths

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _loc(loc_id: str, name: str, location_type: str = "system", parent_id: str | None = None) -> LocationData:
    return LocationData(id=loc_id, name=name, location_type=location_type, parent_id=parent_id)


def _wormhole(from_id: str, to_id: str, distance: float = 300.0) -> DistanceData:
    return DistanceData(from_location_id=from_id, to_location_id=to_id, distance=distance, travel_type="wormhole")


# ---------------------------------------------------------------------------
# Topology: Triangle (Stanton ↔ Pyro ↔ Nyx ↔ Stanton)
# ---------------------------------------------------------------------------

_STANTON = _loc("stanton", "Stanton")
_PYRO = _loc("pyro", "Pyro")
_NYX = _loc("nyx", "Nyx")

_SP_GW = _loc("sp-gw", "Stanton-Pyro GW", "gateway", parent_id="stanton")
_PS_GW = _loc("ps-gw", "Pyro-Stanton GW", "gateway", parent_id="pyro")
_PN_GW = _loc("pn-gw", "Pyro-Nyx GW", "gateway", parent_id="pyro")
_NP_GW = _loc("np-gw", "Nyx-Pyro GW", "gateway", parent_id="nyx")
_NS_GW = _loc("ns-gw", "Nyx-Stanton GW", "gateway", parent_id="nyx")
_SN_GW = _loc("sn-gw", "Stanton-Nyx GW", "gateway", parent_id="stanton")

_TRIANGLE_LOCATIONS: dict[str, LocationData] = {
    loc.id: loc for loc in [_STANTON, _PYRO, _NYX, _SP_GW, _PS_GW, _PN_GW, _NP_GW, _NS_GW, _SN_GW]
}

_TRIANGLE_WORMHOLES: list[DistanceData] = [
    _wormhole("sp-gw", "ps-gw"),
    _wormhole("pn-gw", "np-gw"),
    _wormhole("ns-gw", "sn-gw"),
]


class TestTriangleTopology:
    """Triangle: Stanton ↔ Pyro ↔ Nyx ↔ Stanton (3 systems, 6 gateways)."""

    def test_pyro_to_stanton_finds_two_paths(self) -> None:
        result = find_cross_system_paths("pyro", "stanton", _TRIANGLE_WORMHOLES, _TRIANGLE_LOCATIONS)

        assert sorted(result.gateway_node_ids) == ["np-gw", "ns-gw", "pn-gw", "ps-gw", "sn-gw", "sp-gw"]
        assert len(result.gateway_node_ids) == 6

    def test_pyro_to_stanton_intermediate_systems(self) -> None:
        result = find_cross_system_paths("pyro", "stanton", _TRIANGLE_WORMHOLES, _TRIANGLE_LOCATIONS)

        assert result.intermediate_system_ids == ["nyx"]

    def test_stanton_to_nyx_finds_two_paths(self) -> None:
        result = find_cross_system_paths("stanton", "nyx", _TRIANGLE_WORMHOLES, _TRIANGLE_LOCATIONS)

        assert len(result.gateway_node_ids) == 6
        assert result.intermediate_system_ids == ["pyro"]

    def test_result_is_symmetric(self) -> None:
        forward = find_cross_system_paths("pyro", "stanton", _TRIANGLE_WORMHOLES, _TRIANGLE_LOCATIONS)
        backward = find_cross_system_paths("stanton", "pyro", _TRIANGLE_WORMHOLES, _TRIANGLE_LOCATIONS)

        assert sorted(forward.gateway_node_ids) == sorted(backward.gateway_node_ids)


# ---------------------------------------------------------------------------
# Topology: Linear chain (A → B → C, no shortcuts)
# ---------------------------------------------------------------------------

_SYS_A = _loc("sys-a", "System A")
_SYS_B = _loc("sys-b", "System B")
_SYS_C = _loc("sys-c", "System C")

_AB_GW = _loc("ab-gw", "A-B GW", "gateway", parent_id="sys-a")
_BA_GW = _loc("ba-gw", "B-A GW", "gateway", parent_id="sys-b")
_BC_GW = _loc("bc-gw", "B-C GW", "gateway", parent_id="sys-b")
_CB_GW = _loc("cb-gw", "C-B GW", "gateway", parent_id="sys-c")

_LINEAR_LOCATIONS: dict[str, LocationData] = {
    loc.id: loc for loc in [_SYS_A, _SYS_B, _SYS_C, _AB_GW, _BA_GW, _BC_GW, _CB_GW]
}

_LINEAR_WORMHOLES: list[DistanceData] = [
    _wormhole("ab-gw", "ba-gw"),
    _wormhole("bc-gw", "cb-gw"),
]


class TestLinearChainTopology:
    """Linear: A ↔ B ↔ C (no shortcuts)."""

    def test_a_to_c_finds_one_path(self) -> None:
        result = find_cross_system_paths("sys-a", "sys-c", _LINEAR_WORMHOLES, _LINEAR_LOCATIONS)

        assert sorted(result.gateway_node_ids) == ["ab-gw", "ba-gw", "bc-gw", "cb-gw"]
        assert len(result.gateway_node_ids) == 4

    def test_a_to_c_intermediate_is_b(self) -> None:
        result = find_cross_system_paths("sys-a", "sys-c", _LINEAR_WORMHOLES, _LINEAR_LOCATIONS)

        assert result.intermediate_system_ids == ["sys-b"]

    def test_a_to_b_direct(self) -> None:
        result = find_cross_system_paths("sys-a", "sys-b", _LINEAR_WORMHOLES, _LINEAR_LOCATIONS)

        assert sorted(result.gateway_node_ids) == ["ab-gw", "ba-gw"]
        assert result.intermediate_system_ids == []


# ---------------------------------------------------------------------------
# Topology: Disconnected systems
# ---------------------------------------------------------------------------

_ISO_C = _loc("iso-c", "Isolated C")

_DISCONNECTED_LOCATIONS: dict[str, LocationData] = {loc.id: loc for loc in [_SYS_A, _SYS_B, _ISO_C, _AB_GW, _BA_GW]}

_DISCONNECTED_WORMHOLES: list[DistanceData] = [
    _wormhole("ab-gw", "ba-gw"),
]


class TestDisconnectedTopology:
    """A ↔ B, C isolated — no path A → C."""

    def test_no_path_returns_empty_result(self) -> None:
        result = find_cross_system_paths("sys-a", "iso-c", _DISCONNECTED_WORMHOLES, _DISCONNECTED_LOCATIONS)

        assert result.gateway_node_ids == []
        assert result.intermediate_system_ids == []

    def test_no_path_result_type(self) -> None:
        result = find_cross_system_paths("sys-a", "iso-c", _DISCONNECTED_WORMHOLES, _DISCONNECTED_LOCATIONS)

        assert isinstance(result, CrossSystemResult)


# ---------------------------------------------------------------------------
# Topology: Star (Hub ↔ Spoke1, Hub ↔ Spoke2, Hub ↔ Spoke3)
# ---------------------------------------------------------------------------

_HUB = _loc("hub", "Hub System")
_SPOKE1 = _loc("spoke-1", "Spoke 1")
_SPOKE2 = _loc("spoke-2", "Spoke 2")
_SPOKE3 = _loc("spoke-3", "Spoke 3")

_H1_GW = _loc("h1-gw", "Hub→Spoke1 GW", "gateway", parent_id="hub")
_S1H_GW = _loc("s1h-gw", "Spoke1→Hub GW", "gateway", parent_id="spoke-1")
_H2_GW = _loc("h2-gw", "Hub→Spoke2 GW", "gateway", parent_id="hub")
_S2H_GW = _loc("s2h-gw", "Spoke2→Hub GW", "gateway", parent_id="spoke-2")
_H3_GW = _loc("h3-gw", "Hub→Spoke3 GW", "gateway", parent_id="hub")
_S3H_GW = _loc("s3h-gw", "Spoke3→Hub GW", "gateway", parent_id="spoke-3")

_STAR_LOCATIONS: dict[str, LocationData] = {
    loc.id: loc for loc in [_HUB, _SPOKE1, _SPOKE2, _SPOKE3, _H1_GW, _S1H_GW, _H2_GW, _S2H_GW, _H3_GW, _S3H_GW]
}

_STAR_WORMHOLES: list[DistanceData] = [
    _wormhole("h1-gw", "s1h-gw"),
    _wormhole("h2-gw", "s2h-gw"),
    _wormhole("h3-gw", "s3h-gw"),
]


class TestStarTopology:
    """Star: Hub ↔ Spoke1, Hub ↔ Spoke2, Hub ↔ Spoke3."""

    def test_spoke1_to_spoke2_via_hub(self) -> None:
        result = find_cross_system_paths("spoke-1", "spoke-2", _STAR_WORMHOLES, _STAR_LOCATIONS)

        assert sorted(result.gateway_node_ids) == ["h1-gw", "h2-gw", "s1h-gw", "s2h-gw"]
        assert result.intermediate_system_ids == ["hub"]

    def test_spoke1_to_spoke3_via_hub(self) -> None:
        result = find_cross_system_paths("spoke-1", "spoke-3", _STAR_WORMHOLES, _STAR_LOCATIONS)

        assert sorted(result.gateway_node_ids) == ["h1-gw", "h3-gw", "s1h-gw", "s3h-gw"]
        assert result.intermediate_system_ids == ["hub"]


# ---------------------------------------------------------------------------
# Edge case: Same system
# ---------------------------------------------------------------------------


class TestSameSystem:
    def test_same_system_returns_empty_result(self) -> None:
        result = find_cross_system_paths("stanton", "stanton", _TRIANGLE_WORMHOLES, _TRIANGLE_LOCATIONS)

        assert result.gateway_node_ids == []
        assert result.intermediate_system_ids == []


# ---------------------------------------------------------------------------
# Edge case: Unknown source system (not in graph)
# ---------------------------------------------------------------------------


class TestUnknownSystem:
    def test_unknown_source_returns_empty(self) -> None:
        result = find_cross_system_paths("unknown", "stanton", _TRIANGLE_WORMHOLES, _TRIANGLE_LOCATIONS)

        assert result.gateway_node_ids == []
        assert result.intermediate_system_ids == []

    def test_unknown_target_returns_empty(self) -> None:
        result = find_cross_system_paths("stanton", "unknown", _TRIANGLE_WORMHOLES, _TRIANGLE_LOCATIONS)

        assert result.gateway_node_ids == []
        assert result.intermediate_system_ids == []


# ---------------------------------------------------------------------------
# Edge case: Empty wormhole list
# ---------------------------------------------------------------------------


class TestEmptyInput:
    def test_no_wormholes_returns_empty(self) -> None:
        result = find_cross_system_paths("stanton", "pyro", [], _TRIANGLE_LOCATIONS)

        assert result.gateway_node_ids == []
        assert result.intermediate_system_ids == []


# ---------------------------------------------------------------------------
# Deep parent chain: gateway → moon → planet → system
# ---------------------------------------------------------------------------


class TestDeepParentChain:
    """Gateway whose parent_id is not a system directly (gateway → planet → system)."""

    def test_resolves_through_multi_level_hierarchy(self) -> None:
        sys_x = _loc("sys-x", "System X")
        planet = _loc("planet-x1", "Planet X1", "planet", parent_id="sys-x")
        gw_x = _loc("gw-x", "GW X Side", "gateway", parent_id="planet-x1")

        sys_y = _loc("sys-y", "System Y")
        gw_y = _loc("gw-y", "GW Y Side", "gateway", parent_id="sys-y")

        locations: dict[str, LocationData] = {loc.id: loc for loc in [sys_x, planet, gw_x, sys_y, gw_y]}
        wormholes = [_wormhole("gw-x", "gw-y")]

        result = find_cross_system_paths("sys-x", "sys-y", wormholes, locations)

        assert sorted(result.gateway_node_ids) == ["gw-x", "gw-y"]
        assert result.intermediate_system_ids == []
