from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DbSession
from app.domains.workflow.schemas import CodingTaskCreate, CodingTaskResponse, CodingTaskUpdate
from app.domains.workflow.service import WorkflowService

router = APIRouter()


@router.get("/tasks", response_model=list[CodingTaskResponse])
def list_tasks(db: DbSession, current_user: CurrentUser, skip: int = 0, limit: int = 100):
    service = WorkflowService(db)
    return service.get_tasks(skip=skip, limit=limit)


@router.get("/tasks/{task_id}", response_model=CodingTaskResponse)
def get_task(task_id: UUID, db: DbSession, current_user: CurrentUser):
    service = WorkflowService(db)
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.post("/tasks", response_model=CodingTaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task: CodingTaskCreate, db: DbSession, current_user: CurrentUser):
    service = WorkflowService(db)
    return service.create_task(task, created_by=UUID(current_user.sub))


@router.patch("/tasks/{task_id}", response_model=CodingTaskResponse)
def update_task(task_id: UUID, task: CodingTaskUpdate, db: DbSession, current_user: CurrentUser):
    service = WorkflowService(db)
    updated_task = service.update_task(task_id, task)
    if not updated_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return updated_task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: UUID, db: DbSession, current_user: CurrentUser):
    service = WorkflowService(db)
    if not service.delete_task(task_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
