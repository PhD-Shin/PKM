"""
Notes API Router
"""
from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks
from app.schemas.note import NoteSyncRequest, NoteSyncResponse
from app.schemas.context import NoteContextResponse
from app.db.neo4j import get_neo4j_client
from app.services.graph_service import get_note, get_all_notes
from app.services.note_service import note_service
from app.utils.auth import get_user_id_from_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("/sync", response_model=NoteSyncResponse)
async def sync_note(payload: NoteSyncRequest, background_tasks: BackgroundTasks):
    """
    Note Synchronization API
    Syncs User, Vault, Note nodes to Neo4j.
    AI processing (Entity extraction + embedding) runs in background.
    """
    try:
        user_id = get_user_id_from_token(payload.user_token)
        
        result = await note_service.sync_note(
            user_id=user_id,
            vault_id=payload.vault_id,
            note_data=payload.note.model_dump(exclude_none=True),
            privacy_mode=payload.privacy_mode,
            background_tasks=background_tasks
        )

        return NoteSyncResponse(**result)
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/get/{note_id}")
async def get_note_by_id(note_id: str):
    """
    Get note by ID
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
    limit: int = Query(50, ge=1, le=500, description="Limit"),
    offset: int = Query(0, ge=0, description="Offset")
):
    """
    List notes for a Vault (Pagination)
    """
    client = get_neo4j_client()
    user_id = get_user_id_from_token(user_token)

    # Note: DB-level pagination is better, but keeping existing logic for now
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
    Get note context (Topics/Projects/Tasks + Related Notes)
    """
    try:
        context = note_service.get_context(note_id)
        return NoteContextResponse(**context)
    except Exception as e:
        logger.error(f"Failed to get context for note {note_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get note context"
        )


@router.get("/graph/{note_id:path}")
async def get_note_graph(note_id: str, user_token: str, hops: int = 1):
    """
    Get note graph (vis-network format)
    """
    try:
        return note_service.get_graph(note_id, hops)
    except Exception as e:
        logger.error(f"Failed to get graph for note {note_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get note graph"
        )


@router.delete("/delete/{note_id:path}")
async def delete_note(
    note_id: str,
    user_token: str = Query(..., description="User token"),
    vault_id: str = Query(..., description="Vault ID")
):
    """
    Delete Note API
    """
    try:
        user_id = get_user_id_from_token(user_token)
        return note_service.delete_note(note_id, user_id)
    except Exception as e:
        logger.error(f"Failed to delete note {note_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete note: {str(e)}"
        )
