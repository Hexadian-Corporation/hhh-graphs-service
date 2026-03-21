from collections import defaultdict, deque

from src.application.ports.outbound.maps_client import DistanceData, LocationData
from src.domain.models.cross_system_result import CrossSystemResult


def _resolve_system_id(location_id: str, locations_by_id: dict[str, LocationData]) -> str | None:
    """Walk the parent_id chain to find the top-level system for a gateway location."""
    current = locations_by_id.get(location_id)
    while current is not None:
        parent = locations_by_id.get(current.parent_id) if current.parent_id else None
        if parent is None:
            return current.id
        current = parent
    return None


def _build_system_graph(
    wormhole_distances: list[DistanceData],
    locations_by_id: dict[str, LocationData],
) -> tuple[dict[str, set[str]], dict[tuple[str, str], list[tuple[str, str]]]]:
    """Build a system-level adjacency graph from wormhole distance records.

    Returns:
        adjacency: system_id → set of connected system_ids
        gateway_pairs: (system_a, system_b) → list of (gateway_a_id, gateway_b_id)
    """
    adjacency: dict[str, set[str]] = defaultdict(set)
    gateway_pairs: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)

    for wd in wormhole_distances:
        sys_a = _resolve_system_id(wd.from_location_id, locations_by_id)
        sys_b = _resolve_system_id(wd.to_location_id, locations_by_id)
        if sys_a is None or sys_b is None or sys_a == sys_b:
            continue

        adjacency[sys_a].add(sys_b)
        adjacency[sys_b].add(sys_a)

        edge_key = (sys_a, sys_b)
        gateway_pairs[edge_key].append((wd.from_location_id, wd.to_location_id))

        reverse_key = (sys_b, sys_a)
        gateway_pairs[reverse_key].append((wd.to_location_id, wd.from_location_id))

    return dict(adjacency), dict(gateway_pairs)


def find_cross_system_paths(
    source_system_id: str,
    target_system_id: str,
    wormhole_distances: list[DistanceData],
    locations_by_id: dict[str, LocationData],
) -> CrossSystemResult:
    """Find ALL non-cyclic paths between two systems via wormhole gateways.

    Uses BFS with per-path visited tracking to enumerate every possible route.
    Returns all gateway node IDs and intermediate systems involved in any path.
    """
    if source_system_id == target_system_id:
        return CrossSystemResult()

    adjacency, gateway_pairs = _build_system_graph(wormhole_distances, locations_by_id)

    if source_system_id not in adjacency:
        return CrossSystemResult()

    all_paths: list[list[str]] = []
    queue: deque[tuple[str, list[str]]] = deque()
    queue.append((source_system_id, [source_system_id]))

    while queue:
        current, path = queue.popleft()
        if current == target_system_id:
            all_paths.append(path)
            continue
        for neighbor in adjacency.get(current, set()):
            if neighbor not in path:
                queue.append((neighbor, [*path, neighbor]))

    if not all_paths:
        return CrossSystemResult()

    gateway_node_ids: set[str] = set()
    intermediate_system_ids: set[str] = set()

    for path in all_paths:
        for i in range(len(path) - 1):
            sys_from = path[i]
            sys_to = path[i + 1]
            for gw_from, gw_to in gateway_pairs.get((sys_from, sys_to), []):
                gateway_node_ids.add(gw_from)
                gateway_node_ids.add(gw_to)

        for sys_id in path[1:-1]:
            intermediate_system_ids.add(sys_id)

    return CrossSystemResult(
        gateway_node_ids=sorted(gateway_node_ids),
        intermediate_system_ids=sorted(intermediate_system_ids),
    )
