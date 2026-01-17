"""API routes for the coding queue."""
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DbSession, OptionalTenantContextDep
from app.domains.workflow.coding_queue_service import CodingQueueService
from app.domains.workflow.schemas import (
    AssignQueueItemRequest,
    CodingQueueItemDetailResponse,
    CodingQueueItemResponse,
    CodingQueueListResponse,
    CodingQueueItemWithPatient,
    CodingResultResponse,
    CodingResultsResponse,
    SaveCodingResultsRequest,
    SnapshotDataResponse,
)

router = APIRouter()


@router.get("/queue", response_model=CodingQueueListResponse)
def list_queue_items(
    db: DbSession,
    current_user: CurrentUser,
    tenant_context: OptionalTenantContextDep,
    status: str | None = Query(None, description="Filter by status (pending, in_progress, completed)"),
    billing_component: str | None = Query(None, description="Filter: facility or professional"),
    service_line: str | None = Query(None, description="Filter by service line"),
    assigned_to_me: bool = Query(False, description="Show only items assigned to current user"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """
    List coding queue items with optional filters.

    Returns queue items with patient information for display in the work list.
    """
    service = CodingQueueService(db)

    assigned_to = UUID(current_user.sub) if assigned_to_me else None
    tenant_id = tenant_context.tenant_id if tenant_context else None

    items, total = service.list_queue_items_with_patient(
        status=status,
        billing_component=billing_component,
        service_line=service_line,
        assigned_to=assigned_to,
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
    )

    return CodingQueueListResponse(
        items=[CodingQueueItemWithPatient(**item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/queue/{item_id}", response_model=CodingQueueItemDetailResponse)
def get_queue_item(
    item_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    tenant_context: OptionalTenantContextDep,
):
    """
    Get a single queue item with its latest snapshot for coding.

    Returns the queue item with all snapshot data needed for the coding workbench.
    """
    service = CodingQueueService(db)

    item = service.get_queue_item(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")

    # Check tenant access
    if tenant_context and item.tenant_id and item.tenant_id != tenant_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")

    snapshot = service.get_latest_snapshot(item_id)

    snapshot_response = None
    snapshot_version = None
    if snapshot:
        snapshot_response = SnapshotDataResponse(**snapshot.snapshot_data)
        snapshot_version = snapshot.snapshot_version

    return CodingQueueItemDetailResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        encounter_id=item.encounter_id,
        billing_component=item.billing_component,
        queue_type=item.queue_type,
        service_line=item.service_line,
        payer_identifier=item.payer_identifier,
        priority=item.priority,
        status=item.status,
        assigned_to=item.assigned_to,
        assigned_at=item.assigned_at,
        completed_at=item.completed_at,
        completed_by=item.completed_by,
        created_at=item.created_at,
        updated_at=item.updated_at,
        snapshot=snapshot_response,
        snapshot_version=snapshot_version,
    )


@router.post("/queue/{item_id}/assign", response_model=CodingQueueItemResponse)
def assign_queue_item(
    item_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    tenant_context: OptionalTenantContextDep,
    request: AssignQueueItemRequest | None = None,
):
    """
    Assign a queue item to a user.

    If no user_id is provided in the request, assigns to the current user.
    """
    service = CodingQueueService(db)

    # Check item exists and tenant access
    existing = service.get_queue_item(item_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")
    if tenant_context and existing.tenant_id and existing.tenant_id != tenant_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")

    user_id = (request.user_id if request and request.user_id else None) or UUID(current_user.sub)
    item = service.assign_queue_item(item_id, user_id)

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")

    return item


@router.post("/queue/{item_id}/complete", response_model=CodingQueueItemResponse)
def complete_queue_item(
    item_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    tenant_context: OptionalTenantContextDep,
):
    """
    Mark a queue item as completed.
    """
    service = CodingQueueService(db)

    # Check item exists and tenant access
    existing = service.get_queue_item(item_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")
    if tenant_context and existing.tenant_id and existing.tenant_id != tenant_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")

    item = service.complete_queue_item(item_id, UUID(current_user.sub))

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")

    return item


@router.post("/queue/{item_id}/refresh-snapshot", response_model=CodingQueueItemDetailResponse)
def refresh_snapshot(
    item_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    tenant_context: OptionalTenantContextDep,
):
    """
    Refresh the snapshot with latest encounter data.

    Creates a new snapshot version with current encounter data.
    """
    service = CodingQueueService(db)

    item = service.get_queue_item(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")
    if tenant_context and item.tenant_id and item.tenant_id != tenant_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")

    snapshot = service.refresh_snapshot(item_id, UUID(current_user.sub))

    snapshot_response = None
    snapshot_version = None
    if snapshot:
        snapshot_response = SnapshotDataResponse(**snapshot.snapshot_data)
        snapshot_version = snapshot.snapshot_version

    return CodingQueueItemDetailResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        encounter_id=item.encounter_id,
        billing_component=item.billing_component,
        queue_type=item.queue_type,
        service_line=item.service_line,
        payer_identifier=item.payer_identifier,
        priority=item.priority,
        status=item.status,
        assigned_to=item.assigned_to,
        assigned_at=item.assigned_at,
        completed_at=item.completed_at,
        completed_by=item.completed_by,
        created_at=item.created_at,
        updated_at=item.updated_at,
        snapshot=snapshot_response,
        snapshot_version=snapshot_version,
    )


@router.get("/queue/{item_id}/codes", response_model=CodingResultsResponse)
def get_coding_results(
    item_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    tenant_context: OptionalTenantContextDep,
):
    """
    Get all coding results for a queue item.
    """
    service = CodingQueueService(db)

    # Check item exists and tenant access
    item = service.get_queue_item(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")
    if tenant_context and item.tenant_id and item.tenant_id != tenant_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")

    results = service.get_coding_results(item_id)

    diagnosis_codes = [r for r in results if r.code_category == "diagnosis"]
    procedure_codes = [r for r in results if r.code_category == "procedure"]

    return CodingResultsResponse(
        queue_item_id=item_id,
        diagnosis_codes=[CodingResultResponse.model_validate(r) for r in diagnosis_codes],
        procedure_codes=[CodingResultResponse.model_validate(r) for r in procedure_codes],
    )


@router.post("/queue/{item_id}/codes", response_model=CodingResultsResponse)
def save_coding_results(
    item_id: UUID,
    request: SaveCodingResultsRequest,
    db: DbSession,
    current_user: CurrentUser,
    tenant_context: OptionalTenantContextDep,
):
    """
    Save coding results for a queue item.

    Replaces all existing codes with the provided codes.
    """
    service = CodingQueueService(db)

    # Check item exists and tenant access
    item = service.get_queue_item(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")
    if tenant_context and item.tenant_id and item.tenant_id != tenant_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")

    tenant_id = tenant_context.tenant_id if tenant_context else None

    # Convert Pydantic models to dicts
    diagnosis_dicts = [
        {
            "code": dx.code,
            "description": dx.description,
            "is_principal": dx.is_principal,
            "poa_indicator": dx.poa_indicator,
            "sequence": dx.sequence,
        }
        for dx in request.diagnosis_codes
    ]
    procedure_dicts = [
        {
            "code": px.code,
            "description": px.description,
            "code_type": px.code_type,
            "is_principal": px.is_principal,
            "sequence": px.sequence,
            "procedure_date": px.procedure_date,
        }
        for px in request.procedure_codes
    ]

    results = service.save_coding_results(
        queue_item_id=item_id,
        diagnosis_codes=diagnosis_dicts,
        procedure_codes=procedure_dicts,
        coded_by=UUID(current_user.sub),
        tenant_id=tenant_id,
    )

    diagnosis_results = [r for r in results if r.code_category == "diagnosis"]
    procedure_results = [r for r in results if r.code_category == "procedure"]

    return CodingResultsResponse(
        queue_item_id=item_id,
        diagnosis_codes=[CodingResultResponse.model_validate(r) for r in diagnosis_results],
        procedure_codes=[CodingResultResponse.model_validate(r) for r in procedure_results],
    )
