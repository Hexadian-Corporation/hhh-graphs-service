from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Edge:
    source_id: str = ""
    target_id: str = ""
    distance: float = 0.0
    travel_type: str = ""  # quantum, scm, on_foot
    travel_time_seconds: float = 0.0


@dataclass
class Node:
    location_id: str = ""
    label: str = ""


@dataclass
class Graph:
    id: str | None = None
    name: str = ""
    hash: str = ""
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    stale: bool = False
    stale_reason: str | None = None
    stale_since: datetime | None = None
