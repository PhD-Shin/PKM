"""
노트 동기화를 위한 Pydantic 스키마
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class NotePayload(BaseModel):
    """노트 데이터 페이로드"""
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
    """노트 동기화 요청"""
    user_token: str
    vault_id: str
    note: NotePayload
    privacy_mode: str = Field(default="full", description="full | summary | metadata")


class NoteSyncResponse(BaseModel):
    """노트 동기화 응답"""
    status: str
    note_id: str
    message: Optional[str] = None
