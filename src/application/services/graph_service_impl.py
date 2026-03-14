from src.application.ports.inbound.graph_service import GraphService
from src.application.ports.outbound.graph_repository import GraphRepository
from src.domain.exceptions.graph_exceptions import GraphNotFoundError
from src.domain.models.graph import Graph


class GraphServiceImpl(GraphService):

    def __init__(self, repository: GraphRepository) -> None:
        self._repository = repository

    def create(self, graph: Graph) -> Graph:
        return self._repository.save(graph)

    def get(self, graph_id: str) -> Graph:
        graph = self._repository.find_by_id(graph_id)
        if graph is None:
            raise GraphNotFoundError(graph_id)
        return graph

    def list_all(self) -> list[Graph]:
        return self._repository.find_all()

    def delete(self, graph_id: str) -> None:
        if not self._repository.delete(graph_id):
            raise GraphNotFoundError(graph_id)
