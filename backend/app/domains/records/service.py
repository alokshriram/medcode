from uuid import UUID

from sqlalchemy.orm import Session

from app.domains.records.models import MedicalRecord
from app.domains.records.schemas import MedicalRecordCreate, MedicalRecordUpdate


class RecordsService:
    def __init__(self, db: Session):
        self.db = db

    def get_records(self, skip: int = 0, limit: int = 100) -> list[MedicalRecord]:
        return self.db.query(MedicalRecord).offset(skip).limit(limit).all()

    def get_record(self, record_id: UUID) -> MedicalRecord | None:
        return self.db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()

    def get_records_by_patient(self, patient_id: str) -> list[MedicalRecord]:
        return self.db.query(MedicalRecord).filter(MedicalRecord.patient_id == patient_id).all()

    def create_record(self, record: MedicalRecordCreate, uploaded_by: UUID) -> MedicalRecord:
        db_record = MedicalRecord(**record.model_dump(), uploaded_by=uploaded_by)
        self.db.add(db_record)
        self.db.commit()
        self.db.refresh(db_record)
        return db_record

    def update_record(self, record_id: UUID, record: MedicalRecordUpdate) -> MedicalRecord | None:
        db_record = self.get_record(record_id)
        if not db_record:
            return None
        update_data = record.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_record, field, value)
        self.db.commit()
        self.db.refresh(db_record)
        return db_record

    def delete_record(self, record_id: UUID) -> bool:
        db_record = self.get_record(record_id)
        if not db_record:
            return False
        self.db.delete(db_record)
        self.db.commit()
        return True
