class GraphNotFoundError(Exception):
    def __init__(self, graph_id: str) -> None:
        super().__init__(f"Graph not found: {graph_id}")
        self.graph_id = graph_id


class LocationNotFoundError(Exception):
    def __init__(self, location_id: str) -> None:
        super().__init__(f"Location not found: {location_id}")
        self.location_id = location_id


class ServiceUnavailableError(Exception):
    def __init__(self, service_name: str, status_code: int | None = None) -> None:
        detail = f"{service_name} is unavailable"
        if status_code is not None:
            detail += f" (HTTP {status_code})"
        super().__init__(detail)
        self.service_name = service_name
        self.status_code = status_code
