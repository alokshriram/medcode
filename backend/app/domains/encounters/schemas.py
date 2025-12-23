"""Pydantic schemas for the encounters domain."""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# --- Patient Schemas ---

class PatientBase(BaseModel):
    mrn: str
    name_family: str | None = None
    name_given: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None


class PatientCreate(PatientBase):
    pass


class PatientResponse(PatientBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Encounter Schemas ---

class EncounterBase(BaseModel):
    visit_number: str
    encounter_type: str | None = None
    service_line: str | None = None
    payer_identifier: str | None = None
    admit_datetime: datetime | None = None
    discharge_datetime: datetime | None = None
    admitting_diagnosis: str | None = None
    discharge_disposition: str | None = None


class EncounterCreate(EncounterBase):
    patient_id: UUID


class EncounterResponse(EncounterBase):
    id: UUID
    patient_id: UUID
    status: str
    ready_to_code_at: datetime | None = None
    ready_to_code_reason: str | None = None
    last_message_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EncounterWithPatientResponse(EncounterResponse):
    patient: PatientResponse


class EncounterListResponse(BaseModel):
    encounters: list[EncounterResponse]
    total: int
    skip: int
    limit: int


# --- Diagnosis Schemas ---

class DiagnosisBase(BaseModel):
    set_id: int | None = None
    diagnosis_code: str | None = None
    diagnosis_description: str | None = None
    diagnosis_type: str | None = None
    coding_method: str | None = None


class DiagnosisResponse(DiagnosisBase):
    id: UUID
    encounter_id: UUID
    hl7_message_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Procedure Schemas ---

class ProcedureBase(BaseModel):
    set_id: int | None = None
    procedure_code: str | None = None
    procedure_description: str | None = None
    procedure_datetime: datetime | None = None
    performing_physician: str | None = None
    performing_physician_id: str | None = None


class ProcedureResponse(ProcedureBase):
    id: UUID
    encounter_id: UUID
    hl7_message_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Observation Schemas ---

class ObservationBase(BaseModel):
    set_id: int | None = None
    observation_identifier: str | None = None
    observation_value: str | None = None
    units: str | None = None
    reference_range: str | None = None
    abnormal_flags: str | None = None
    observation_datetime: datetime | None = None
    result_status: str | None = None


class ObservationResponse(ObservationBase):
    id: UUID
    encounter_id: UUID
    hl7_message_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Order Schemas ---

class OrderBase(BaseModel):
    order_control: str | None = None
    placer_order_number: str | None = None
    filler_order_number: str | None = None
    order_status: str | None = None
    order_datetime: datetime | None = None
    ordering_provider: str | None = None
    order_type: str | None = None
    diagnostic_service_section: str | None = None


class OrderResponse(OrderBase):
    id: UUID
    encounter_id: UUID
    hl7_message_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Document Schemas ---

class DocumentBase(BaseModel):
    document_type: str | None = None
    document_status: str | None = None
    origination_datetime: datetime | None = None
    author: str | None = None
    content: str | None = None


class DocumentResponse(DocumentBase):
    id: UUID
    encounter_id: UUID
    hl7_message_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- HL7 Message Schemas ---

class HL7MessageBase(BaseModel):
    message_control_id: str
    message_type: str
    event_type: str | None = None
    file_source: str | None = None


class HL7MessageResponse(HL7MessageBase):
    id: UUID
    processing_status: str
    error_message: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Full Encounter Detail (with all related data) ---

class EncounterDetailResponse(EncounterResponse):
    patient: PatientResponse
    diagnoses: list[DiagnosisResponse] = []
    procedures: list[ProcedureResponse] = []
    observations: list[ObservationResponse] = []
    orders: list[OrderResponse] = []
    documents: list[DocumentResponse] = []


# --- Upload Schemas ---

class UploadJobCreate(BaseModel):
    """Request to upload HL7 files."""
    pass  # Files will be sent as multipart form data


class UploadJobStatus(BaseModel):
    """Status of an upload processing job."""
    job_id: str
    status: str  # pending, processing, completed, failed
    total_messages: int = 0
    processed_messages: int = 0
    failed_messages: int = 0
    errors: list[str] = []
    created_at: datetime
    completed_at: datetime | None = None


class UploadResult(BaseModel):
    """Result of uploading and processing HL7 files."""
    job_id: str
    files_received: int
    messages_found: int
    messages_processed: int
    messages_failed: int
    encounters_created: int
    encounters_updated: int
    errors: list[str] = []


# --- Ready to Code Schemas ---

class MarkReadyToCodeRequest(BaseModel):
    """Request to manually mark an encounter as ready to code."""
    reason: str = "manual_override"


# --- Service Line Rule Schemas ---

class ServiceLineRuleBase(BaseModel):
    rule_type: str
    match_pattern: str
    service_line: str
    priority: int = 100
    is_active: bool = True


class ServiceLineRuleCreate(ServiceLineRuleBase):
    pass


class ServiceLineRuleResponse(ServiceLineRuleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Filter Schemas ---

class EncounterFilters(BaseModel):
    """Filters for listing encounters."""
    status: str | None = None
    encounter_type: str | None = None
    service_line: str | None = None
    patient_mrn: str | None = None
    visit_number: str | None = None
    admit_date_from: datetime | None = None
    admit_date_to: datetime | None = None
