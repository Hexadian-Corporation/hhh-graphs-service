from itertools import combinations

from cachetools import TTLCache

from src.application.ports.inbound.graph_service import GraphService
from src.application.ports.outbound.graph_repository import GraphRepository
from src.application.ports.outbound.maps_client import LocationData, MapsClient
from src.domain.exceptions.graph_exceptions import GraphNotFoundError
from src.domain.models.graph import Edge, Graph, Node
from src.domain.services.graph_hasher import compute_hash
from src.domain.services.system_path_finder import find_cross_system_paths

_LIST_ALL_KEY = "all"


class GraphServiceImpl(GraphService):
    def __init__(self, repository: GraphRepository, maps_client: MapsClient) -> None:
        self._repository = repository
        self._maps_client = maps_client
        self._graph_cache: TTLCache[str, Graph] = TTLCache(maxsize=64, ttl=3600)
        self._list_cache: TTLCache[str, list[Graph]] = TTLCache(maxsize=1, ttl=3600)

    def _invalidate_cache(self) -> None:
        self._graph_cache.clear()
        self._list_cache.clear()

    def create(self, graph: Graph) -> Graph:
        result = self._repository.save(graph)
        self._invalidate_cache()
        return result

    def get(self, graph_id: str) -> Graph:
        cached = self._graph_cache.get(graph_id)
        if cached is not None:
            return cached
        graph = self._repository.find_by_id(graph_id)
        if graph is None:
            raise GraphNotFoundError(graph_id)
        self._graph_cache[graph_id] = graph
        return graph

    def list_all(self) -> list[Graph]:
        cached = self._list_cache.get(_LIST_ALL_KEY)
        if cached is not None:
            return cached
        graphs = self._repository.find_all()
        self._list_cache[_LIST_ALL_KEY] = graphs
        return graphs

    def delete(self, graph_id: str) -> None:
        if not self._repository.delete(graph_id):
            raise GraphNotFoundError(graph_id)
        self._invalidate_cache()

    # ------------------------------------------------------------------
    # Pairwise graph composition with two-level hash caching (#41)
    # ------------------------------------------------------------------

    def generate(self, location_ids: list[str]) -> Graph:
        if len(location_ids) < 2:
            raise ValueError("At least two location IDs are required")

        # --- Level 1: full-request hash ---
        full_hash = compute_hash(location_ids)
        existing = self._repository.find_by_hash(full_hash)
        if existing is not None:
            self._graph_cache[existing.id] = existing
            return existing

        # --- Pairwise loop ---
        sorted_ids = sorted(set(location_ids))
        pairwise_graphs: list[Graph] = []

        for id_a, id_b in combinations(sorted_ids, 2):
            # Level 2: pairwise hash
            pair_hash = compute_hash([id_a, id_b])
            cached_pair = self._repository.find_by_hash(pair_hash)
            if cached_pair is not None:
                pairwise_graphs.append(cached_pair)
                continue

            pair_graph = self._build_pairwise_graph(id_a, id_b, pair_hash)
            pairwise_graphs.append(pair_graph)

        # --- Merge & persist ---
        merged = self._merge_graphs(pairwise_graphs)
        merged.hash = full_hash
        merged.name = f"distance-graph-{len(merged.nodes)}n-{len(merged.edges)}e"

        created = self._repository.save(merged)
        self._invalidate_cache()
        return created

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_tree_and_system(
        ancestors: list[LocationData],
    ) -> tuple[list[str], str | None]:
        """Derive tree node IDs and system ID from an ancestor chain.

        Uses the same filtering logic as ``tree_builder.build_tree`` (#39):
        exclude nodes with ``location_type == "system"`` or ``parent_id is None``.
        The system ID is the ``parent_id`` of the highest remaining ancestor.
        """
        filtered = [a for a in ancestors if a.location_type != "system" and a.parent_id is not None]
        tree_ids = [a.id for a in filtered]
        system_id = filtered[-1].parent_id if filtered else None
        return tree_ids, system_id

    def _build_pairwise_graph(self, id_a: str, id_b: str, pair_hash: str) -> Graph:
        """Build, persist, and return a pairwise graph for two locations."""
        # Ancestor chains (one API call each)
        ancestors_a = self._maps_client.get_location_ancestors(id_a)
        ancestors_b = self._maps_client.get_location_ancestors(id_b)

        tree_a, system_a = self._resolve_tree_and_system(ancestors_a)
        tree_b, system_b = self._resolve_tree_and_system(ancestors_b)

        node_ids: set[str] = set(tree_a) | set(tree_b)
        loc_dict: dict[str, LocationData] = {a.id: a for a in ancestors_a + ancestors_b}

        # Cross-system: add gateway nodes via BFS
        if system_a and system_b and system_a != system_b:
            wormhole_distances = self._maps_client.get_wormhole_distances()

            # Collect gateway IDs & fetch their LocationData + parent systems
            gw_ids: set[str] = set()
            for wd in wormhole_distances:
                gw_ids.add(wd.from_location_id)
                gw_ids.add(wd.to_location_id)

            gw_locations = self._maps_client.get_locations(list(gw_ids))
            parent_ids = {loc.parent_id for loc in gw_locations if loc.parent_id} - gw_ids
            parent_locations = self._maps_client.get_locations(list(parent_ids)) if parent_ids else []

            locations_by_id: dict[str, LocationData] = {loc.id: loc for loc in gw_locations + parent_locations}

            result = find_cross_system_paths(system_a, system_b, wormhole_distances, locations_by_id)
            node_ids.update(result.gateway_node_ids)
            loc_dict.update(locations_by_id)

        # Fetch edges for all nodes in the set
        distances = self._maps_client.get_distances_for_locations(list(node_ids))

        # Fetch labels for any node IDs not yet in loc_dict
        missing_ids = node_ids - set(loc_dict)
        if missing_ids:
            for loc in self._maps_client.get_locations(list(missing_ids)):
                loc_dict[loc.id] = loc

        nodes = [Node(location_id=nid, label=loc_dict[nid].name if nid in loc_dict else nid) for nid in node_ids]
        edges = [
            Edge(
                source_id=d.from_location_id,
                target_id=d.to_location_id,
                distance=d.distance,
                travel_type=d.travel_type,
                travel_time_seconds=0.0,
            )
            for d in distances
        ]

        graph = Graph(
            name=f"distance-graph-{len(nodes)}n-{len(edges)}e",
            hash=pair_hash,
            nodes=nodes,
            edges=edges,
        )
        return self._repository.save(graph)

    @staticmethod
    def _merge_graphs(graphs: list[Graph]) -> Graph:
        """Merge multiple graphs: union nodes, deduplicate edges by (source_id, target_id)."""
        node_map: dict[str, Node] = {}
        edge_map: dict[tuple[str, str], Edge] = {}

        for g in graphs:
            for node in g.nodes:
                node_map[node.location_id] = node
            for edge in g.edges:
                key = (edge.source_id, edge.target_id)
                if key not in edge_map:
                    edge_map[key] = edge

        return Graph(nodes=list(node_map.values()), edges=list(edge_map.values()))
