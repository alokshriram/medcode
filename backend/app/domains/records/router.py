from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DbSession
from app.domains.records.schemas import MedicalRecordCreate, MedicalRecordResponse, MedicalRecordUpdate
from app.domains.records.service import RecordsService

router = APIRouter()


@router.get("/", response_model=list[MedicalRecordResponse])
def list_records(db: DbSession, current_user: CurrentUser, skip: int = 0, limit: int = 100):
    service = RecordsService(db)
    return service.get_records(skip=skip, limit=limit)


@router.get("/{record_id}", response_model=MedicalRecordResponse)
def get_record(record_id: UUID, db: DbSession, current_user: CurrentUser):
    service = RecordsService(db)
    record = service.get_record(record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return record


@router.get("/patient/{patient_id}", response_model=list[MedicalRecordResponse])
def get_patient_records(patient_id: str, db: DbSession, current_user: CurrentUser):
    service = RecordsService(db)
    return service.get_records_by_patient(patient_id)


@router.post("/", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
def create_record(record: MedicalRecordCreate, db: DbSession, current_user: CurrentUser):
    service = RecordsService(db)
    return service.create_record(record, uploaded_by=UUID(current_user.sub))


@router.patch("/{record_id}", response_model=MedicalRecordResponse)
def update_record(record_id: UUID, record: MedicalRecordUpdate, db: DbSession, current_user: CurrentUser):
    service = RecordsService(db)
    updated_record = service.update_record(record_id, record)
    if not updated_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return updated_record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: UUID, db: DbSession, current_user: CurrentUser):
    service = RecordsService(db)
    if not service.delete_record(record_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
