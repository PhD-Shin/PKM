# Phase 2-1: Note Sync API (Backend)

> FastAPI ↔ Neo4j 파이프라인

**예상 시간**: 2~3시간  
**난이도**: ⭐⭐⭐⭐☆

---

## 목표

- 노트 데이터 스키마 정의 (Pydantic)
- `/notes/sync` API 구현
- Neo4j에 User, Vault, Note 저장
- Swagger로 E2E 확인

---

## Step 2-1: 스키마 정의

파일: `didymos-backend/app/schemas/note.py`

```python
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class NotePayload(BaseModel):
    note_id: str = Field(..., description="노트 ID (파일 경로)")
    title: str
    path: str
    content: Optional[str] = None
    yaml: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    links: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class NoteSyncRequest(BaseModel):
    user_token: str
    vault_id: str
    note: NotePayload


class NoteSyncResponse(BaseModel):
    status: str
    note_id: str
    message: Optional[str] = None
```

`app/schemas/__init__.py`
```python
from .note import NotePayload, NoteSyncRequest, NoteSyncResponse

__all__ = ["NotePayload", "NoteSyncRequest", "NoteSyncResponse"]
```

---

## Step 2-2: Neo4j 그래프 서비스

파일: `didymos-backend/app/services/graph_service.py`

```python
from neo4j import Driver
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def upsert_note(
    driver: Driver,
    user_id: str,
    vault_id: str,
    note_data: Dict[str, Any],
) -> bool:
    try:
        with driver.session() as session:
            result = session.run(
                """
                MERGE (u:User {id: $user_id})
                  ON CREATE SET u.created_at = datetime()

                MERGE (v:Vault {id: $vault_id})
                  ON CREATE SET v.created_at = datetime()
                MERGE (v)-[:OWNED_BY]->(u)

                MERGE (n:Note {note_id: $note_id})
                  ON CREATE SET 
                    n.title = $title,
                    n.path = $path,
                    n.created_at = datetime($created_at),
                    n.updated_at = datetime($updated_at),
                    n.tags = $tags
                  ON MATCH SET
                    n.title = $title,
                    n.path = $path,
                    n.updated_at = datetime($updated_at),
                    n.tags = $tags

                MERGE (v)-[:HAS_NOTE]->(n)
                RETURN n.note_id AS note_id
                """,
                user_id=user_id,
                vault_id=vault_id,
                note_id=note_data["note_id"],
                title=note_data["title"],
                path=note_data["path"],
                tags=note_data.get("tags", []),
                created_at=note_data["created_at"],
                updated_at=note_data["updated_at"],
            )

            record = result.single()
            if record:
                logger.info("✅ Note saved: %s", record["note_id"])
                return True
            return False

    except Exception as e:
        logger.error("Error saving note: %s", e)
        return False


def get_note(driver: Driver, note_id: str) -> Optional[Dict[str, Any]]:
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (n:Note {note_id: $note_id})
                RETURN n.note_id, n.title, n.path, n.tags, 
                       n.created_at, n.updated_at
                """,
                note_id=note_id,
            )
            record = result.single()
            return dict(record) if record else None
    except Exception as e:
        logger.error("Error fetching note: %s", e)
        return None
```

---

## Step 2-3: Notes API

파일: `didymos-backend/app/api/routes_notes.py`

```python
from fastapi import APIRouter, HTTPException, status
from app.schemas.note import NoteSyncRequest, NoteSyncResponse
from app.db.neo4j import get_neo4j_driver
from app.services.graph_service import upsert_note, get_note

router = APIRouter(prefix="/notes", tags=["notes"])


def get_user_id_from_token(token: str) -> str:
    return token  # MVP: 토큰 = user_id


@router.post("/sync", response_model=NoteSyncResponse)
async def sync_note(payload: NoteSyncRequest):
    try:
        driver = get_neo4j_driver()
        user_id = get_user_id_from_token(payload.user_token)

        success = upsert_note(
            driver=driver,
            user_id=user_id,
            vault_id=payload.vault_id,
            note_data=payload.note.dict(exclude_none=True),
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save note",
            )

        return NoteSyncResponse(
            status="success",
            note_id=payload.note.note_id,
            message="Note synced successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/get/{note_id}")
async def get_note_by_id(note_id: str):
    driver = get_neo4j_driver()
    note = get_note(driver, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note
```

`app/main.py`
```python
from app.api import routes_notes
app.include_router(routes_notes.router, prefix=settings.api_prefix)
```

---

## Step 2-4: Swagger 테스트

1. `uvicorn app.main:app --reload`
2. http://localhost:8000/docs 접속
3. `/api/v1/notes/sync` → “Try it out”
4. 예제 Payload 입력 후 Execute
5. Neo4j Browser에서 확인
```cypher
MATCH (u:User)-[:OWNS]->(v:Vault)-[:HAS_NOTE]->(n:Note)
RETURN u, v, n
```

---

## ✅ 체크리스트

- [ ] 스키마 (`app/schemas/note.py`) 작성
- [ ] Neo4j 서비스 (`app/services/graph_service.py`)
- [ ] `/notes/sync` API (FastAPI)
- [ ] Swagger로 동작 확인
- [ ] Neo4j에서 User/Vault/Note 생성 확인

---

**다음 단계**: [Phase 2-2: Obsidian 플러그인 (Frontend)](./phase-2-sync-frontend.md)

