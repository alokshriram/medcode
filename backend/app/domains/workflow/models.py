import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class CodingTask(Base):
    __tablename__ = "coding_tasks"
    __table_args__ = {"schema": "workflow"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    priority: Mapped[int] = mapped_column(default=0)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CodingQueueItem(Base):
    """Work item for coding an encounter."""
    __tablename__ = "coding_queue_items"
    __table_args__ = {"schema": "workflow"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    billing_component: Mapped[str] = mapped_column(String(20), nullable=False)  # facility, professional
    queue_type: Mapped[str | None] = mapped_column(String(50))
    service_line: Mapped[str | None] = mapped_column(String(100), index=True)
    payer_identifier: Mapped[str | None] = mapped_column(String(100))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    snapshots: Mapped[list["EncounterSnapshot"]] = relationship("EncounterSnapshot", back_populates="queue_item")


class EncounterSnapshot(Base):
    """Point-in-time snapshot of encounter data for coding."""
    __tablename__ = "encounter_snapshots"
    __table_args__ = {"schema": "workflow"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    queue_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow.coding_queue_items.id"), nullable=False, index=True)
    snapshot_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    snapshot_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Relationships
    queue_item: Mapped["CodingQueueItem"] = relationship("CodingQueueItem", back_populates="snapshots")


class CodingConfiguration(Base):
    """System configuration for coding workflow."""
    __tablename__ = "coding_configuration"
    __table_args__ = {"schema": "workflow"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[dict[str, Any] | list | str | int | bool] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
