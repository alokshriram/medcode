"""Tests for EncountersService integration with CodingQueueService."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.domains.encounters.service import EncountersService
from app.domains.encounters.models import Encounter, Patient
from app.domains.encounters.hl7 import (
    ParsedHL7Message,
    ParsedPatient,
    ParsedEncounter,
)


class TestEncountersServiceQueueIntegration:
    """Tests for queue creation integration in EncountersService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create an EncountersService instance."""
        return EncountersService(mock_db)

    @pytest.fixture
    def sample_patient(self):
        """Create a sample patient."""
        patient = MagicMock(spec=Patient)
        patient.id = uuid4()
        patient.mrn = "12345678"
        patient.name_family = "Smith"
        patient.name_given = "John"
        patient.date_of_birth = datetime(1980, 5, 15).date()
        patient.gender = "M"
        return patient

    @pytest.fixture
    def sample_encounter(self, sample_patient):
        """Create a sample encounter."""
        encounter = MagicMock(spec=Encounter)
        encounter.id = uuid4()
        encounter.patient_id = sample_patient.id
        encounter.visit_number = "V123456789"
        encounter.encounter_type = "inpatient"
        encounter.service_line = "surgery"
        encounter.status = "open"
        encounter.admit_datetime = datetime.now(timezone.utc) - timedelta(days=3)
        encounter.discharge_datetime = None
        encounter.ready_to_code_at = None
        encounter.ready_to_code_reason = None
        return encounter

    def test_mark_ready_to_code_creates_queue_items(
        self, service, mock_db, sample_encounter
    ):
        """Test that mark_ready_to_code creates coding queue items."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_encounter

        with patch.object(
            service.coding_queue_service,
            "create_queue_items_for_encounter",
            return_value=[MagicMock(), MagicMock()],
        ) as mock_create:
            result = service.mark_ready_to_code(
                sample_encounter.id,
                reason="manual_override",
                triggered_by=uuid4(),
            )

            assert result is not None
            assert result.status == "ready_to_code"
            assert result.ready_to_code_reason == "manual_override"
            mock_create.assert_called_once()

    def test_mark_ready_to_code_skips_already_ready(
        self, service, mock_db, sample_encounter
    ):
        """Test that mark_ready_to_code skips if already ready."""
        sample_encounter.status = "ready_to_code"
        mock_db.query.return_value.filter.return_value.first.return_value = sample_encounter

        with patch.object(
            service.coding_queue_service,
            "create_queue_items_for_encounter",
        ) as mock_create:
            result = service.mark_ready_to_code(sample_encounter.id)

            assert result is not None
            # Should not create new queue items
            mock_create.assert_not_called()

    def test_process_hl7_discharge_creates_queue_items(
        self, service, mock_db, sample_patient, sample_encounter
    ):
        """Test that processing a discharge event creates queue items."""
        # Setup mock HL7 message
        parsed = ParsedHL7Message(
            message_control_id="MSG001",
            message_type="ADT",
            event_type="A03",  # Discharge event
            raw_content="MSH|...",
            patient=ParsedPatient(
                mrn="12345678",
                name_family="Smith",
                name_given="John",
            ),
            encounter=ParsedEncounter(
                visit_number="V123456789",
                encounter_type="inpatient",
                discharge_datetime=datetime.now(timezone.utc),
            ),
        )

        # Mock HL7 message storage (not duplicate)
        mock_hl7_msg = MagicMock()
        mock_hl7_msg.id = uuid4()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,  # No existing message (not duplicate)
            sample_patient,  # Patient lookup
            sample_encounter,  # Encounter lookup
        ]

        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        with patch.object(service, "store_hl7_message", return_value=(mock_hl7_msg, False)):
            with patch.object(service, "get_or_create_patient", return_value=sample_patient):
                with patch.object(service, "get_or_create_encounter", return_value=(sample_encounter, False)):
                    with patch.object(
                        service.coding_queue_service,
                        "create_queue_items_for_encounter",
                        return_value=[MagicMock()],
                    ) as mock_create:
                        result = service.process_hl7_message(parsed)

                        # Queue items should be created for discharge
                        mock_create.assert_called_once()
                        assert "queue_items_created" in result
                        assert result["queue_items_created"] == 1

    def test_process_hl7_non_discharge_no_queue_items(
        self, service, mock_db, sample_patient, sample_encounter
    ):
        """Test that non-discharge events don't create queue items."""
        # Setup mock HL7 message (ADT^A01 - Admit, not discharge)
        parsed = ParsedHL7Message(
            message_control_id="MSG002",
            message_type="ADT",
            event_type="A01",  # Admit event, not discharge
            raw_content="MSH|...",
            patient=ParsedPatient(
                mrn="12345678",
                name_family="Smith",
                name_given="John",
            ),
            encounter=ParsedEncounter(
                visit_number="V123456789",
                encounter_type="inpatient",
            ),
        )

        mock_hl7_msg = MagicMock()
        mock_hl7_msg.id = uuid4()

        with patch.object(service, "store_hl7_message", return_value=(mock_hl7_msg, False)):
            with patch.object(service, "get_or_create_patient", return_value=sample_patient):
                with patch.object(service, "get_or_create_encounter", return_value=(sample_encounter, True)):
                    with patch.object(service, "update_message_status"):
                        with patch.object(
                            service.coding_queue_service,
                            "create_queue_items_for_encounter",
                        ) as mock_create:
                            result = service.process_hl7_message(parsed)

                            # Queue items should NOT be created for admit
                            mock_create.assert_not_called()
                            assert "queue_items_created" not in result

    def test_lazy_loading_coding_queue_service(self, service):
        """Test that coding_queue_service is lazy-loaded."""
        # Initially None
        assert service._coding_queue_service is None

        # Access property to trigger lazy load
        queue_service = service.coding_queue_service

        # Now it should be set
        assert service._coding_queue_service is not None
        assert queue_service is service._coding_queue_service

        # Second access returns same instance
        assert service.coding_queue_service is queue_service
