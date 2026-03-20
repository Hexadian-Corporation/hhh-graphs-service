from fastapi import APIRouter, Depends, HTTPException, Response
from hexadian_auth_common.fastapi import require_permission

from src.application.ports.inbound.graph_service import GraphService
from src.domain.exceptions.graph_exceptions import GraphNotFoundError
from src.infrastructure.adapters.inbound.api.graph_api_mapper import GraphApiMapper
from src.infrastructure.adapters.inbound.api.graph_dto import GraphDTO, GraphGenerateDTO

router = APIRouter(prefix="/graphs", tags=["graphs"])

_graph_service: GraphService | None = None

_read = [Depends(require_permission("hhh:graphs:read"))]
_write = [Depends(require_permission("hhh:graphs:write"))]
_delete = [Depends(require_permission("hhh:graphs:delete"))]


def init_router(graph_service: GraphService) -> None:
    global _graph_service
    _graph_service = graph_service


@router.post("/", response_model=GraphDTO, status_code=201, dependencies=_write)
def create_graph(dto: GraphDTO) -> GraphDTO:
    graph = GraphApiMapper.to_domain(dto)
    created = _graph_service.create(graph)
    return GraphApiMapper.to_dto(created)


@router.post("/generate", response_model=GraphDTO, status_code=201, dependencies=_write)
def generate_graph(dto: GraphGenerateDTO) -> GraphDTO:
    """Generate a distance graph from Maps data, deduplicating by hash."""
    try:
        graph = _graph_service.generate(dto.location_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GraphApiMapper.to_dto(graph)


@router.get("/{graph_id}", response_model=GraphDTO, dependencies=_read)
def get_graph(graph_id: str, response: Response) -> GraphDTO:
    response.headers["Cache-Control"] = "max-age=3600"
    try:
        graph = _graph_service.get(graph_id)
    except GraphNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return GraphApiMapper.to_dto(graph)


@router.get("/", response_model=list[GraphDTO], dependencies=_read)
def list_graphs(response: Response) -> list[GraphDTO]:
    response.headers["Cache-Control"] = "max-age=3600"
    return [GraphApiMapper.to_dto(g) for g in _graph_service.list_all()]


@router.delete("/{graph_id}", status_code=204, dependencies=_delete)
def delete_graph(graph_id: str) -> None:
    try:
        _graph_service.delete(graph_id)
    except GraphNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
