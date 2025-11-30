"""
Task API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, status
from typing import Optional
import logging

from app.schemas.task import TaskUpdate, TaskOut
from app.db.neo4j import get_neo4j_client
from app.services.task_service import update_task, list_tasks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_user_id_from_token(token: str) -> str:
    return token


@router.put("/{task_id}")
async def update_task_endpoint(task_id: str, updates: TaskUpdate, user_token: str):
    """
    Task 업데이트 (status / priority)
    """
    try:
        client = get_neo4j_client()

        success = update_task(client, task_id, updates.model_dump(exclude_none=True))
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
            )

        return {"status": "ok", "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/list", response_model=list[TaskOut])
async def list_tasks_endpoint(
    vault_id: str,
    user_token: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
):
    """
    Task 목록 조회
    """
    try:
        client = get_neo4j_client()
        tasks = list_tasks(client, vault_id, status, priority)
        return tasks
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
