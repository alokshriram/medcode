from uuid import UUID

from sqlalchemy.orm import Session

from app.domains.workflow.models import CodingTask
from app.domains.workflow.schemas import CodingTaskCreate, CodingTaskUpdate


class WorkflowService:
    def __init__(self, db: Session):
        self.db = db

    def get_tasks(self, skip: int = 0, limit: int = 100) -> list[CodingTask]:
        return self.db.query(CodingTask).offset(skip).limit(limit).all()

    def get_task(self, task_id: UUID) -> CodingTask | None:
        return self.db.query(CodingTask).filter(CodingTask.id == task_id).first()

    def create_task(self, task: CodingTaskCreate, created_by: UUID) -> CodingTask:
        db_task = CodingTask(**task.model_dump(), created_by=created_by)
        self.db.add(db_task)
        self.db.commit()
        self.db.refresh(db_task)
        return db_task

    def update_task(self, task_id: UUID, task: CodingTaskUpdate) -> CodingTask | None:
        db_task = self.get_task(task_id)
        if not db_task:
            return None
        update_data = task.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_task, field, value)
        self.db.commit()
        self.db.refresh(db_task)
        return db_task

    def delete_task(self, task_id: UUID) -> bool:
        db_task = self.get_task(task_id)
        if not db_task:
            return False
        self.db.delete(db_task)
        self.db.commit()
        return True
