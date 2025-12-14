from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CodingTaskBase(BaseModel):
    title: str
    description: str | None = None
    priority: int = 0
    due_date: datetime | None = None


class CodingTaskCreate(CodingTaskBase):
    assigned_to: UUID | None = None


class CodingTaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: int | None = None
    assigned_to: UUID | None = None
    due_date: datetime | None = None


class CodingTaskResponse(CodingTaskBase):
    id: UUID
    status: str
    assigned_to: UUID | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
