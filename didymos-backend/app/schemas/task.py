"""
Task 관련 Pydantic 스키마
"""
from typing import Optional
from pydantic import BaseModel


class TaskUpdate(BaseModel):
    status: Optional[str] = None  # todo/in_progress/done
    priority: Optional[str] = None  # low/medium/high


class TaskOut(BaseModel):
    id: str
    title: str
    status: str
    priority: str
    note_id: str
    note_title: str
