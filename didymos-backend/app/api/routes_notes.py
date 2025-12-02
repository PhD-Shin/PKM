"""
Notes API 라우터
"""
from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks
from app.schemas.note import NoteSyncRequest, NoteSyncResponse
from app.schemas.context import NoteContextResponse
from app.db.neo4j import get_neo4j_client
from app.services.graph_service import upsert_note, get_note, get_all_notes
from app.services.graph_visualization_service import get_note_graph_vis
from app.services.ontology_service import process_note_to_graph
from app.services.context_service import get_note_context
from app.services.llm_client import summarize_content
from app.utils.cache import TTLCache
from app.utils.auth import get_user_id_from_token
from app.config import settings
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)

# Feature flag for Graphiti (controlled via settings or env)
USE_GRAPHITI = getattr(settings, 'use_graphiti', False)

# Rate limiting: 동시 AI 처리 제한 (OpenAI Rate Limit 방지)
_ai_semaphore = asyncio.Semaphore(2)  # 최대 2개 동시 처리
_AI_PROCESSING_DELAY = 1.0  # 처리 간 대기 시간 (초)

router = APIRouter(prefix="/notes", tags=["notes"])
context_cache = TTLCache(ttl_seconds=300)  # 5분으로 연장
graph_cache = TTLCache(ttl_seconds=300)  # 5분으로 연장


async def process_ai_in_background(
    note_id: str,
    content: str,
    tags: list,
    path: str,
    title: str,
    created_at: str,
    updated_at: str
):
    """
    백그라운드에서 AI 처리 (엔티티 추출 + 임베딩 생성)
    API 응답을 빠르게 반환하고 AI 작업은 비동기로 처리
    세마포어로 동시 처리 개수 제한 (OpenAI Rate Limit 방지)
    """
    async with _ai_semaphore:
        # Rate limiting: 처리 간 대기 시간
        await asyncio.sleep(_AI_PROCESSING_DELAY)

        try:
            logger.info(f"🔄 Background AI processing started for: {note_id[:50]}...")

            # 1. 엔티티 추출 (Hybrid Mode: Graphiti + PKM Labels)
            if USE_GRAPHITI:
                # Hybrid mode: Graphiti extracts EntityNode, then add PKM labels
                from app.services.hybrid_graphiti_service import process_note_hybrid
                note_updated_at = datetime.now()
                if updated_at:
                    try:
                        updated_str = updated_at.replace('Z', '+00:00')
                        note_updated_at = datetime.fromisoformat(updated_str)
                    except (ValueError, AttributeError):
                        pass

                hybrid_result = await process_note_hybrid(
                    note_id=note_id,
                    content=content,
                    updated_at=note_updated_at,
                    metadata={
                        "tags": tags,
                        "path": path,
                        "title": title,
                        "created_at": created_at
                    }
                )
                extracted_nodes = hybrid_result.get("nodes_extracted", 0)
                pkm_labels = hybrid_result.get("pkm_labels_added", 0)
                mentions = hybrid_result.get("mentions_created", 0)
                logger.info(f"✅ Hybrid mode: {extracted_nodes} entities, {pkm_labels} PKM labels, {mentions} MENTIONS")
            else:
                extracted_nodes = process_note_to_graph(
                    note_id=note_id,
                    content=content,
                    metadata={"tags": tags}
                )
                logger.info(f"✅ Extracted {extracted_nodes} entities from note")

            # 2. 임베딩 생성 및 저장
            from app.services.vector_service import store_note_embedding
            embedding_created = store_note_embedding(
                note_id=note_id,
                content=content,
                metadata={"tags": tags}
            )

            if embedding_created:
                logger.info(f"✅ Embedding created for note: {note_id[:50]}")

            # 캐시 무효화
            context_cache.clear(note_id)
            graph_cache.clear_prefix(f"{note_id}:")

        except Exception as e:
            logger.error(f"❌ Background AI processing failed for {note_id[:50]}: {e}", exc_info=True)


