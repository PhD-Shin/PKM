"""
Weekly Review API 라우터
"""
from fastapi import APIRouter, HTTPException, status
import logging

from app.db.neo4j import get_neo4j_client
from app.schemas import WeeklyReviewResponse, WeeklyReviewRecord
from app.services.review_service import (
    get_weekly_review,
    save_weekly_review,
    list_review_history,
)
from app.utils.cache import TTLCache
from app.utils.auth import get_user_id_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/review", tags=["review"])
review_cache = TTLCache(ttl_seconds=300)  # 5분으로 연장


@router.get("/weekly", response_model=WeeklyReviewResponse)
async def weekly_review(vault_id: str, user_token: str):
    """
    주간 리뷰 데이터 반환
    """
    try:
        client = get_neo4j_client()
        cached = review_cache.get(vault_id)
        if cached:
            return cached

        data = get_weekly_review(client, vault_id)
        resp = WeeklyReviewResponse(**data)
        review_cache.set(vault_id, resp)
        return resp
    except Exception as e:
        logger.error(f"Weekly review failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/weekly/save")
async def save_weekly(vault_id: str, user_token: str):
    """
    주간 리뷰 생성 후 히스토리에 저장
    """
    try:
        client = get_neo4j_client()
        data = get_weekly_review(client, vault_id)
        review_cache.set(vault_id, WeeklyReviewResponse(**data))
        review_id = save_weekly_review(client, vault_id, data)
        if not review_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save review",
            )
        return {"status": "ok", "review_id": review_id, "review": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save weekly review failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/history", response_model=list[WeeklyReviewRecord])
async def review_history(vault_id: str, user_token: str, limit: int = 5):
    """
    저장된 리뷰 히스토리 조회
    """
    try:
        client = get_neo4j_client()
        history = list_review_history(client, vault_id, limit=limit)
        return [WeeklyReviewRecord(**item) for item in history]
    except Exception as e:
        logger.error(f"List review history failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
