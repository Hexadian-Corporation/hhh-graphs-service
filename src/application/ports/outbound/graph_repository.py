from abc import ABC, abstractmethod

from src.domain.models.graph import Graph


class GraphRepository(ABC):
    @abstractmethod
    async def save(self, graph: Graph) -> Graph: ...

    @abstractmethod
    async def find_by_id(self, graph_id: str) -> Graph | None: ...

    @abstractmethod
    async def find_all(self) -> list[Graph]: ...

    @abstractmethod
    async def delete(self, graph_id: str) -> bool: ...

    @abstractmethod
    async def find_by_hash(self, hash_value: str) -> Graph | None: ...
