from cachetools import TTLCache

from src.application.ports.inbound.graph_service import GraphService
from src.application.ports.outbound.graph_repository import GraphRepository
from src.domain.exceptions.graph_exceptions import GraphNotFoundError
from src.domain.models.graph import Graph

_LIST_ALL_KEY = "all"


class GraphServiceImpl(GraphService):

    def __init__(self, repository: GraphRepository) -> None:
        self._repository = repository
        self._graph_cache: TTLCache[str, Graph] = TTLCache(maxsize=64, ttl=600)
        self._list_cache: TTLCache[str, list[Graph]] = TTLCache(maxsize=1, ttl=600)

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
