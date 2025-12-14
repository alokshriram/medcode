from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.domains.catalogs.models import CPTCode, ICD10Code
from app.domains.catalogs.schemas import CPTCodeCreate, CPTCodeUpdate, ICD10CodeCreate, ICD10CodeUpdate


class CatalogsService:
    def __init__(self, db: Session):
        self.db = db

    # ICD-10 methods
    def get_icd10_codes(self, skip: int = 0, limit: int = 100) -> list[ICD10Code]:
        return self.db.query(ICD10Code).offset(skip).limit(limit).all()

    def get_icd10_code(self, code_id: UUID) -> ICD10Code | None:
        return self.db.query(ICD10Code).filter(ICD10Code.id == code_id).first()

    def get_icd10_by_code(self, code: str) -> ICD10Code | None:
        return self.db.query(ICD10Code).filter(ICD10Code.code == code).first()

    def search_icd10_codes(self, query: str, limit: int = 50) -> list[ICD10Code]:
        search_pattern = f"%{query}%"
        return (
            self.db.query(ICD10Code)
            .filter(or_(ICD10Code.code.ilike(search_pattern), ICD10Code.description.ilike(search_pattern)))
            .limit(limit)
            .all()
        )

    def create_icd10_code(self, code: ICD10CodeCreate) -> ICD10Code:
        db_code = ICD10Code(**code.model_dump())
        self.db.add(db_code)
        self.db.commit()
        self.db.refresh(db_code)
        return db_code

    def update_icd10_code(self, code_id: UUID, code: ICD10CodeUpdate) -> ICD10Code | None:
        db_code = self.get_icd10_code(code_id)
        if not db_code:
            return None
        update_data = code.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_code, field, value)
        self.db.commit()
        self.db.refresh(db_code)
        return db_code

    # CPT methods
    def get_cpt_codes(self, skip: int = 0, limit: int = 100) -> list[CPTCode]:
        return self.db.query(CPTCode).offset(skip).limit(limit).all()

    def get_cpt_code(self, code_id: UUID) -> CPTCode | None:
        return self.db.query(CPTCode).filter(CPTCode.id == code_id).first()

    def get_cpt_by_code(self, code: str) -> CPTCode | None:
        return self.db.query(CPTCode).filter(CPTCode.code == code).first()

    def search_cpt_codes(self, query: str, limit: int = 50) -> list[CPTCode]:
        search_pattern = f"%{query}%"
        return (
            self.db.query(CPTCode)
            .filter(or_(CPTCode.code.ilike(search_pattern), CPTCode.description.ilike(search_pattern)))
            .limit(limit)
            .all()
        )

    def create_cpt_code(self, code: CPTCodeCreate) -> CPTCode:
        db_code = CPTCode(**code.model_dump())
        self.db.add(db_code)
        self.db.commit()
        self.db.refresh(db_code)
        return db_code

    def update_cpt_code(self, code_id: UUID, code: CPTCodeUpdate) -> CPTCode | None:
        db_code = self.get_cpt_code(code_id)
        if not db_code:
            return None
        update_data = code.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_code, field, value)
        self.db.commit()
        self.db.refresh(db_code)
        return db_code

    # Combined search
    def search_all_codes(self, query: str, limit: int = 25) -> dict:
        icd10_results = self.search_icd10_codes(query, limit=limit)
        cpt_results = self.search_cpt_codes(query, limit=limit)
        return {"icd10_codes": icd10_results, "cpt_codes": cpt_results}
