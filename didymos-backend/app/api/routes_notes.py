"""
Notes API 라우터
"""
from fastapi import APIRouter, HTTPException, status
from app.schemas.note import NoteSyncRequest, NoteSyncResponse
from app.schemas.context import NoteContextResponse
from app.db.neo4j import get_neo4j_client
from app.services.graph_service import upsert_note, get_note, get_all_notes
from app.services.graph_visualization_service import get_note_graph_vis
from app.services.ontology_service import process_note_to_graph
from app.services.context_service import get_note_context
from app.services.llm_client import summarize_content
from app.utils.cache import TTLCache
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notes", tags=["notes"])
context_cache = TTLCache(ttl_seconds=30)
graph_cache = TTLCache(ttl_seconds=30)


def get_user_id_from_token(token: str) -> str:
    """
    토큰에서 사용자 ID 추출
    MVP: 토큰 = user_id (실제로는 JWT 검증 필요)
    """
    return token


@router.post("/sync", response_model=NoteSyncResponse)
async def sync_note(payload: NoteSyncRequest):
    """
    노트 동기화 API

    User, Vault, Note 노드를 Neo4j에 생성/업데이트합니다.
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

        # AI 그래프 추출 실행 (content가 있는 경우에만)
        extracted_nodes = 0
        embedding_created = False
        content_for_ai = payload.note.content or ""
        if payload.privacy_mode == "summary":
            content_for_ai = summarize_content(content_for_ai)
        elif payload.privacy_mode == "metadata":
            content_for_ai = ""

        if content_for_ai:
            try:
                # 1. 엔티티 추출
                extracted_nodes = process_note_to_graph(
                    note_id=payload.note.note_id,
                    content=content_for_ai,
                    metadata={"tags": payload.note.tags}
                )
                logger.info(f"Extracted {extracted_nodes} entities from note")

                # 2. 임베딩 생성 및 저장
                from app.services.vector_service import store_note_embedding
                embedding_created = store_note_embedding(
                    note_id=payload.note.note_id,
                    content=content_for_ai,
                    metadata={"tags": payload.note.tags}
                )

            except Exception as e:
                logger.error(f"AI processing failed: {e}")
                # 추출 실패해도 노트 저장은 성공으로 처리

        # 캐시 무효화
        context_cache.clear(payload.note.note_id)
        graph_cache.clear_prefix(f"{payload.note.note_id}:")

        message_parts = [f"Note synced successfully"]
        if extracted_nodes > 0:
            message_parts.append(f"Extracted {extracted_nodes} entities")
        if embedding_created:
            message_parts.append("Embedding created")

        return NoteSyncResponse(
            status="success",
            note_id=payload.note.note_id,
            message=". ".join(message_parts) + ".",
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
async def list_notes(user_token: str, vault_id: str):
    """
    특정 Vault의 모든 노트 목록 조회
    """
    client = get_neo4j_client()
    user_id = get_user_id_from_token(user_token)

    notes = get_all_notes(client, user_id, vault_id)

    return {
        "user_id": user_id,
        "vault_id": vault_id,
        "count": len(notes),
        "notes": notes
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
