"""
GraphRAG 검색 API 라우터

Phase 12: neo4j-graphrag 기반 하이브리드 검색
Phase 14: ToolsRetriever (Agentic RAG)

엔드포인트:
- /search/vector: 순수 벡터 검색
- /search/hybrid: 벡터 + 그래프 컨텍스트
- /search/text2cypher: 자연어 → Cypher
- /search/agentic: LLM이 최적 retriever 자동 선택
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Literal
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    """검색 요청"""
    query: str
    mode: Literal["vector", "hybrid", "text2cypher", "agentic"] = "hybrid"
    top_k: int = 10
    vault_id: Optional[str] = None


class SearchResponse(BaseModel):
    """검색 응답"""
    status: str
    mode: str
    query: str
    results: list
    generated_cypher: Optional[str] = None


@router.post("", response_model=SearchResponse)
async def unified_search(request: SearchRequest):
    """
    통합 검색 API

    검색 모드:
    - vector: 순수 벡터 유사도 검색 (가장 빠름)
    - hybrid: 벡터 검색 + 그래프 컨텍스트 확장 (권장)
    - text2cypher: 자연어 질문을 Cypher로 변환
    - agentic: LLM이 질문을 분석하여 최적 retriever 자동 선택 (Phase 14)

    Args:
        query: 검색 쿼리
        mode: 검색 모드 (vector, hybrid, text2cypher, agentic)
        top_k: 반환할 결과 수 (text2cypher 제외)
        vault_id: 특정 Vault로 필터링 (선택)

    Returns:
        검색 결과
    """
    try:
        from app.services.graphrag_retriever import get_graphrag_service

        service = await get_graphrag_service()
        if service is None:
            raise HTTPException(
                status_code=503,
                detail="GraphRAG service not available. Install neo4j-graphrag package."
            )

        result = await service.search(
            query=request.query,
            mode=request.mode,
            top_k=request.top_k,
            vault_id=request.vault_id
        )

        return SearchResponse(
            status="success",
            mode=request.mode,
            query=request.query,
            results=result.get("results", []),
            generated_cypher=result.get("generated_cypher")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vector")
async def vector_search(
    query: str = Query(..., description="검색 쿼리"),
    top_k: int = Query(10, ge=1, le=100, description="반환할 결과 수"),
    vault_id: Optional[str] = Query(None, description="Vault ID 필터")
):
    """
    벡터 유사도 검색

    노트 임베딩을 기반으로 시맨틱 유사도 검색을 수행합니다.
    가장 빠르고 간단한 검색 방식입니다.
    """
    try:
        from app.services.graphrag_retriever import get_graphrag_service

        service = await get_graphrag_service()
        if service is None:
            raise HTTPException(
                status_code=503,
                detail="GraphRAG service not available"
            )

        results = await service.search_vector(
            query=query,
            top_k=top_k,
            vault_id=vault_id
        )

        return {
            "status": "success",
            "mode": "vector",
            "query": query,
            "count": len(results),
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hybrid")
async def hybrid_search(
    query: str = Query(..., description="검색 쿼리"),
    top_k: int = Query(10, ge=1, le=100, description="반환할 결과 수"),
    vault_id: Optional[str] = Query(None, description="Vault ID 필터")
):
    """
    하이브리드 검색 (벡터 + 그래프)

    벡터 검색으로 관련 노트를 찾은 후,
    그래프를 탐색하여 추가 컨텍스트를 제공합니다:
    - 노트가 언급하는 엔티티
    - SKOS 계층 관계 (BROADER/NARROWER)
    - 관련 엔티티

    권장 검색 모드입니다.
    """
    try:
        from app.services.graphrag_retriever import get_graphrag_service

        service = await get_graphrag_service()
        if service is None:
            raise HTTPException(
                status_code=503,
                detail="GraphRAG service not available"
            )

        results = await service.search_hybrid(
            query=query,
            top_k=top_k,
            vault_id=vault_id
        )

        return {
            "status": "success",
            "mode": "hybrid",
            "query": query,
            "count": len(results),
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/text2cypher")
async def text2cypher_search(
    query: str = Query(..., description="자연어 질문"),
    vault_id: Optional[str] = Query(None, description="Vault ID 필터")
):
    """
    자연어 → Cypher 검색

    자연어 질문을 Cypher 쿼리로 자동 변환하여 검색합니다.

    예시 질문:
    - "Machine Learning 관련 노트 찾아줘"
    - "Didymos 프로젝트의 할일 목록"
    - "최근 일주일간 수정된 노트"
    - "Transformer 주제의 상위 개념은?"

    생성된 Cypher 쿼리도 함께 반환됩니다.
    """
    try:
        from app.services.graphrag_retriever import get_graphrag_service

        service = await get_graphrag_service()
        if service is None:
            raise HTTPException(
                status_code=503,
                detail="GraphRAG service not available"
            )

        result = await service.search_text2cypher(
            query=query,
            vault_id=vault_id
        )

        return {
            "status": "success",
            "mode": "text2cypher",
            "query": result.get("query"),
            "generated_cypher": result.get("generated_cypher"),
            "count": len(result.get("results", [])),
            "results": result.get("results", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text2Cypher search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agentic")
async def agentic_search(
    query: str = Query(..., description="자연어 질문"),
    vault_id: Optional[str] = Query(None, description="Vault ID 필터")
):
    """
    Agentic RAG 검색 (Phase 14: ToolsRetriever)

    LLM이 질문을 분석하고 최적의 검색 전략을 자동 선택합니다.

    동작 방식:
    1. LLM이 질문의 특성을 분석
    2. 최적의 retriever 선택 (semantic, structured, hybrid)
    3. 선택 이유(reasoning)와 함께 결과 반환

    예시:
    - "Machine Learning 관련 노트" → semantic_search (벡터)
    - "우선순위 높은 태스크 목록" → structured_query (Cypher)
    - "Transformer 관련 노트와 그 주제들" → hybrid_search

    Note: ToolsRetriever가 없으면 hybrid 검색으로 fallback
    """
    try:
        from app.services.graphrag_retriever import get_graphrag_service

        service = await get_graphrag_service()
        if service is None:
            raise HTTPException(
                status_code=503,
                detail="GraphRAG service not available"
            )

        result = await service.search_agentic(
            query=query,
            vault_id=vault_id
        )

        return {
            "status": "success",
            "mode": result.get("mode", "agentic"),
            "query": query,
            "selected_retriever": result.get("selected_retriever"),
            "reasoning": result.get("reasoning"),
            "fallback": result.get("fallback", False),
            "count": len(result.get("results", [])),
            "results": result.get("results", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agentic search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def search_status():
    """
    검색 서비스 상태 확인
    """
    try:
        from app.services.graphrag_retriever import GRAPHRAG_AVAILABLE, get_graphrag_service

        if not GRAPHRAG_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "neo4j-graphrag package not installed",
                "available_modes": []
            }

        service = await get_graphrag_service()
        if service is None:
            return {
                "status": "error",
                "message": "Failed to initialize GraphRAG service",
                "available_modes": []
            }

        # Check ToolsRetriever availability
        from app.services.graphrag_retriever import TOOLS_RETRIEVER_AVAILABLE
        modes = ["vector", "hybrid", "text2cypher"]
        if TOOLS_RETRIEVER_AVAILABLE:
            modes.append("agentic")

        return {
            "status": "available",
            "message": "GraphRAG search service is ready",
            "available_modes": modes,
            "features": {
                "vector_search": "Semantic similarity search using note embeddings",
                "hybrid_search": "Vector search + graph context expansion",
                "text2cypher": "Natural language to Cypher query conversion",
                "agentic_search": "LLM automatically selects optimal retriever (Phase 14)"
            },
            "tools_retriever_available": TOOLS_RETRIEVER_AVAILABLE
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "available_modes": []
        }
