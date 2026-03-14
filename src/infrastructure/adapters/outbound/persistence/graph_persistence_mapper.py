from src.domain.models.graph import Edge, Graph, Node


class GraphPersistenceMapper:

    @staticmethod
    def to_document(graph: Graph) -> dict:
        return {
            "name": graph.name,
            "nodes": [
                {"location_id": n.location_id, "label": n.label}
                for n in graph.nodes
            ],
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
        }

    @staticmethod
    def to_domain(doc: dict) -> Graph:
        return Graph(
            id=str(doc["_id"]),
            name=doc.get("name", ""),
            nodes=[
                Node(location_id=n["location_id"], label=n.get("label", ""))
                for n in doc.get("nodes", [])
            ],
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
        )
