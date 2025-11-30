"""
Context 관련 Pydantic 스키마
"""
from typing import List
from pydantic import BaseModel


class TopicOut(BaseModel):
    id: str
    name: str
    importance_score: float = 0.0
    mention_count: int = 0


class ProjectOut(BaseModel):
    id: str
    name: str
    status: str = "unknown"
    updated_at: str = ""


class TaskOut(BaseModel):
    id: str
    title: str
    status: str = "unknown"
    priority: str = "normal"


class RelatedNoteOut(BaseModel):
    note_id: str
    title: str
    path: str
    similarity: float  # 0.0-1.0
    reason: str = "semantic"  # semantic(의미) or structural(구조)


class NoteContextResponse(BaseModel):
    topics: List[TopicOut]
    projects: List[ProjectOut]
    tasks: List[TaskOut]
    related_notes: List[RelatedNoteOut]
