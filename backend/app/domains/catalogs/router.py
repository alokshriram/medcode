from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.domains.catalogs.schemas import (
    CodeSearchResponse,
    CPTCodeCreate,
    CPTCodeResponse,
    CPTCodeUpdate,
    ICD10CodeCreate,
    ICD10CodeResponse,
    ICD10CodeUpdate,
)
from app.domains.catalogs.service import CatalogsService

router = APIRouter()


# Search endpoint
@router.get("/search", response_model=CodeSearchResponse)
def search_codes(
    db: DbSession,
    current_user: CurrentUser,
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(25, ge=1, le=100),
):
    service = CatalogsService(db)
    return service.search_all_codes(q, limit=limit)


# ICD-10 endpoints
@router.get("/icd10", response_model=list[ICD10CodeResponse])
def list_icd10_codes(db: DbSession, current_user: CurrentUser, skip: int = 0, limit: int = 100):
    service = CatalogsService(db)
    return service.get_icd10_codes(skip=skip, limit=limit)


@router.get("/icd10/{code_id}", response_model=ICD10CodeResponse)
def get_icd10_code(code_id: UUID, db: DbSession, current_user: CurrentUser):
    service = CatalogsService(db)
    code = service.get_icd10_code(code_id)
    if not code:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ICD-10 code not found")
    return code


@router.get("/icd10/code/{code}", response_model=ICD10CodeResponse)
def get_icd10_by_code(code: str, db: DbSession, current_user: CurrentUser):
    service = CatalogsService(db)
    result = service.get_icd10_by_code(code)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ICD-10 code not found")
    return result


@router.post("/icd10", response_model=ICD10CodeResponse, status_code=status.HTTP_201_CREATED)
def create_icd10_code(code: ICD10CodeCreate, db: DbSession, current_user: CurrentUser):
    service = CatalogsService(db)
    return service.create_icd10_code(code)


@router.patch("/icd10/{code_id}", response_model=ICD10CodeResponse)
def update_icd10_code(code_id: UUID, code: ICD10CodeUpdate, db: DbSession, current_user: CurrentUser):
    service = CatalogsService(db)
    updated_code = service.update_icd10_code(code_id, code)
    if not updated_code:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ICD-10 code not found")
    return updated_code


# CPT endpoints
@router.get("/cpt", response_model=list[CPTCodeResponse])
def list_cpt_codes(db: DbSession, current_user: CurrentUser, skip: int = 0, limit: int = 100):
    service = CatalogsService(db)
    return service.get_cpt_codes(skip=skip, limit=limit)


@router.get("/cpt/{code_id}", response_model=CPTCodeResponse)
def get_cpt_code(code_id: UUID, db: DbSession, current_user: CurrentUser):
    service = CatalogsService(db)
    code = service.get_cpt_code(code_id)
    if not code:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CPT code not found")
    return code


@router.get("/cpt/code/{code}", response_model=CPTCodeResponse)
def get_cpt_by_code(code: str, db: DbSession, current_user: CurrentUser):
    service = CatalogsService(db)
    result = service.get_cpt_by_code(code)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CPT code not found")
    return result


@router.post("/cpt", response_model=CPTCodeResponse, status_code=status.HTTP_201_CREATED)
def create_cpt_code(code: CPTCodeCreate, db: DbSession, current_user: CurrentUser):
    service = CatalogsService(db)
    return service.create_cpt_code(code)


@router.patch("/cpt/{code_id}", response_model=CPTCodeResponse)
def update_cpt_code(code_id: UUID, code: CPTCodeUpdate, db: DbSession, current_user: CurrentUser):
    service = CatalogsService(db)
    updated_code = service.update_cpt_code(code_id, code)
    if not updated_code:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CPT code not found")
    return updated_code
