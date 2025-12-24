from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.dependencies import CurrentUser, DbSession
from app.domains.catalogs.service import CatalogsService
from app.domains.encounters.service import EncountersService
from app.domains.workflow.service import WorkflowService

router = APIRouter()


class DashboardResponse(BaseModel):
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks_today: int
    total_records: int


class TaskWithRecordsResponse(BaseModel):
    task_id: UUID
    task_title: str
    task_status: str
    associated_records: list[dict]


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: DbSession, current_user: CurrentUser):
    """
    Aggregates data from multiple domains for the dashboard view.
    BFF pattern: orchestrates calls to domain services without persistence.
    """
    workflow_service = WorkflowService(db)
    encounters_service = EncountersService(db)

    all_tasks = workflow_service.get_tasks()
    _, total_encounters = encounters_service.list_encounters()

    pending = sum(1 for t in all_tasks if t.status == "pending")
    in_progress = sum(1 for t in all_tasks if t.status == "in_progress")
    completed_today = sum(1 for t in all_tasks if t.status == "completed")

    return DashboardResponse(
        pending_tasks=pending,
        in_progress_tasks=in_progress,
        completed_tasks_today=completed_today,
        total_records=total_encounters,
    )


@router.get("/coding-workspace/{task_id}")
def get_coding_workspace(task_id: UUID, db: DbSession, current_user: CurrentUser):
    """
    Aggregates task details with associated records and code suggestions.
    Provides everything needed for the coding workspace in a single call.
    """
    workflow_service = WorkflowService(db)
    catalogs_service = CatalogsService(db)

    task = workflow_service.get_task(task_id)
    if not task:
        return {"error": "Task not found"}

    return {
        "task": {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
        },
        "recent_icd10_codes": [],
        "recent_cpt_codes": [],
    }
