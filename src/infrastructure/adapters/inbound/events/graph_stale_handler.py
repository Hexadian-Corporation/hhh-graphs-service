"""StaleMarker adapter that marks graphs as stale when location data changes."""

from hhh_events import EventDocument, StaleMarker

from src.application.ports.inbound.graph_service import GraphService


class GraphStaleMarker(StaleMarker):
    """Marks affected graphs as stale when locations or distances change."""

    def __init__(self, graph_service: GraphService) -> None:
        self._graph_service = graph_service

    async def mark_stale(self, event: EventDocument) -> int:
        return await self._graph_service.mark_graphs_stale(
            location_ids=event.modified_ids,
            reason="data_import",
        )
