from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ICD10CodeBase(BaseModel):
    code: str
    description: str
    category: str | None = None
    subcategory: str | None = None
    is_billable: bool = True
    effective_date: datetime | None = None
    expiration_date: datetime | None = None


class ICD10CodeCreate(ICD10CodeBase):
    pass


class ICD10CodeUpdate(BaseModel):
    description: str | None = None
    category: str | None = None
    subcategory: str | None = None
    is_billable: bool | None = None
    effective_date: datetime | None = None
    expiration_date: datetime | None = None


class ICD10CodeResponse(ICD10CodeBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CPTCodeBase(BaseModel):
    code: str
    description: str
    long_description: str | None = None
    category: str | None = None
    subcategory: str | None = None
    effective_date: datetime | None = None
    expiration_date: datetime | None = None


class CPTCodeCreate(CPTCodeBase):
    pass


class CPTCodeUpdate(BaseModel):
    description: str | None = None
    long_description: str | None = None
    category: str | None = None
    subcategory: str | None = None
    effective_date: datetime | None = None
    expiration_date: datetime | None = None


class CPTCodeResponse(CPTCodeBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CodeSearchResponse(BaseModel):
    icd10_codes: list[ICD10CodeResponse]
    cpt_codes: list[CPTCodeResponse]
