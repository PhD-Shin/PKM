"""
Weekly Review 히스토리 스키마
"""
from typing import List, Dict
from pydantic import BaseModel


class WeeklyReviewRecord(BaseModel):
    id: str
    vault_id: str
    created_at: str
    summary: Dict
