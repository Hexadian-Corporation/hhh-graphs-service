from abc import ABC, abstractmethod

from src.domain.models.graph import Graph


class GraphRepository(ABC):
    @abstractmethod
    def save(self, graph: Graph) -> Graph: ...

    @abstractmethod
    def find_by_id(self, graph_id: str) -> Graph | None: ...

    @abstractmethod
    def find_all(self) -> list[Graph]: ...

    @abstractmethod
    def delete(self, graph_id: str) -> bool: ...

    @abstractmethod
    def find_by_hash(self, hash_value: str) -> Graph | None: ...
