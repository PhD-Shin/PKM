"""
Weekly Review 관련 스키마
"""
from typing import List
from pydantic import BaseModel


class NewTopicOut(BaseModel):
    name: str
    mention_count: int
    first_seen: str


class ForgottenProjectOut(BaseModel):
    name: str
    status: str
    last_updated: str
    days_inactive: int


class OverdueTaskOut(BaseModel):
    id: str
    title: str
    priority: str
    note_title: str


class ActiveNoteOut(BaseModel):
    title: str
    path: str
    update_count: int


class WeeklyReviewResponse(BaseModel):
    new_topics: List[NewTopicOut]
    forgotten_projects: List[ForgottenProjectOut]
    overdue_tasks: List[OverdueTaskOut]
    most_active_notes: List[ActiveNoteOut]
