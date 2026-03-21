import httpx

from src.application.ports.outbound.maps_client import DistanceData, LocationData, MapsClient
from src.domain.exceptions.graph_exceptions import LocationNotFoundError, ServiceUnavailableError


class HttpMapsClient(MapsClient):
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def get_locations(self, location_ids: list[str]) -> list[LocationData]:
        locations = []
        # Fetch each location individually (Maps API is GET /locations/{id})
        for loc_id in location_ids:
            resp = httpx.get(
                f"{self._base_url}/locations/{loc_id}",
                timeout=self._timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                locations.append(
                    LocationData(
                        id=data["_id"],
                        name=data["name"],
                        location_type=data.get("location_type", ""),
                        parent_id=data.get("parent_id"),
                    )
                )
        return locations

    def get_distances_for_locations(self, location_ids: list[str]) -> list[DistanceData]:
        distances = []
        seen_pairs: set[tuple[str, str]] = set()
        # For each location, fetch its distances and filter to only include
        # edges where BOTH endpoints are in the requested location_ids set
        loc_id_set = set(location_ids)
        for loc_id in location_ids:
            resp = httpx.get(
                f"{self._base_url}/locations/{loc_id}/distances",
                timeout=self._timeout,
            )
            if resp.status_code == 200:
                for d in resp.json():
                    from_id = d["from_location_id"]
                    to_id = d["to_location_id"]
                    # Only include edges where both endpoints are in our set
                    if from_id not in loc_id_set or to_id not in loc_id_set:
                        continue
                    pair = tuple(sorted([from_id, to_id]))
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)
                    distances.append(
                        DistanceData(
                            from_location_id=from_id,
                            to_location_id=to_id,
                            distance=d["distance"],
                            travel_type=d.get("travel_type", ""),
                        )
                    )
        return distances

    def get_location_ancestors(self, location_id: str) -> list[LocationData]:
        resp = httpx.get(
            f"{self._base_url}/locations/{location_id}/ancestors",
            timeout=self._timeout,
        )
        if resp.status_code == 404:
            raise LocationNotFoundError(location_id)
        if resp.status_code >= 500:
            raise ServiceUnavailableError("maps-service", resp.status_code)
        return [
            LocationData(
                id=loc["_id"],
                name=loc["name"],
                location_type=loc.get("location_type", ""),
                parent_id=loc.get("parent_id"),
            )
            for loc in resp.json()
        ]

    def get_wormhole_distances(self) -> list[DistanceData]:
        resp = httpx.get(
            f"{self._base_url}/distances",
            params={"travel_type": "wormhole"},
            timeout=self._timeout,
        )
        if resp.status_code >= 500:
            raise ServiceUnavailableError("maps-service", resp.status_code)
        return [
            DistanceData(
                from_location_id=d["from_location_id"],
                to_location_id=d["to_location_id"],
                distance=d["distance"],
                travel_type=d.get("travel_type", ""),
            )
            for d in resp.json()
        ]
