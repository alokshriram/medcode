import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class HL7Message(Base):
    """Raw HL7 message storage for audit and debugging."""
    __tablename__ = "hl7_messages"
    __table_args__ = {"schema": "encounters"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    message_control_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    message_type: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    event_type: Mapped[str | None] = mapped_column(String(10))
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    file_source: Mapped[str | None] = mapped_column(String(500))
    processing_status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Patient(Base):
    """Patient demographics extracted from HL7 PID segments."""
    __tablename__ = "patients"
    __table_args__ = {"schema": "encounters"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    mrn: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name_family: Mapped[str | None] = mapped_column(String(255))
    name_given: Mapped[str | None] = mapped_column(String(255))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    encounters: Mapped[list["Encounter"]] = relationship("Encounter", back_populates="patient")


class Encounter(Base):
    """Patient encounter/visit - the core linking entity for clinical data."""
    __tablename__ = "encounters"
    __table_args__ = {"schema": "encounters"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.patients.id"), nullable=False, index=True)
    visit_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    encounter_type: Mapped[str | None] = mapped_column(String(50))  # inpatient, outpatient, emergency, observation
    service_line: Mapped[str | None] = mapped_column(String(100), index=True)
    payer_identifier: Mapped[str | None] = mapped_column(String(100))
    admit_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discharge_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    admitting_diagnosis: Mapped[str | None] = mapped_column(Text)
    discharge_disposition: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="open", index=True)  # open, closed, ready_to_code, coded
    ready_to_code_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ready_to_code_reason: Mapped[str | None] = mapped_column(String(50))  # discharge, timeout_manual, manual_override
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="encounters")
    diagnoses: Mapped[list["Diagnosis"]] = relationship("Diagnosis", back_populates="encounter")
    procedures: Mapped[list["Procedure"]] = relationship("Procedure", back_populates="encounter")
    observations: Mapped[list["Observation"]] = relationship("Observation", back_populates="encounter")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="encounter")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="encounter")


class Diagnosis(Base):
    """Diagnosis information from HL7 DG1 segments."""
    __tablename__ = "diagnoses"
    __table_args__ = {"schema": "encounters"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.encounters.id"), nullable=False, index=True)
    hl7_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.hl7_messages.id"))
    set_id: Mapped[int | None] = mapped_column(Integer)
    diagnosis_code: Mapped[str | None] = mapped_column(String(20), index=True)
    diagnosis_description: Mapped[str | None] = mapped_column(Text)
    diagnosis_type: Mapped[str | None] = mapped_column(String(50))  # admitting, working, final
    coding_method: Mapped[str | None] = mapped_column(String(20))  # ICD-10-CM, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    encounter: Mapped["Encounter"] = relationship("Encounter", back_populates="diagnoses")


class Procedure(Base):
    """Procedure information from HL7 PR1 segments."""
    __tablename__ = "procedures"
    __table_args__ = {"schema": "encounters"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.encounters.id"), nullable=False, index=True)
    hl7_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.hl7_messages.id"))
    set_id: Mapped[int | None] = mapped_column(Integer)
    procedure_code: Mapped[str | None] = mapped_column(String(20), index=True)
    procedure_description: Mapped[str | None] = mapped_column(Text)
    procedure_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    performing_physician: Mapped[str | None] = mapped_column(String(255))
    performing_physician_id: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    encounter: Mapped["Encounter"] = relationship("Encounter", back_populates="procedures")


class Observation(Base):
    """Clinical observations from HL7 OBX segments."""
    __tablename__ = "observations"
    __table_args__ = {"schema": "encounters"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.encounters.id"), nullable=False, index=True)
    hl7_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.hl7_messages.id"))
    set_id: Mapped[int | None] = mapped_column(Integer)
    observation_identifier: Mapped[str | None] = mapped_column(String(100), index=True)
    observation_value: Mapped[str | None] = mapped_column(Text)
    units: Mapped[str | None] = mapped_column(String(50))
    reference_range: Mapped[str | None] = mapped_column(String(100))
    abnormal_flags: Mapped[str | None] = mapped_column(String(20))
    observation_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_status: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    encounter: Mapped["Encounter"] = relationship("Encounter", back_populates="observations")


class Order(Base):
    """Order information from HL7 ORC/OBR segments."""
    __tablename__ = "orders"
    __table_args__ = {"schema": "encounters"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.encounters.id"), nullable=False, index=True)
    hl7_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.hl7_messages.id"))
    order_control: Mapped[str | None] = mapped_column(String(10))
    placer_order_number: Mapped[str | None] = mapped_column(String(100), index=True)
    filler_order_number: Mapped[str | None] = mapped_column(String(100), index=True)
    order_status: Mapped[str | None] = mapped_column(String(20))
    order_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ordering_provider: Mapped[str | None] = mapped_column(String(255))
    order_type: Mapped[str | None] = mapped_column(String(100))  # Universal Service ID
    diagnostic_service_section: Mapped[str | None] = mapped_column(String(20))  # OBR-24
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    encounter: Mapped["Encounter"] = relationship("Encounter", back_populates="orders")


class Document(Base):
    """Clinical documents from HL7 MDM messages."""
    __tablename__ = "documents"
    __table_args__ = {"schema": "encounters"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.encounters.id"), nullable=False, index=True)
    hl7_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.hl7_messages.id"))
    document_type: Mapped[str | None] = mapped_column(String(100), index=True)
    document_status: Mapped[str | None] = mapped_column(String(50))
    origination_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    encounter: Mapped["Encounter"] = relationship("Encounter", back_populates="documents")


class ServiceLineRule(Base):
    """Configurable rules for deriving service line from HL7 data."""
    __tablename__ = "service_line_rules"
    __table_args__ = {"schema": "encounters"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)  # diagnostic_section, department, procedure_range, default
    match_pattern: Mapped[str] = mapped_column(String(255), nullable=False)
    service_line: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
