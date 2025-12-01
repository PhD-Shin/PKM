"""
패턴 분석 API 라우터
"""
from fastapi import APIRouter, HTTPException, Query
from app.services.pattern_service import analyze_vault_patterns
from app.services.recommendation_service import get_recommendations
from app.services.weakness_service import analyze_weaknesses
from app.utils.auth import get_user_id_from_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patterns", tags=["patterns"])


@router.get("/analyze/{user_token}/{vault_id}")
async def get_vault_patterns(user_token: str, vault_id: str):
    """
    Vault 패턴 분석

    Returns:
        - important_notes: PageRank 기반 중요 노트
        - communities: 노트 클러스터
        - orphan_notes: 고립된 노트
        - stats: 통계 정보
    """
    try:
        user_id = get_user_id_from_token(user_token)

        patterns = analyze_vault_patterns(user_id, vault_id)

        return {
            "status": "success",
            "user_id": user_id,
            "vault_id": vault_id,
            "patterns": patterns
        }

    except Exception as e:
        logger.error(f"Pattern analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze patterns: {str(e)}"
        )


@router.get("/recommendations/{user_token}/{vault_id}")
async def get_vault_recommendations(
    user_token: str,
    vault_id: str,
    note_id: str = Query(None, description="특정 노트에 대한 추천")
):
    """
    의사결정 추천

    Returns:
        - suggested_connections: 연결 제안 (note_id가 있을 때)
        - priority_tasks: 우선순위 Task
        - missing_connections: 놓친 연결
    """
    try:
        user_id = get_user_id_from_token(user_token)

        recommendations = get_recommendations(
            user_id=user_id,
            vault_id=vault_id,
            note_id=note_id
        )

        return {
            "status": "success",
            "user_id": user_id,
            "vault_id": vault_id,
            "note_id": note_id,
            "recommendations": recommendations
        }

    except Exception as e:
        logger.error(f"Recommendations failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


@router.get("/weaknesses/{user_token}/{vault_id}")
async def get_vault_weaknesses(user_token: str, vault_id: str):
    """
    약점 분석
    "The chain is only as strong as its weakest link" 원칙

    Returns:
        - weaknesses: 카테고리별 약점 (isolated_topics, stale_projects, chronic_overdue_tasks, weak_clusters, knowledge_gaps)
        - total_weakness_score: 전체 약점 점수
        - critical_weakness: 가장 심각한 약점
        - strengthening_plan: 보완 계획
    """
    try:
        user_id = get_user_id_from_token(user_token)

        weakness_analysis = analyze_weaknesses(user_id, vault_id)

        return {
            "status": "success",
            "user_id": user_id,
            "vault_id": vault_id,
            "weakness_analysis": weakness_analysis
        }

    except Exception as e:
        logger.error(f"Weakness analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze weaknesses: {str(e)}"
        )
