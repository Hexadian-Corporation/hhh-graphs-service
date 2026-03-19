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
    def get_locations(self, location_ids: list[str]) -> list[LocationData]:
        """Fetch multiple locations by ID from Maps service."""
        ...

    @abstractmethod
    def get_distances_for_locations(self, location_ids: list[str]) -> list[DistanceData]:
        """Fetch all distances between the given location IDs from Maps service."""
        ...
