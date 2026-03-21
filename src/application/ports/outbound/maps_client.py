from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LocationData:
    """Lightweight representation of a Maps service Location."""

    id: str = ""
    name: str = ""
    location_type: str = ""
    parent_id: str | None = None


@dataclass
class DistanceData:
    """Lightweight representation of a Maps service LocationDistance."""

    from_location_id: str = ""
    to_location_id: str = ""
    distance: float = 0.0
    travel_type: str = ""


class MapsClient(ABC):
    @abstractmethod
    async def get_locations(self, location_ids: list[str]) -> list[LocationData]:
        """Fetch multiple locations by ID from Maps service."""
        ...

    @abstractmethod
    async def get_distances_for_locations(self, location_ids: list[str]) -> list[DistanceData]:
        """Fetch all distances between the given location IDs from Maps service."""
        ...

    @abstractmethod
    async def get_location_ancestors(self, location_id: str) -> list[LocationData]:
        """Return ancestor chain: [location, parent, grandparent, ...] excluding star/system root."""
        ...

    @abstractmethod
    async def get_wormhole_distances(self) -> list[DistanceData]:
        """Return all LocationDistance records with travel_type='wormhole'."""
        ...
