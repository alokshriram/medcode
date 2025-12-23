"""Service layer for the encounters domain."""
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.domains.encounters.models import (
    HL7Message,
    Patient,
    Encounter,
    Diagnosis,
    Procedure,
    Observation,
    Order,
    Document,
    ServiceLineRule,
)
from app.domains.encounters.schemas import EncounterFilters
from app.domains.encounters.hl7 import (
    ParsedHL7Message,
    ParsedPatient,
    ParsedEncounter,
    ParsedDiagnosis,
    ParsedProcedure,
    ParsedObservation,
    ParsedOrder,
    ParsedDocument,
)
from app.domains.workflow.coding_queue_service import CodingQueueService

logger = logging.getLogger(__name__)


class EncountersService:
    """Service for managing encounters and related clinical data."""

    def __init__(self, db: Session):
        self.db = db
        self._coding_queue_service: CodingQueueService | None = None

    @property
    def coding_queue_service(self) -> CodingQueueService:
        """Lazy-load the coding queue service."""
        if self._coding_queue_service is None:
            self._coding_queue_service = CodingQueueService(self.db)
        return self._coding_queue_service

    # --- Patient Operations ---

    def get_patient_by_mrn(self, mrn: str) -> Patient | None:
        """Get patient by MRN."""
        return self.db.query(Patient).filter(Patient.mrn == mrn).first()

    def get_or_create_patient(self, parsed: ParsedPatient) -> Patient:
        """Get existing patient or create new one from parsed HL7 data."""
        patient = self.get_patient_by_mrn(parsed.mrn)

        if patient:
            # Update patient info if we have new data
            if parsed.name_family and not patient.name_family:
                patient.name_family = parsed.name_family
            if parsed.name_given and not patient.name_given:
                patient.name_given = parsed.name_given
            if parsed.date_of_birth and not patient.date_of_birth:
                patient.date_of_birth = parsed.date_of_birth
            if parsed.gender and not patient.gender:
                patient.gender = parsed.gender
            self.db.commit()
            return patient

        # Create new patient
        patient = Patient(
            mrn=parsed.mrn,
            name_family=parsed.name_family,
            name_given=parsed.name_given,
            date_of_birth=parsed.date_of_birth,
            gender=parsed.gender,
        )
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient

    # --- Encounter Operations ---

    def get_encounter(self, encounter_id: UUID) -> Encounter | None:
        """Get encounter by ID."""
        return self.db.query(Encounter).filter(Encounter.id == encounter_id).first()

    def get_encounter_by_visit_number(self, visit_number: str) -> Encounter | None:
        """Get encounter by visit number."""
        return self.db.query(Encounter).filter(Encounter.visit_number == visit_number).first()

    def get_encounter_with_details(self, encounter_id: UUID) -> Encounter | None:
        """Get encounter with all related data loaded."""
        return (
            self.db.query(Encounter)
            .options(
                joinedload(Encounter.patient),
                joinedload(Encounter.diagnoses),
                joinedload(Encounter.procedures),
                joinedload(Encounter.observations),
                joinedload(Encounter.orders),
                joinedload(Encounter.documents),
            )
            .filter(Encounter.id == encounter_id)
            .first()
        )

    def list_encounters(
        self,
        filters: EncounterFilters | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Encounter], int]:
        """List encounters with optional filters."""
        query = self.db.query(Encounter).join(Patient)

        if filters:
            if filters.status:
                query = query.filter(Encounter.status == filters.status)
            if filters.encounter_type:
                query = query.filter(Encounter.encounter_type == filters.encounter_type)
            if filters.service_line:
                query = query.filter(Encounter.service_line == filters.service_line)
            if filters.patient_mrn:
                query = query.filter(Patient.mrn == filters.patient_mrn)
            if filters.visit_number:
                query = query.filter(Encounter.visit_number == filters.visit_number)
            if filters.admit_date_from:
                query = query.filter(Encounter.admit_datetime >= filters.admit_date_from)
            if filters.admit_date_to:
                query = query.filter(Encounter.admit_datetime <= filters.admit_date_to)

        total = query.count()
        encounters = query.order_by(Encounter.created_at.desc()).offset(skip).limit(limit).all()

        return encounters, total

    def get_or_create_encounter(
        self,
        patient: Patient,
        parsed: ParsedEncounter,
    ) -> tuple[Encounter, bool]:
        """
        Get existing encounter or create new one from parsed HL7 data.

        Returns:
            Tuple of (encounter, is_new)
        """
        encounter = self.get_encounter_by_visit_number(parsed.visit_number)

        if encounter:
            # Update encounter info if we have new data
            if parsed.encounter_type and not encounter.encounter_type:
                encounter.encounter_type = parsed.encounter_type
            if parsed.admit_datetime and not encounter.admit_datetime:
                encounter.admit_datetime = parsed.admit_datetime
            if parsed.discharge_datetime:
                encounter.discharge_datetime = parsed.discharge_datetime
            if parsed.hospital_service:
                encounter.service_line = self._derive_service_line(parsed.hospital_service)

            encounter.last_message_at = datetime.now(timezone.utc)
            self.db.commit()
            return encounter, False

        # Derive service line for new encounter
        service_line = self._derive_service_line(parsed.hospital_service) if parsed.hospital_service else None

        # Create new encounter
        encounter = Encounter(
            patient_id=patient.id,
            visit_number=parsed.visit_number,
            encounter_type=parsed.encounter_type,
            service_line=service_line,
            admit_datetime=parsed.admit_datetime,
            discharge_datetime=parsed.discharge_datetime,
            last_message_at=datetime.now(timezone.utc),
        )
        self.db.add(encounter)
        self.db.commit()
        self.db.refresh(encounter)
        return encounter, True

    def mark_ready_to_code(
        self,
        encounter_id: UUID,
        reason: str = "manual_override",
        triggered_by: UUID | None = None,
    ) -> Encounter | None:
        """Mark an encounter as ready to code and create coding queue items."""
        encounter = self.get_encounter(encounter_id)
        if not encounter:
            return None

        # Only transition if not already ready to code
        if encounter.status == "ready_to_code":
            logger.info(f"Encounter {encounter_id} is already ready to code")
            return encounter

        encounter.status = "ready_to_code"
        encounter.ready_to_code_at = datetime.now(timezone.utc)
        encounter.ready_to_code_reason = reason
        self.db.commit()
        self.db.refresh(encounter)

        # Create coding queue items
        queue_items = self.coding_queue_service.create_queue_items_for_encounter(
            encounter=encounter,
            triggered_by=triggered_by,
        )
        logger.info(
            f"Created {len(queue_items)} queue items for encounter {encounter_id} "
            f"(reason: {reason})"
        )

        return encounter

    # --- HL7 Message Operations ---

    def get_hl7_message_by_control_id(self, control_id: str) -> HL7Message | None:
        """Get HL7 message by message control ID (for idempotency)."""
        return (
            self.db.query(HL7Message)
            .filter(HL7Message.message_control_id == control_id)
            .first()
        )

    def store_hl7_message(
        self,
        parsed: ParsedHL7Message,
        file_source: str | None = None,
    ) -> tuple[HL7Message, bool]:
        """
        Store raw HL7 message for audit.

        Returns:
            Tuple of (message, is_duplicate)
        """
        # Check for duplicate
        existing = self.get_hl7_message_by_control_id(parsed.message_control_id)
        if existing:
            return existing, True

        message = HL7Message(
            message_control_id=parsed.message_control_id,
            message_type=parsed.message_type,
            event_type=parsed.event_type,
            raw_content=parsed.raw_content,
            file_source=file_source,
            processing_status="pending",
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message, False

    def update_message_status(
        self,
        message_id: UUID,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Update HL7 message processing status."""
        message = self.db.query(HL7Message).filter(HL7Message.id == message_id).first()
        if message:
            message.processing_status = status
            if error_message:
                message.error_message = error_message
            self.db.commit()

    # --- Clinical Data Operations ---

    def add_diagnosis(
        self,
        encounter: Encounter,
        hl7_message: HL7Message,
        parsed: ParsedDiagnosis,
    ) -> Diagnosis:
        """Add diagnosis to encounter."""
        diagnosis = Diagnosis(
            encounter_id=encounter.id,
            hl7_message_id=hl7_message.id,
            set_id=parsed.set_id,
            diagnosis_code=parsed.diagnosis_code,
            diagnosis_description=parsed.diagnosis_description,
            diagnosis_type=parsed.diagnosis_type,
            coding_method=parsed.coding_method,
        )
        self.db.add(diagnosis)
        self.db.commit()
        return diagnosis

    def add_procedure(
        self,
        encounter: Encounter,
        hl7_message: HL7Message,
        parsed: ParsedProcedure,
    ) -> Procedure:
        """Add procedure to encounter."""
        procedure = Procedure(
            encounter_id=encounter.id,
            hl7_message_id=hl7_message.id,
            set_id=parsed.set_id,
            procedure_code=parsed.procedure_code,
            procedure_description=parsed.procedure_description,
            procedure_datetime=parsed.procedure_datetime,
            performing_physician=parsed.performing_physician,
            performing_physician_id=parsed.performing_physician_id,
        )
        self.db.add(procedure)
        self.db.commit()
        return procedure

    def add_observation(
        self,
        encounter: Encounter,
        hl7_message: HL7Message,
        parsed: ParsedObservation,
    ) -> Observation:
        """Add observation to encounter."""
        observation = Observation(
            encounter_id=encounter.id,
            hl7_message_id=hl7_message.id,
            set_id=parsed.set_id,
            observation_identifier=parsed.observation_identifier,
            observation_value=parsed.observation_value,
            units=parsed.units,
            reference_range=parsed.reference_range,
            abnormal_flags=parsed.abnormal_flags,
            observation_datetime=parsed.observation_datetime,
            result_status=parsed.result_status,
        )
        self.db.add(observation)
        self.db.commit()
        return observation

    def add_order(
        self,
        encounter: Encounter,
        hl7_message: HL7Message,
        parsed: ParsedOrder,
    ) -> Order:
        """Add order to encounter."""
        order = Order(
            encounter_id=encounter.id,
            hl7_message_id=hl7_message.id,
            order_control=parsed.order_control,
            placer_order_number=parsed.placer_order_number,
            filler_order_number=parsed.filler_order_number,
            order_status=parsed.order_status,
            order_datetime=parsed.order_datetime,
            ordering_provider=parsed.ordering_provider,
            order_type=parsed.order_type,
            diagnostic_service_section=parsed.diagnostic_service_section,
        )
        self.db.add(order)
        self.db.commit()

        # Update encounter service line if we have diagnostic section
        if parsed.diagnostic_service_section and not encounter.service_line:
            encounter.service_line = self._derive_service_line(parsed.diagnostic_service_section)
            self.db.commit()

        return order

    def add_document(
        self,
        encounter: Encounter,
        hl7_message: HL7Message,
        parsed: ParsedDocument,
    ) -> Document:
        """Add document to encounter."""
        document = Document(
            encounter_id=encounter.id,
            hl7_message_id=hl7_message.id,
            document_type=parsed.document_type,
            document_status=parsed.document_status,
            origination_datetime=parsed.origination_datetime,
            author=parsed.author,
            content=parsed.content,
        )
        self.db.add(document)
        self.db.commit()
        return document

    # --- Service Line Derivation ---

    def get_service_line_rules(self) -> list[ServiceLineRule]:
        """Get all active service line rules ordered by priority."""
        return (
            self.db.query(ServiceLineRule)
            .filter(ServiceLineRule.is_active == True)
            .order_by(ServiceLineRule.priority)
            .all()
        )

    def _derive_service_line(self, code: str) -> str:
        """Derive service line from diagnostic section or hospital service code."""
        if not code:
            return "Unassigned"

        code_upper = code.upper()

        # Get rules from database
        rules = self.get_service_line_rules()

        for rule in rules:
            if rule.rule_type == "diagnostic_section":
                if rule.match_pattern.upper() == code_upper:
                    return rule.service_line
            elif rule.rule_type == "default" and rule.match_pattern == "*":
                return rule.service_line

        return "Unassigned"

    # --- HL7 Message Processing ---

    def process_hl7_message(
        self,
        parsed: ParsedHL7Message,
        file_source: str | None = None,
    ) -> dict:
        """
        Process a parsed HL7 message and store all data.

        Returns:
            dict with processing results
        """
        result = {
            "message_id": None,
            "is_duplicate": False,
            "encounter_id": None,
            "encounter_created": False,
            "patient_id": None,
            "error": None,
        }

        try:
            # Store raw message (idempotency check)
            hl7_msg, is_duplicate = self.store_hl7_message(parsed, file_source)
            result["message_id"] = str(hl7_msg.id)
            result["is_duplicate"] = is_duplicate

            if is_duplicate:
                self.update_message_status(hl7_msg.id, "duplicate")
                return result

            # Validate required data
            if not parsed.has_patient:
                self.update_message_status(hl7_msg.id, "error", "Missing patient data")
                result["error"] = "Missing patient data"
                return result

            if not parsed.has_encounter:
                self.update_message_status(hl7_msg.id, "error", "Missing encounter data")
                result["error"] = "Missing encounter data"
                return result

            # Get or create patient
            patient = self.get_or_create_patient(parsed.patient)
            result["patient_id"] = str(patient.id)

            # Get or create encounter
            encounter, is_new = self.get_or_create_encounter(patient, parsed.encounter)
            result["encounter_id"] = str(encounter.id)
            result["encounter_created"] = is_new

            # Add clinical data
            for diag in parsed.diagnoses:
                self.add_diagnosis(encounter, hl7_msg, diag)

            for proc in parsed.procedures:
                self.add_procedure(encounter, hl7_msg, proc)

            for obs in parsed.observations:
                self.add_observation(encounter, hl7_msg, obs)

            for order in parsed.orders:
                self.add_order(encounter, hl7_msg, order)

            for doc in parsed.documents:
                self.add_document(encounter, hl7_msg, doc)

            # Check for discharge event
            if parsed.is_discharge_event and encounter.status == "open":
                encounter.status = "ready_to_code"
                encounter.ready_to_code_at = datetime.now(timezone.utc)
                encounter.ready_to_code_reason = "discharge"
                if parsed.encounter.discharge_datetime:
                    encounter.discharge_datetime = parsed.encounter.discharge_datetime
                self.db.commit()
                self.db.refresh(encounter)

                # Create coding queue items for the now-ready encounter
                queue_items = self.coding_queue_service.create_queue_items_for_encounter(
                    encounter=encounter,
                    triggered_by=None,  # System-triggered via HL7 processing
                )
                result["queue_items_created"] = len(queue_items)
                logger.info(
                    f"Discharge detected for encounter {encounter.id}, "
                    f"created {len(queue_items)} queue items"
                )

            # Update message status
            self.update_message_status(hl7_msg.id, "processed")

        except Exception as e:
            logger.exception(f"Error processing HL7 message: {e}")
            if result["message_id"]:
                self.update_message_status(UUID(result["message_id"]), "error", str(e))
            result["error"] = str(e)

        return result

    # --- Stale Encounter Detection ---

    def get_stale_encounters(self, hours: int = 72) -> list[Encounter]:
        """Get encounters that haven't received messages in the specified hours."""
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        return (
            self.db.query(Encounter)
            .filter(
                and_(
                    Encounter.status == "open",
                    Encounter.last_message_at < cutoff,
                )
            )
            .all()
        )

    def flag_stale_encounters(self, hours: int = 72) -> int:
        """Flag stale encounters for review. Returns count of flagged encounters."""
        stale = self.get_stale_encounters(hours)
        count = 0

        for encounter in stale:
            encounter.status = "stale"
            count += 1

        if count > 0:
            self.db.commit()

        return count
