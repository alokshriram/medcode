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


# --- Coding Queue Schemas ---


class CodingQueueItemResponse(BaseModel):
    """Response schema for a coding queue item."""
    id: UUID
    tenant_id: UUID | None
    encounter_id: UUID
    billing_component: str  # "facility" or "professional"
    queue_type: str | None
    service_line: str | None
    payer_identifier: str | None
    priority: int
    status: str
    assigned_to: UUID | None
    assigned_at: datetime | None
    completed_at: datetime | None
    completed_by: UUID | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CodingQueueItemWithPatient(CodingQueueItemResponse):
    """Queue item with patient info for list display."""
    patient_name: str | None
    patient_mrn: str | None
    visit_number: str
    encounter_type: str | None


class CodingQueueListResponse(BaseModel):
    """Paginated list of coding queue items."""
    items: list[CodingQueueItemWithPatient]
    total: int
    skip: int
    limit: int


class SnapshotPatient(BaseModel):
    """Patient data in snapshot."""
    id: str | None
    mrn: str | None
    name_family: str | None
    name_given: str | None
    date_of_birth: str | None
    gender: str | None


class SnapshotEncounter(BaseModel):
    """Encounter data in snapshot."""
    id: str
    visit_number: str | None
    encounter_type: str | None
    service_line: str | None
    payer_identifier: str | None
    admit_datetime: str | None
    discharge_datetime: str | None
    admitting_diagnosis: str | None
    discharge_disposition: str | None
    status: str | None
    ready_to_code_at: str | None
    ready_to_code_reason: str | None


class SnapshotDiagnosis(BaseModel):
    """Diagnosis data in snapshot."""
    id: str
    set_id: int | None = None
    diagnosis_code: str | None
    diagnosis_description: str | None
    diagnosis_type: str | None
    coding_method: str | None


class SnapshotProcedure(BaseModel):
    """Procedure data in snapshot."""
    id: str
    set_id: int | None = None
    procedure_code: str | None
    procedure_description: str | None
    procedure_datetime: str | None
    performing_physician: str | None
    performing_physician_id: str | None


class SnapshotObservation(BaseModel):
    """Observation data in snapshot."""
    id: str
    set_id: int | None = None
    observation_identifier: str | None
    observation_value: str | None
    units: str | None
    reference_range: str | None
    abnormal_flags: str | None
    observation_datetime: str | None
    result_status: str | None


class SnapshotOrder(BaseModel):
    """Order data in snapshot."""
    id: str
    order_control: str | None
    placer_order_number: str | None
    filler_order_number: str | None
    order_status: str | None
    order_datetime: str | None
    ordering_provider: str | None
    order_type: str | None
    diagnostic_service_section: str | None


class SnapshotDocument(BaseModel):
    """Document data in snapshot."""
    id: str
    document_type: str | None
    document_status: str | None
    origination_datetime: str | None
    author: str | None
    content: str | None


class SnapshotDataResponse(BaseModel):
    """Full snapshot data for coding workbench."""
    snapshot_created_at: str
    patient: SnapshotPatient
    encounter: SnapshotEncounter
    diagnoses: list[SnapshotDiagnosis]
    procedures: list[SnapshotProcedure]
    observations: list[SnapshotObservation]
    orders: list[SnapshotOrder]
    documents: list[SnapshotDocument]


class CodingQueueItemDetailResponse(CodingQueueItemResponse):
    """Queue item with snapshot for coding workbench."""
    snapshot: SnapshotDataResponse | None
    snapshot_version: int | None


class AssignQueueItemRequest(BaseModel):
    """Request to assign a queue item."""
    user_id: UUID | None = None  # If None, assign to current user


# --- Coding Result Schemas ---


class DiagnosisCodeEntry(BaseModel):
    """A diagnosis code entered by a coder."""
    code: str
    description: str
    is_principal: bool = False
    poa_indicator: str | None = None  # Y, N, U, W, or 1 (exempt)
    sequence: int


class ProcedureCodeEntry(BaseModel):
    """A procedure code entered by a coder."""
    code: str
    description: str
    code_type: str  # "ICD-10-PCS" or "CPT"
    is_principal: bool = False
    sequence: int
    procedure_date: datetime | None = None


class SaveCodingResultsRequest(BaseModel):
    """Request to save coding results."""
    diagnosis_codes: list[DiagnosisCodeEntry]
    procedure_codes: list[ProcedureCodeEntry]


class CodingResultResponse(BaseModel):
    """Response for a single coding result."""
    id: UUID
    queue_item_id: UUID
    code: str
    code_type: str
    description: str
    code_category: str  # "diagnosis" or "procedure"
    is_principal: bool
    poa_indicator: str | None
    sequence: int
    procedure_date: datetime | None
    coded_by: UUID
    coded_at: datetime

    class Config:
        from_attributes = True


class CodingResultsResponse(BaseModel):
    """Response containing all coding results for a queue item."""
    queue_item_id: UUID
    diagnosis_codes: list[CodingResultResponse]
    procedure_codes: list[CodingResultResponse]
