from abc import ABC, abstractmethod
from datetime import datetime

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

    @abstractmethod
    async def mark_stale_by_location_ids(self, location_ids: list[str], reason: str, since: datetime) -> int:
        """Mark all graphs containing any of the given node location IDs as stale.

        Returns the number of graphs updated.
        """
        ...
