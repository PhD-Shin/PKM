"""
Graph Visualization API 라우터
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.services.graph_visualization_service import (
    get_note_graph,
    get_note_graph_vis,
    get_user_graph,
    get_entity_graph
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])


class GraphNode(BaseModel):
    """그래프 노드"""
    id: str
    label: str
    type: str
    properties: Dict[str, Any]


class GraphEdge(BaseModel):
    """그래프 엣지"""
    from_: str = None  # Use alias to avoid 'from' keyword
    to: str
    type: str
    label: str

    class Config:
        fields = {'from_': 'from'}


class GraphResponse(BaseModel):
    """그래프 응답"""
    status: str
    count_nodes: int
    count_edges: int
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


@router.get("/note/{note_id}", response_model=GraphResponse)
async def get_note_graph_view(
    note_id: str,
    depth: int = Query(1, description="탐색 깊이", ge=1, le=3)
):
    """
    특정 노트 중심의 그래프 시각화 데이터

    - note_id: 중심 노트 ID
    - depth: 탐색 깊이 (1~3)
    """
    try:
        graph_data = get_note_graph_vis(note_id=note_id, hops=depth)

        return GraphResponse(
            status="success",
            count_nodes=len(graph_data["nodes"]),
            count_edges=len(graph_data["edges"]),
            nodes=graph_data["nodes"],
            edges=graph_data["edges"]
        )

    except Exception as e:
        logger.error(f"Failed to get note graph: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve graph: {str(e)}"
        )


@router.get("/user/{user_id}", response_model=GraphResponse)
async def get_user_graph_view(
    user_id: str,
    vault_id: Optional[str] = Query(None, description="Vault ID (optional)"),
    limit: int = Query(100, description="최대 노드 개수", ge=10, le=500)
):
    """
    사용자의 전체 지식 그래프

    - user_id: 사용자 ID
    - vault_id: Vault ID (optional)
    - limit: 최대 노드 개수 (기본 100, 최대 5000)
    """
    try:
        graph_data = get_user_graph(
            user_id=user_id,
            vault_id=vault_id,
            limit=limit
        )

        return GraphResponse(
            status="success",
            count_nodes=len(graph_data["nodes"]),
            count_edges=len(graph_data["edges"]),
            nodes=graph_data["nodes"],
            edges=graph_data["edges"]
        )

    except Exception as e:
        logger.error(f"Failed to get user graph: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve graph: {str(e)}"
        )


@router.get("/entities", response_model=GraphResponse)
async def get_entities_graph_view(
    entity_type: Optional[str] = Query(None, description="엔티티 타입 (Topic, Project, Task, Person)"),
    limit: int = Query(50, description="최대 엔티티 개수", ge=10, le=200)
):
    """
    엔티티 중심 그래프

    - entity_type: 필터링할 엔티티 타입 (optional)
    - limit: 최대 엔티티 개수
    """
    try:
        graph_data = get_entity_graph(
            entity_type=entity_type,
            limit=limit
        )

        return GraphResponse(
            status="success",
            count_nodes=len(graph_data["nodes"]),
            count_edges=len(graph_data["edges"]),
            nodes=graph_data["nodes"],
            edges=graph_data["edges"]
        )

    except Exception as e:
        logger.error(f"Failed to get entity graph: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve graph: {str(e)}"
        )
