from src.application.ports.outbound.maps_client import MapsClient


def build_tree(location_id: str, maps_client: MapsClient) -> list[str]:
    """Build the ancestor chain from a location up to (excluding) the star/system root.

    Returns an ordered list of location IDs: [location, parent, grandparent, ...]
    where the star (location_type == "system" or parent_id is None) is excluded.
    """
    ancestors = maps_client.get_location_ancestors(location_id)
    return [loc.id for loc in ancestors if loc.location_type != "system" and loc.parent_id is not None]
