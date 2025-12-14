from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MedicalRecordBase(BaseModel):
    patient_id: str
    document_type: str
    document_category: str | None = None


class MedicalRecordCreate(MedicalRecordBase):
    file_path: str
    file_name: str
    file_size: int
    mime_type: str


class MedicalRecordUpdate(BaseModel):
    document_type: str | None = None
    document_category: str | None = None
    summary: str | None = None
    processing_status: str | None = None


class MedicalRecordResponse(MedicalRecordBase):
    id: UUID
    file_path: str
    file_name: str
    file_size: int
    mime_type: str
    summary: str | None
    processing_status: str
    uploaded_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
