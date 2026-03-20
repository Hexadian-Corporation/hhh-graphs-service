from datetime import datetime

from pydantic import BaseModel, Field


class NodeDTO(BaseModel):
    location_id: str
    label: str = ""


class EdgeDTO(BaseModel):
    source_id: str
    target_id: str
    distance: float = 0.0
    travel_type: str = ""
    travel_time_seconds: float = 0.0


class GraphGenerateDTO(BaseModel):
    """Request body for graph generation."""

    location_ids: list[str]


class GraphDTO(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    name: str
    hash: str = ""
    nodes: list[NodeDTO] = Field(default_factory=list)
    edges: list[EdgeDTO] = Field(default_factory=list)
    stale: bool = False
    stale_reason: str | None = None
    stale_since: datetime | None = None

    model_config = {"populate_by_name": True}
