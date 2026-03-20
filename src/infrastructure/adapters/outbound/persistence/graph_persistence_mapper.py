from datetime import UTC, datetime

from src.domain.models.graph import Edge, Graph, Node


class GraphPersistenceMapper:
    @staticmethod
    def to_document(graph: Graph) -> dict:
        doc: dict = {
            "name": graph.name,
            "hash": graph.hash,
            "nodes": [{"location_id": n.location_id, "label": n.label} for n in graph.nodes],
            "edges": [
                {
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "distance": e.distance,
                    "travel_type": e.travel_type,
                    "travel_time_seconds": e.travel_time_seconds,
                }
                for e in graph.edges
            ],
            "stale": graph.stale,
            "stale_reason": graph.stale_reason,
            "stale_since": graph.stale_since,
        }
        return doc

    @staticmethod
    def to_domain(doc: dict) -> Graph:
        stale_since_raw = doc.get("stale_since")
        if isinstance(stale_since_raw, datetime) and stale_since_raw.tzinfo is None:
            stale_since_raw = stale_since_raw.replace(tzinfo=UTC)
        return Graph(
            id=str(doc["_id"]),
            name=doc.get("name", ""),
            hash=doc.get("hash", ""),
            nodes=[Node(location_id=n["location_id"], label=n.get("label", "")) for n in doc.get("nodes", [])],
            edges=[
                Edge(
                    source_id=e["source_id"],
                    target_id=e["target_id"],
                    distance=e.get("distance", 0.0),
                    travel_type=e.get("travel_type", ""),
                    travel_time_seconds=e.get("travel_time_seconds", 0.0),
                )
                for e in doc.get("edges", [])
            ],
            stale=doc.get("stale", False),
            stale_reason=doc.get("stale_reason"),
            stale_since=stale_since_raw,
        )
