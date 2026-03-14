from abc import ABC, abstractmethod

from src.domain.models.graph import Graph


class GraphService(ABC):

    @abstractmethod
    def create(self, graph: Graph) -> Graph: ...

    @abstractmethod
    def get(self, graph_id: str) -> Graph: ...

    @abstractmethod
    def list_all(self) -> list[Graph]: ...

    @abstractmethod
    def delete(self, graph_id: str) -> None: ...
