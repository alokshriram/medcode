"""Data types for parsed HL7 v2.x messages."""
from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class ParsedPatient:
    """Patient demographics from PID segment."""
    mrn: str
    name_family: str | None = None
    name_given: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None


@dataclass
class ParsedEncounter:
    """Encounter/visit information from PV1 segment."""
    visit_number: str
    encounter_type: str | None = None  # inpatient, outpatient, emergency, observation
    admit_datetime: datetime | None = None
    discharge_datetime: datetime | None = None
    attending_physician: str | None = None
    attending_physician_id: str | None = None
    hospital_service: str | None = None
    payer_identifier: str | None = None


@dataclass
class ParsedDiagnosis:
    """Diagnosis from DG1 segment."""
    set_id: int | None = None
    diagnosis_code: str | None = None
    diagnosis_description: str | None = None
    diagnosis_type: str | None = None  # admitting, working, final
    coding_method: str | None = None  # ICD-10-CM, etc.


@dataclass
class ParsedProcedure:
    """Procedure from PR1 segment."""
    set_id: int | None = None
    procedure_code: str | None = None
    procedure_description: str | None = None
    procedure_datetime: datetime | None = None
    performing_physician: str | None = None
    performing_physician_id: str | None = None


@dataclass
class ParsedObservation:
    """Clinical observation from OBX segment."""
    set_id: int | None = None
    observation_identifier: str | None = None
    observation_identifier_text: str | None = None
    observation_value: str | None = None
    units: str | None = None
    reference_range: str | None = None
    abnormal_flags: str | None = None
    observation_datetime: datetime | None = None
    result_status: str | None = None


@dataclass
class ParsedOrder:
    """Order information from ORC/OBR segments."""
    order_control: str | None = None
    placer_order_number: str | None = None
    filler_order_number: str | None = None
    order_status: str | None = None
    order_datetime: datetime | None = None
    ordering_provider: str | None = None
    ordering_provider_id: str | None = None
    order_type: str | None = None  # Universal Service ID text
    order_type_code: str | None = None  # Universal Service ID code
    diagnostic_service_section: str | None = None  # OBR-24


@dataclass
class ParsedDocument:
    """Document information from TXA/OBX in MDM messages."""
    document_type: str | None = None
    document_type_code: str | None = None
    document_status: str | None = None
    origination_datetime: datetime | None = None
    author: str | None = None
    author_id: str | None = None
    content: str | None = None


@dataclass
class ParsedHL7Message:
    """Complete parsed HL7 message with all extracted data."""
    # Message header info
    message_control_id: str
    message_type: str  # ADT, ORU, ORM, MDM, SIU
    event_type: str | None = None  # A01, A03, R01, etc.
    sending_application: str | None = None
    sending_facility: str | None = None
    message_datetime: datetime | None = None

    # Extracted clinical data
    patient: ParsedPatient | None = None
    encounter: ParsedEncounter | None = None
    diagnoses: list[ParsedDiagnosis] = field(default_factory=list)
    procedures: list[ParsedProcedure] = field(default_factory=list)
    observations: list[ParsedObservation] = field(default_factory=list)
    orders: list[ParsedOrder] = field(default_factory=list)
    documents: list[ParsedDocument] = field(default_factory=list)

    # Original message for audit
    raw_content: str = ""

    # Parsing metadata
    parse_errors: list[str] = field(default_factory=list)

    @property
    def is_discharge_event(self) -> bool:
        """Check if this message indicates a discharge."""
        # ADT^A03 is the standard discharge event
        # Also check A04 (registration), A08 (update), etc. don't trigger
        return self.message_type == "ADT" and self.event_type in ("A03", "A04")

    @property
    def has_patient(self) -> bool:
        return self.patient is not None and self.patient.mrn is not None

    @property
    def has_encounter(self) -> bool:
        return self.encounter is not None and self.encounter.visit_number is not None
