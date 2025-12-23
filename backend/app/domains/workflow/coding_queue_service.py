"""Service for managing coding queue items."""
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.domains.workflow.models import CodingQueueItem, EncounterSnapshot, CodingConfiguration
from app.domains.encounters.models import Encounter, Patient, Diagnosis, Procedure, Observation, Order, Document

logger = logging.getLogger(__name__)


class CodingQueueService:
    """Service for creating and managing coding queue items."""

    def __init__(self, db: Session):
        self.db = db
        self._config_cache: dict[str, Any] = {}

    # --- Configuration ---

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        if key in self._config_cache:
            return self._config_cache[key]

        config = self.db.query(CodingConfiguration).filter(CodingConfiguration.key == key).first()
        if config:
            self._config_cache[key] = config.value
            return config.value
        return default

    def get_config_bool(self, key: str, default: bool = False) -> bool:
        """Get configuration value as boolean."""
        value = self.get_config(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)

    def get_config_list(self, key: str, default: list | None = None) -> list:
        """Get configuration value as list."""
        value = self.get_config(key, default or [])
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return [value]
        return default or []

    # --- Queue Item Operations ---

    def get_queue_item(self, item_id: UUID) -> CodingQueueItem | None:
        """Get queue item by ID."""
        return self.db.query(CodingQueueItem).filter(CodingQueueItem.id == item_id).first()

    def get_queue_items_for_encounter(self, encounter_id: UUID) -> list[CodingQueueItem]:
        """Get all queue items for an encounter."""
        return (
            self.db.query(CodingQueueItem)
            .filter(CodingQueueItem.encounter_id == encounter_id)
            .all()
        )

    def list_queue_items(
        self,
        status: str | None = None,
        billing_component: str | None = None,
        service_line: str | None = None,
        assigned_to: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[CodingQueueItem], int]:
        """List queue items with filters."""
        query = self.db.query(CodingQueueItem)

        if status:
            query = query.filter(CodingQueueItem.status == status)
        if billing_component:
            query = query.filter(CodingQueueItem.billing_component == billing_component)
        if service_line:
            query = query.filter(CodingQueueItem.service_line == service_line)
        if assigned_to:
            query = query.filter(CodingQueueItem.assigned_to == assigned_to)

        total = query.count()
        items = query.order_by(CodingQueueItem.priority.desc(), CodingQueueItem.created_at).offset(skip).limit(limit).all()

        return items, total

    def assign_queue_item(self, item_id: UUID, user_id: UUID) -> CodingQueueItem | None:
        """Assign a queue item to a user."""
        item = self.get_queue_item(item_id)
        if not item:
            return None

        item.assigned_to = user_id
        item.assigned_at = datetime.now(timezone.utc)
        item.status = "in_progress"
        self.db.commit()
        self.db.refresh(item)
        return item

    def complete_queue_item(self, item_id: UUID, user_id: UUID) -> CodingQueueItem | None:
        """Mark a queue item as completed."""
        item = self.get_queue_item(item_id)
        if not item:
            return None

        item.status = "completed"
        item.completed_at = datetime.now(timezone.utc)
        item.completed_by = user_id
        self.db.commit()
        self.db.refresh(item)
        return item

    # --- Queue Creation Logic ---

    def create_queue_items_for_encounter(
        self,
        encounter: Encounter,
        triggered_by: UUID | None = None,
    ) -> list[CodingQueueItem]:
        """
        Create coding queue items for an encounter that is ready to code.

        Based on PDD-001:
        - Always create facility work item (configurable)
        - Conditionally create professional work item based on:
          - Service line in professional_component_services list
          - Presence of interpreting/performing physician
          - Or always_create_professional config
        """
        created_items: list[CodingQueueItem] = []

        # Check if items already exist for this encounter
        existing = self.get_queue_items_for_encounter(encounter.id)
        if existing:
            logger.info(f"Queue items already exist for encounter {encounter.id}")
            return existing

        # Get configuration
        always_create_facility = self.get_config_bool("always_create_facility", True)
        always_create_professional = self.get_config_bool("always_create_professional", False)
        professional_services = self.get_config_list(
            "professional_component_services",
            ["radiology", "pathology", "cardiology", "surgery"]
        )

        # Create facility work item
        if always_create_facility:
            facility_item = self._create_queue_item(
                encounter=encounter,
                billing_component="facility",
                triggered_by=triggered_by,
            )
            created_items.append(facility_item)

        # Determine if we should create professional work item
        should_create_professional = always_create_professional

        if not should_create_professional and encounter.service_line:
            # Check if service line is in professional component services
            service_line_lower = encounter.service_line.lower()
            if any(svc.lower() in service_line_lower for svc in professional_services):
                should_create_professional = True

        if not should_create_professional:
            # Check if there's a performing physician in procedures
            procedures = self.db.query(Procedure).filter(Procedure.encounter_id == encounter.id).all()
            if any(p.performing_physician_id for p in procedures):
                should_create_professional = True

        if should_create_professional:
            professional_item = self._create_queue_item(
                encounter=encounter,
                billing_component="professional",
                triggered_by=triggered_by,
            )
            created_items.append(professional_item)

        logger.info(
            f"Created {len(created_items)} queue items for encounter {encounter.id}: "
            f"{[item.billing_component for item in created_items]}"
        )

        return created_items

    def _create_queue_item(
        self,
        encounter: Encounter,
        billing_component: str,
        triggered_by: UUID | None = None,
    ) -> CodingQueueItem:
        """Create a single queue item with snapshot."""
        # Create queue item
        queue_item = CodingQueueItem(
            encounter_id=encounter.id,
            billing_component=billing_component,
            queue_type=encounter.encounter_type,
            service_line=encounter.service_line,
            payer_identifier=encounter.payer_identifier,
            priority=self._calculate_priority(encounter),
            status="pending",
        )
        self.db.add(queue_item)
        self.db.commit()
        self.db.refresh(queue_item)

        # Create snapshot
        snapshot_data = self._create_encounter_snapshot_data(encounter)
        snapshot = EncounterSnapshot(
            encounter_id=encounter.id,
            queue_item_id=queue_item.id,
            snapshot_data=snapshot_data,
            snapshot_version=1,
            created_by=triggered_by,
        )
        self.db.add(snapshot)
        self.db.commit()

        return queue_item

    def _calculate_priority(self, encounter: Encounter) -> int:
        """Calculate priority for queue item based on encounter attributes."""
        priority = 0

        # Higher priority for certain encounter types
        if encounter.encounter_type == "emergency":
            priority += 10
        elif encounter.encounter_type == "inpatient":
            priority += 5

        # Higher priority for older encounters (longer since discharge)
        if encounter.discharge_datetime:
            days_since_discharge = (datetime.now(timezone.utc) - encounter.discharge_datetime).days
            if days_since_discharge > 3:
                priority += 3
            elif days_since_discharge > 7:
                priority += 5

        return priority

    def _create_encounter_snapshot_data(self, encounter: Encounter) -> dict[str, Any]:
        """Create snapshot of encounter data for coding."""
        # Get patient
        patient = self.db.query(Patient).filter(Patient.id == encounter.patient_id).first()

        # Get all related clinical data
        diagnoses = self.db.query(Diagnosis).filter(Diagnosis.encounter_id == encounter.id).all()
        procedures = self.db.query(Procedure).filter(Procedure.encounter_id == encounter.id).all()
        observations = self.db.query(Observation).filter(Observation.encounter_id == encounter.id).all()
        orders = self.db.query(Order).filter(Order.encounter_id == encounter.id).all()
        documents = self.db.query(Document).filter(Document.encounter_id == encounter.id).all()

        return {
            "snapshot_created_at": datetime.now(timezone.utc).isoformat(),
            "patient": {
                "id": str(patient.id) if patient else None,
                "mrn": patient.mrn if patient else None,
                "name_family": patient.name_family if patient else None,
                "name_given": patient.name_given if patient else None,
                "date_of_birth": patient.date_of_birth.isoformat() if patient and patient.date_of_birth else None,
                "gender": patient.gender if patient else None,
            },
            "encounter": {
                "id": str(encounter.id),
                "visit_number": encounter.visit_number,
                "encounter_type": encounter.encounter_type,
                "service_line": encounter.service_line,
                "payer_identifier": encounter.payer_identifier,
                "admit_datetime": encounter.admit_datetime.isoformat() if encounter.admit_datetime else None,
                "discharge_datetime": encounter.discharge_datetime.isoformat() if encounter.discharge_datetime else None,
                "admitting_diagnosis": encounter.admitting_diagnosis,
                "discharge_disposition": encounter.discharge_disposition,
                "status": encounter.status,
                "ready_to_code_at": encounter.ready_to_code_at.isoformat() if encounter.ready_to_code_at else None,
                "ready_to_code_reason": encounter.ready_to_code_reason,
            },
            "diagnoses": [
                {
                    "id": str(d.id),
                    "set_id": d.set_id,
                    "diagnosis_code": d.diagnosis_code,
                    "diagnosis_description": d.diagnosis_description,
                    "diagnosis_type": d.diagnosis_type,
                    "coding_method": d.coding_method,
                }
                for d in diagnoses
            ],
            "procedures": [
                {
                    "id": str(p.id),
                    "set_id": p.set_id,
                    "procedure_code": p.procedure_code,
                    "procedure_description": p.procedure_description,
                    "procedure_datetime": p.procedure_datetime.isoformat() if p.procedure_datetime else None,
                    "performing_physician": p.performing_physician,
                    "performing_physician_id": p.performing_physician_id,
                }
                for p in procedures
            ],
            "observations": [
                {
                    "id": str(o.id),
                    "set_id": o.set_id,
                    "observation_identifier": o.observation_identifier,
                    "observation_value": o.observation_value,
                    "units": o.units,
                    "reference_range": o.reference_range,
                    "abnormal_flags": o.abnormal_flags,
                    "observation_datetime": o.observation_datetime.isoformat() if o.observation_datetime else None,
                    "result_status": o.result_status,
                }
                for o in observations
            ],
            "orders": [
                {
                    "id": str(o.id),
                    "order_control": o.order_control,
                    "placer_order_number": o.placer_order_number,
                    "filler_order_number": o.filler_order_number,
                    "order_status": o.order_status,
                    "order_datetime": o.order_datetime.isoformat() if o.order_datetime else None,
                    "ordering_provider": o.ordering_provider,
                    "order_type": o.order_type,
                    "diagnostic_service_section": o.diagnostic_service_section,
                }
                for o in orders
            ],
            "documents": [
                {
                    "id": str(doc.id),
                    "document_type": doc.document_type,
                    "document_status": doc.document_status,
                    "origination_datetime": doc.origination_datetime.isoformat() if doc.origination_datetime else None,
                    "author": doc.author,
                    "content": doc.content,
                }
                for doc in documents
            ],
        }

    # --- Snapshot Refresh ---

    def refresh_snapshot(
        self,
        queue_item_id: UUID,
        triggered_by: UUID | None = None,
    ) -> EncounterSnapshot | None:
        """Create a new snapshot for a queue item (refresh with latest encounter data)."""
        queue_item = self.get_queue_item(queue_item_id)
        if not queue_item:
            return None

        # Get the encounter
        encounter = self.db.query(Encounter).filter(Encounter.id == queue_item.encounter_id).first()
        if not encounter:
            return None

        # Get current snapshot version
        current_version = (
            self.db.query(EncounterSnapshot)
            .filter(EncounterSnapshot.queue_item_id == queue_item_id)
            .order_by(EncounterSnapshot.snapshot_version.desc())
            .first()
        )
        new_version = (current_version.snapshot_version + 1) if current_version else 1

        # Create new snapshot
        snapshot_data = self._create_encounter_snapshot_data(encounter)
        snapshot = EncounterSnapshot(
            encounter_id=encounter.id,
            queue_item_id=queue_item_id,
            snapshot_data=snapshot_data,
            snapshot_version=new_version,
            created_by=triggered_by,
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)

        logger.info(f"Created snapshot version {new_version} for queue item {queue_item_id}")
        return snapshot

    def get_latest_snapshot(self, queue_item_id: UUID) -> EncounterSnapshot | None:
        """Get the latest snapshot for a queue item."""
        return (
            self.db.query(EncounterSnapshot)
            .filter(EncounterSnapshot.queue_item_id == queue_item_id)
            .order_by(EncounterSnapshot.snapshot_version.desc())
            .first()
        )
