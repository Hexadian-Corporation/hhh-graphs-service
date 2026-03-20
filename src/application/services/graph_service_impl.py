from cachetools import TTLCache

from src.application.ports.inbound.graph_service import GraphService
from src.application.ports.outbound.graph_repository import GraphRepository
from src.application.ports.outbound.maps_client import MapsClient
from src.domain.exceptions.graph_exceptions import GraphNotFoundError
from src.domain.models.graph import Edge, Graph, Node
from src.domain.services.graph_hasher import compute_graph_hash

_LIST_ALL_KEY = "all"


class GraphServiceImpl(GraphService):
    def __init__(self, repository: GraphRepository, maps_client: MapsClient) -> None:
        self._repository = repository
        self._maps_client = maps_client
        self._graph_cache: TTLCache[str, Graph] = TTLCache(maxsize=64, ttl=3600)
        self._list_cache: TTLCache[str, list[Graph]] = TTLCache(maxsize=1, ttl=3600)

    def _invalidate_cache(self) -> None:
        self._graph_cache.clear()
        self._list_cache.clear()

    def create(self, graph: Graph) -> Graph:
        result = self._repository.save(graph)
        self._invalidate_cache()
        return result

    def get(self, graph_id: str) -> Graph:
        cached = self._graph_cache.get(graph_id)
        if cached is not None:
            return cached
        graph = self._repository.find_by_id(graph_id)
        if graph is None:
            raise GraphNotFoundError(graph_id)
        self._graph_cache[graph_id] = graph
        return graph

    def list_all(self) -> list[Graph]:
        cached = self._list_cache.get(_LIST_ALL_KEY)
        if cached is not None:
            return cached
        graphs = self._repository.find_all()
        self._list_cache[_LIST_ALL_KEY] = graphs
        return graphs

    def delete(self, graph_id: str) -> None:
        if not self._repository.delete(graph_id):
            raise GraphNotFoundError(graph_id)
        self._invalidate_cache()

    def generate(self, location_ids: list[str]) -> Graph:
        locations = self._maps_client.get_locations(location_ids)
        if not locations:
            raise ValueError("No locations found for the given IDs")

        distances = self._maps_client.get_distances_for_locations(location_ids)

        nodes = [Node(location_id=loc.id, label=loc.name) for loc in locations]
        edges = [
            Edge(
                source_id=d.from_location_id,
                target_id=d.to_location_id,
                distance=d.distance,
                travel_type=d.travel_type,
                travel_time_seconds=0.0,
            )
            for d in distances
        ]

        graph_hash = compute_graph_hash(nodes, edges)

        existing = self._repository.find_by_hash(graph_hash)
        if existing is not None:
            self._graph_cache[existing.id] = existing
            return existing

        graph = Graph(
            name=f"distance-graph-{len(nodes)}n-{len(edges)}e",
            hash=graph_hash,
            nodes=nodes,
            edges=edges,
        )
        created = self._repository.save(graph)
        self._invalidate_cache()
        return created
