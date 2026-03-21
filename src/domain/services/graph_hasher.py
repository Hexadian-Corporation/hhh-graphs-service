import hashlib
import json

from src.domain.models.graph import Edge, Node


def compute_graph_hash(nodes: list[Node], edges: list[Edge]) -> str:
    """Compute a deterministic SHA-256 hash for a set of nodes and edges.

    Nodes are sorted by location_id. Edges are sorted by (source_id, target_id).
    This ensures the same graph always produces the same hash regardless of input order.

    ``travel_time_seconds`` is intentionally excluded from the hash because
    time-based graphs are ephemeral and including travel time would make the
    hash nave-dependent.
    """
    sorted_nodes = sorted(
        [{"location_id": n.location_id, "label": n.label} for n in nodes],
        key=lambda x: x["location_id"],
    )
    sorted_edges = sorted(
        [
            {
                "source_id": e.source_id,
                "target_id": e.target_id,
                "distance": e.distance,
                "travel_type": e.travel_type,
            }
            for e in edges
        ],
        key=lambda x: (x["source_id"], x["target_id"]),
    )

    canonical = json.dumps(
        {"nodes": sorted_nodes, "edges": sorted_edges},
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_hash(location_ids: list[str]) -> str:
    """Compute a deterministic, order-independent hash from a list of location IDs.

    Used for two-level caching:
    - Level 1 (full-request): compute_hash(["A", "B", "C"]) → merged graph lookup
    - Level 2 (pairwise):     compute_hash(["A", "B"])       → pair graph lookup

    IDs are sorted alphabetically and joined with ``|`` before hashing, so the
    result is identical regardless of the order in which the caller supplies them.
    """
    canonical = "|".join(sorted(location_ids))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
