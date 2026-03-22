from abc import ABC, abstractmethod

from src.domain.models.graph import Graph


class GraphService(ABC):
    @abstractmethod
    async def create(self, graph: Graph) -> Graph: ...

    @abstractmethod
    async def get(self, graph_id: str) -> Graph: ...

    @abstractmethod
    async def list_all(self) -> list[Graph]: ...

    @abstractmethod
    async def delete(self, graph_id: str) -> None: ...

    @abstractmethod
    async def generate(self, location_ids: list[str]) -> Graph:
        """Generate a distance graph from Maps data, deduplicating by hash."""
        ...

    @abstractmethod
    async def mark_graphs_stale(self, location_ids: list[str], reason: str) -> int:
        """Mark all graphs containing any of the given location IDs as stale.

        Returns the number of graphs updated.
        """
        ...  # pragma: no cover
