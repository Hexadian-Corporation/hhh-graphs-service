from dataclasses import dataclass, field


@dataclass
class CrossSystemResult:
    """Result of BFS pathfinding between two systems."""

    gateway_node_ids: list[str] = field(default_factory=list)
    intermediate_system_ids: list[str] = field(default_factory=list)
