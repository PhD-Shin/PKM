"""
Context API 라우터 - 하이브리드 검색
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from app.services.vector_service import hybrid_search, vector_search, graph_search
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/context", tags=["context"])


class ContextResult(BaseModel):
    """컨텍스트 검색 결과"""
    note_id: str
    title: str
    path: str
    content: str
    tags: List[str]
    score: float
    source: str  # "vector", "graph", "hybrid"


class ContextResponse(BaseModel):
    """컨텍스트 검색 응답"""
    status: str
    query: Optional[str] = None
    note_id: Optional[str] = None
    count: int
    results: List[ContextResult]


@router.get("/search", response_model=ContextResponse)
async def search_context(
    query: Optional[str] = Query(None, description="검색 쿼리 (벡터 검색용)"),
    note_id: Optional[str] = Query(None, description="기준 노트 ID (그래프 검색용)"),
    k: int = Query(10, description="반환할 결과 개수", ge=1, le=50)
):
    """
    하이브리드 컨텍스트 검색

    - query: 텍스트 쿼리 → 벡터 유사도 검색
    - note_id: 노트 ID → 그래프 연결 검색
    - 둘 다 제공 시 → 하이브리드 검색 (벡터 + 그래프)
    """
    if not query and not note_id:
        raise HTTPException(
            status_code=400,
            detail="Either 'query' or 'note_id' must be provided"
        )

    try:
        results = hybrid_search(query=query, note_id=note_id, k=k)

        return ContextResponse(
            status="success",
            query=query,
            note_id=note_id,
            count=len(results),
            results=[ContextResult(**r) for r in results]
        )

    except Exception as e:
        logger.error(f"Context search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/vector", response_model=ContextResponse)
async def search_vector_only(
    query: str = Query(..., description="검색 쿼리"),
    k: int = Query(10, description="반환할 결과 개수", ge=1, le=50)
):
    """
    벡터 유사도 검색만 수행
    """
    try:
        results = vector_search(query=query, k=k)

        return ContextResponse(
            status="success",
            query=query,
            count=len(results),
            results=[ContextResult(**r) for r in results]
        )

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/graph", response_model=ContextResponse)
async def search_graph_only(
    note_id: str = Query(..., description="기준 노트 ID"),
    limit: int = Query(10, description="반환할 결과 개수", ge=1, le=50)
):
    """
    그래프 연결 검색만 수행
    """
    try:
        results = graph_search(note_id=note_id, limit=limit)

        return ContextResponse(
            status="success",
            note_id=note_id,
            count=len(results),
            results=[ContextResult(**r) for r in results]
        )

    except Exception as e:
        logger.error(f"Graph search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )
