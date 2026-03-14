from src.domain.models.graph import Edge, Graph, Node
from src.infrastructure.adapters.inbound.api.graph_dto import EdgeDTO, GraphDTO, NodeDTO


class GraphApiMapper:

    @staticmethod
    def to_domain(dto: GraphDTO) -> Graph:
        return Graph(
            id=dto.id,
            name=dto.name,
            nodes=[Node(location_id=n.location_id, label=n.label) for n in dto.nodes],
            edges=[
                Edge(
                    source_id=e.source_id,
                    target_id=e.target_id,
                    distance=e.distance,
                    travel_type=e.travel_type,
                    travel_time_seconds=e.travel_time_seconds,
                )
                for e in dto.edges
            ],
        )

    @staticmethod
    def to_dto(graph: Graph) -> GraphDTO:
        return GraphDTO(
            _id=graph.id,
            name=graph.name,
            nodes=[NodeDTO(location_id=n.location_id, label=n.label) for n in graph.nodes],
            edges=[
                EdgeDTO(
                    source_id=e.source_id,
                    target_id=e.target_id,
                    distance=e.distance,
                    travel_type=e.travel_type,
                    travel_time_seconds=e.travel_time_seconds,
                )
                for e in graph.edges
            ],
        )
