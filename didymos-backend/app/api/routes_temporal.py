"""
Temporal Knowledge Graph API 라우터

Graphiti 기반 시간 인식 지식 그래프 API
- 시간 범위 검색
- 지식 진화 추적
- 엔티티 요약 조회
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/temporal", tags=["temporal"])


class TemporalSearchRequest(BaseModel):
    """시간 기반 검색 요청"""
    query: str
    start_date: Optional[str] = None  # ISO format: 2024-01-01
    end_date: Optional[str] = None
    num_results: int = 10


class EvolutionResponse(BaseModel):
    """엔티티 진화 응답"""
    entity_name: str
    time_range: dict
    evolution: list
    total_changes: int


@router.post("/search")
async def temporal_search(request: TemporalSearchRequest):
    """
    시간 인식 하이브리드 검색

    Graphiti의 시맨틱 + BM25 + 그래프 순회 검색을 사용합니다.

    Args:
        query: 검색 쿼리
        start_date: 검색 시작 날짜 (ISO format)
        end_date: 검색 종료 날짜 (ISO format)
        num_results: 반환할 결과 수

    Returns:
        검색된 노드와 엣지 (시간 정보 포함)
    """
    if not settings.use_graphiti:
        raise HTTPException(
            status_code=400,
            detail="Graphiti is not enabled. Set USE_GRAPHITI=true in environment."
        )

    try:
        from app.services.graphiti_service import async_search

        result = await async_search(
            query=request.query,
            num_results=request.num_results
        )

        # 시간 필터링 (선택적)
        if request.start_date or request.end_date:
            start_dt = datetime.fromisoformat(request.start_date) if request.start_date else None
            end_dt = datetime.fromisoformat(request.end_date) if request.end_date else None

            # 엣지 필터링
            filtered_edges = []
            for edge in result.get("edges", []):
                valid_at = edge.get("valid_at")
                if valid_at:
                    valid_dt = datetime.fromisoformat(valid_at)
                    if start_dt and valid_dt < start_dt:
                        continue
                    if end_dt and valid_dt > end_dt:
                        continue
                filtered_edges.append(edge)

            result["edges"] = filtered_edges
            result["time_filter"] = {
                "start_date": request.start_date,
                "end_date": request.end_date
            }

        return result

    except Exception as e:
        logger.error(f"Temporal search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evolution/{entity_name}")
async def get_entity_evolution(
    entity_name: str,
    start_date: Optional[str] = Query(None, description="시작 날짜 (ISO format)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (ISO format)")
):
    """
    엔티티의 시간에 따른 변화 조회

    "2024년 1월에 내가 관심 있었던 주제는?" 같은 쿼리를 지원합니다.

    Args:
        entity_name: 엔티티 이름
        start_date: 시작 날짜 (ISO format)
        end_date: 종료 날짜 (ISO format)

    Returns:
        시간에 따른 관계 변화 정보
    """
    if not settings.use_graphiti:
        raise HTTPException(
            status_code=400,
            detail="Graphiti is not enabled. Set USE_GRAPHITI=true in environment."
        )

    try:
        from app.services.graphiti_service import async_get_temporal_evolution

        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        result = await async_get_temporal_evolution(
            entity_name=entity_name,
            start_date=start_dt,
            end_date=end_dt
        )

        return result

    except Exception as e:
        logger.error(f"Evolution query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_graphiti_status():
    """
    Graphiti 서비스 상태 확인

    Returns:
        Graphiti 활성화 상태 및 연결 정보
    """
    status_info = {
        "graphiti_enabled": settings.use_graphiti,
        "neo4j_uri": settings.neo4j_uri.split("@")[-1] if "@" in settings.neo4j_uri else settings.neo4j_uri,
    }

    if settings.use_graphiti:
        try:
            from app.services.graphiti_service import GraphitiService
            service = await GraphitiService.get_instance()
            status_info["connection"] = "connected"
            status_info["message"] = "Graphiti temporal knowledge graph is active"
        except Exception as e:
            status_info["connection"] = "error"
            status_info["error"] = str(e)
    else:
        status_info["message"] = "Using legacy LLMGraphTransformer. Enable Graphiti with USE_GRAPHITI=true"

    return status_info


@router.get("/insights/stale")
async def get_stale_knowledge(
    days: int = Query(30, ge=7, le=365, description="N일 이상 미접근 지식"),
    limit: int = Query(20, ge=1, le=100, description="반환할 최대 개수")
):
    """
    오래된 지식 리마인더

    N일 이상 업데이트/접근이 없는 엔티티를 조회합니다.
    "잊혀진 지식"을 다시 상기시켜 복습 기회를 제공합니다.

    Args:
        days: 미접근 기준 일수 (기본 30일)
        limit: 반환할 최대 개수

    Returns:
        오래된 지식 목록 (우선순위 순)
    """
    if not settings.use_graphiti:
        raise HTTPException(
            status_code=400,
            detail="Graphiti is not enabled. Set USE_GRAPHITI=true in environment."
        )

    try:
        from app.db.neo4j import get_neo4j_client
        from datetime import timedelta

        client = get_neo4j_client()
        cutoff_date = datetime.now() - timedelta(days=days)

        # Graphiti Entity 노드에서 오래된 것 조회
        # created_at 또는 last_accessed 기준
        cypher = """
        MATCH (e:Entity)
        WHERE e.created_at IS NOT NULL
          AND datetime(e.created_at) < datetime($cutoff_date)
        WITH e,
             duration.inDays(datetime(e.created_at), datetime()).days AS days_old,
             e.summary AS summary
        ORDER BY days_old DESC
        LIMIT $limit
        RETURN e.uuid AS uuid,
               e.name AS name,
               e.summary AS summary,
               e.created_at AS created_at,
               days_old
        """

        results = client.query(cypher, {
            "cutoff_date": cutoff_date.isoformat(),
            "limit": limit
        })

        stale_entities = []
        for record in results:
            stale_entities.append({
                "uuid": record.get("uuid"),
                "name": record.get("name"),
                "summary": record.get("summary"),
                "created_at": record.get("created_at"),
                "days_old": record.get("days_old"),
                "priority": "high" if record.get("days_old", 0) > 60 else "medium"
            })

        return {
            "status": "success",
            "criteria": {
                "min_days_old": days,
                "cutoff_date": cutoff_date.isoformat()
            },
            "stale_knowledge": stale_entities,
            "total_count": len(stale_entities),
            "message": f"{len(stale_entities)}개의 잊혀진 지식을 발견했습니다. 복습을 권장합니다!"
        }

    except Exception as e:
        logger.error(f"Stale knowledge query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/recent")
async def get_recent_knowledge_changes(
    days: int = Query(7, ge=1, le=90, description="최근 N일간의 변화")
):
    """
    최근 지식 변화 인사이트

    최근 N일간 추가되거나 변경된 엔티티/관계를 조회합니다.

    Args:
        days: 조회할 기간 (일)

    Returns:
        최근 변화된 지식 요약
    """
    if not settings.use_graphiti:
        raise HTTPException(
            status_code=400,
            detail="Graphiti is not enabled. Set USE_GRAPHITI=true in environment."
        )

    try:
        from app.services.graphiti_service import async_search
        from datetime import timedelta

        # 시간 범위 계산
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 최근 변화 검색 (빈 쿼리로 전체 검색 후 시간 필터)
        result = await async_search(
            query="",  # 모든 엔티티
            num_results=100
        )

        # 최근 생성된 엔티티 필터링
        recent_nodes = []
        for node in result.get("nodes", []):
            created_at = node.get("created_at")
            if created_at:
                try:
                    created_dt = datetime.fromisoformat(created_at)
                    if created_dt >= start_date:
                        recent_nodes.append(node)
                except:
                    pass

        # 최근 생성된 관계 필터링
        recent_edges = []
        for edge in result.get("edges", []):
            created_at = edge.get("created_at")
            if created_at:
                try:
                    created_dt = datetime.fromisoformat(created_at)
                    if created_dt >= start_date:
                        recent_edges.append(edge)
                except:
                    pass

        return {
            "status": "success",
            "time_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "new_entities": recent_nodes,
            "new_relationships": recent_edges,
            "summary": {
                "new_entities_count": len(recent_nodes),
                "new_relationships_count": len(recent_edges)
            }
        }

    except Exception as e:
        logger.error(f"Recent insights query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