@router.post("/sync", response_model=NoteSyncResponse)
async def sync_note(payload: NoteSyncRequest, background_tasks: BackgroundTasks):
    """
    노트 동기화 API

    User, Vault, Note 노드를 Neo4j에 생성/업데이트합니다.
    AI 처리(엔티티 추출 + 임베딩)는 백그라운드에서 비동기로 실행됩니다.
    """
    try:
        client = get_neo4j_client()
        user_id = get_user_id_from_token(payload.user_token)

        success = upsert_note(
            client=client,
            user_id=user_id,
            vault_id=payload.vault_id,
            note_data=payload.note.model_dump(exclude_none=True),
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save note",
            )

        # AI 처리를 백그라운드 태스크로 실행 (content가 있는 경우에만)
        content_for_ai = payload.note.content or ""
        if payload.privacy_mode == "summary":
            content_for_ai = summarize_content(content_for_ai)
        elif payload.privacy_mode == "metadata":
            content_for_ai = ""

        ai_scheduled = False
        if content_for_ai:
            # 백그라운드에서 AI 처리 실행 (API는 즉시 응답)
            background_tasks.add_task(
                process_ai_in_background,
                note_id=payload.note.note_id,
                content=content_for_ai,
                tags=payload.note.tags or [],
                path=payload.note.path or "",
                title=payload.note.title or "",
                created_at=payload.note.created_at or "",
                updated_at=payload.note.updated_at or ""
            )
            ai_scheduled = True
            logger.info(f"📋 AI processing scheduled for: {payload.note.note_id[:50]}...")

        message = "Note synced successfully"
        if ai_scheduled:
            message += ". AI processing scheduled in background."

        return NoteSyncResponse(
            status="success",
            note_id=payload.note.note_id,
            message=message,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/get/{note_id}")
async def get_note_by_id(note_id: str):
    """
    노트 ID로 노트 조회
    """
    client = get_neo4j_client()
    note = get_note(client, note_id)

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    return note


@router.get("/list/{user_token}/{vault_id}")
async def list_notes(
    user_token: str,
    vault_id: str,
    limit: int = Query(50, ge=1, le=500, description="노트 수 제한"),
    offset: int = Query(0, ge=0, description="시작 위치")
):
    """
    특정 Vault의 노트 목록 조회 (페이지네이션)

    Args:
        limit: 반환할 노트 수 (기본 50, 최대 500)
        offset: 시작 인덱스 (페이지네이션용)
    """
    client = get_neo4j_client()
    user_id = get_user_id_from_token(user_token)

    # 전체 노트 조회 후 슬라이싱 (추후 DB 레벨 페이지네이션으로 개선 가능)
    all_notes = get_all_notes(client, user_id, vault_id)
    paginated_notes = all_notes[offset:offset + limit]

    return {
        "user_id": user_id,
        "vault_id": vault_id,
        "total": len(all_notes),
        "count": len(paginated_notes),
        "limit": limit,
        "offset": offset,
        "notes": paginated_notes
    }


@router.get("/context/{note_id:path}", response_model=NoteContextResponse)
async def get_context(note_id: str, user_token: str):
    """
    노트 컨텍스트 조회 (토픽/프로젝트/태스크 + 추천 노트)
    """
    try:
        cached = context_cache.get(note_id)
        if cached:
            return cached

        context = get_note_context(note_id=note_id, content_preview=note_id)
        context_obj = NoteContextResponse(**context)
        context_cache.set(note_id, context_obj)
        return context_obj
    except Exception as e:
        logger.error(f"Failed to get context for note {note_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get note context"
        )


@router.get("/graph/{note_id:path}")
async def get_note_graph(note_id: str, user_token: str, hops: int = 1):
    """
    노트 그래프 조회 (vis-network 형식)
    """
    try:
        cache_key = f"{note_id}:{hops}"
        cached = graph_cache.get(cache_key)
        if cached:
            return cached

        graph = get_note_graph_vis(note_id=note_id, hops=hops)
        graph_cache.set(cache_key, graph)
        return graph
    except Exception as e:
        logger.error(f"Failed to get graph for note {note_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get note graph"
        )
