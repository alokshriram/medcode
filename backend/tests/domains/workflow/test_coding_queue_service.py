"""Tests for the coding queue service."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.domains.workflow.coding_queue_service import CodingQueueService
from app.domains.workflow.models import CodingQueueItem, EncounterSnapshot, CodingConfiguration
from app.domains.encounters.models import Encounter, Patient, Procedure


class TestCodingQueueService:
    """Tests for CodingQueueService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create a CodingQueueService instance."""
        return CodingQueueService(mock_db)

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
        encounter.payer_identifier = "BCBS"
        encounter.admit_datetime = datetime.now(timezone.utc) - timedelta(days=3)
        encounter.discharge_datetime = datetime.now(timezone.utc)
        encounter.status = "ready_to_code"
        encounter.ready_to_code_at = datetime.now(timezone.utc)
        encounter.ready_to_code_reason = "discharge"
        encounter.admitting_diagnosis = "Appendicitis"
        encounter.discharge_disposition = "Home"
        return encounter

    # --- Configuration Tests ---

    def test_get_config_returns_cached_value(self, service):
        """Test that cached config values are returned."""
        service._config_cache["test_key"] = "cached_value"
        result = service.get_config("test_key")
        assert result == "cached_value"
        service.db.query.assert_not_called()

    def test_get_config_queries_database(self, service, mock_db):
        """Test that config is queried from database when not cached."""
        mock_config = MagicMock(spec=CodingConfiguration)
        mock_config.value = "db_value"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_config

        result = service.get_config("test_key")

        assert result == "db_value"
        assert service._config_cache["test_key"] == "db_value"

    def test_get_config_returns_default_when_not_found(self, service, mock_db):
        """Test that default is returned when config not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service.get_config("missing_key", "default_value")

        assert result == "default_value"

    def test_get_config_bool_true_values(self, service):
        """Test boolean config parsing for true values."""
        service._config_cache["bool_true"] = True
        service._config_cache["str_true"] = "true"
        service._config_cache["str_1"] = "1"
        service._config_cache["str_yes"] = "yes"

        assert service.get_config_bool("bool_true") is True
        assert service.get_config_bool("str_true") is True
        assert service.get_config_bool("str_1") is True
        assert service.get_config_bool("str_yes") is True

    def test_get_config_bool_false_values(self, service):
        """Test boolean config parsing for false values."""
        service._config_cache["bool_false"] = False
        service._config_cache["str_false"] = "false"
        service._config_cache["str_0"] = "0"

        assert service.get_config_bool("bool_false") is False
        assert service.get_config_bool("str_false") is False
        assert service.get_config_bool("str_0") is False

    def test_get_config_list_from_list(self, service):
        """Test list config when value is already a list."""
        service._config_cache["list_key"] = ["a", "b", "c"]
        result = service.get_config_list("list_key")
        assert result == ["a", "b", "c"]

    def test_get_config_list_from_json_string(self, service):
        """Test list config when value is a JSON string."""
        service._config_cache["json_list"] = '["radiology", "pathology"]'
        result = service.get_config_list("json_list")
        assert result == ["radiology", "pathology"]

    # --- Queue Item Operations Tests ---

    def test_get_queue_item(self, service, mock_db):
        """Test getting a queue item by ID."""
        item_id = uuid4()
        mock_item = MagicMock(spec=CodingQueueItem)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        result = service.get_queue_item(item_id)

        assert result == mock_item

    def test_assign_queue_item(self, service, mock_db):
        """Test assigning a queue item to a user."""
        item_id = uuid4()
        user_id = uuid4()
        mock_item = MagicMock(spec=CodingQueueItem)
        mock_item.status = "pending"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        result = service.assign_queue_item(item_id, user_id)

        assert result == mock_item
        assert mock_item.assigned_to == user_id
        assert mock_item.status == "in_progress"
        assert mock_item.assigned_at is not None
        mock_db.commit.assert_called()

    def test_complete_queue_item(self, service, mock_db):
        """Test completing a queue item."""
        item_id = uuid4()
        user_id = uuid4()
        mock_item = MagicMock(spec=CodingQueueItem)
        mock_item.status = "in_progress"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        result = service.complete_queue_item(item_id, user_id)

        assert result == mock_item
        assert mock_item.status == "completed"
        assert mock_item.completed_by == user_id
        assert mock_item.completed_at is not None
        mock_db.commit.assert_called()

    # --- Queue Creation Tests ---

    def test_create_queue_items_skips_if_existing(
        self, service, mock_db, sample_encounter
    ):
        """Test that queue items are not duplicated if they already exist."""
        existing_items = [MagicMock(spec=CodingQueueItem)]
        mock_db.query.return_value.filter.return_value.all.return_value = existing_items

        result = service.create_queue_items_for_encounter(sample_encounter)

        assert result == existing_items
        mock_db.add.assert_not_called()

    def test_create_queue_items_creates_facility_by_default(
        self, service, mock_db, sample_encounter, sample_patient
    ):
        """Test that facility queue item is created by default."""
        # Setup comprehensive mock that returns empty for all queries
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.first.return_value = sample_patient

        # Mock config for always_create_facility = True
        def mock_get_config_bool(key, default=False):
            if key == "always_create_facility":
                return True
            if key == "always_create_professional":
                return False
            return default

        def mock_get_config_list(key, default=None):
            if key == "professional_component_services":
                return ["radiology", "pathology"]
            return default or []

        service.get_config_bool = MagicMock(side_effect=mock_get_config_bool)
        service.get_config_list = MagicMock(side_effect=mock_get_config_list)

        result = service.create_queue_items_for_encounter(sample_encounter)

        # Should have called db.add at least once for facility item
        assert mock_db.add.called

    def test_create_queue_items_creates_professional_for_surgery(
        self, service, mock_db, sample_encounter, sample_patient
    ):
        """Test that professional queue item is created for surgery service line."""
        sample_encounter.service_line = "surgery"

        # Setup comprehensive mock
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.first.return_value = sample_patient

        # Mock config
        def mock_get_config_bool(key, default=False):
            if key == "always_create_facility":
                return True
            if key == "always_create_professional":
                return False
            return default

        def mock_get_config_list(key, default=None):
            if key == "professional_component_services":
                return ["radiology", "pathology", "cardiology", "surgery"]
            return default or []

        service.get_config_bool = MagicMock(side_effect=mock_get_config_bool)
        service.get_config_list = MagicMock(side_effect=mock_get_config_list)

        result = service.create_queue_items_for_encounter(sample_encounter)

        # Should create both facility and professional items
        # db.add should be called 4 times (queue item + snapshot for each)
        assert mock_db.add.call_count >= 4

    def test_create_queue_items_with_always_create_professional(
        self, service, mock_db, sample_encounter, sample_patient
    ):
        """Test that professional queue item is created when always_create_professional is True."""
        sample_encounter.service_line = "general"  # Not in professional services list

        # Setup comprehensive mock
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.first.return_value = sample_patient

        # Mock config with always_create_professional = True
        def mock_get_config_bool(key, default=False):
            if key == "always_create_facility":
                return True
            if key == "always_create_professional":
                return True  # Force professional creation
            return default

        def mock_get_config_list(key, default=None):
            if key == "professional_component_services":
                return ["radiology", "pathology"]  # Doesn't include "general"
            return default or []

        service.get_config_bool = MagicMock(side_effect=mock_get_config_bool)
        service.get_config_list = MagicMock(side_effect=mock_get_config_list)

        result = service.create_queue_items_for_encounter(sample_encounter)

        # Should create both facility and professional items
        # db.add should be called 4 times (queue item + snapshot for each)
        assert mock_db.add.call_count >= 4

    # --- Priority Calculation Tests ---

    def test_calculate_priority_emergency_highest(self, service):
        """Test that emergency encounters have highest priority."""
        encounter = MagicMock(spec=Encounter)
        encounter.encounter_type = "emergency"
        encounter.discharge_datetime = None

        priority = service._calculate_priority(encounter)

        assert priority >= 10

    def test_calculate_priority_inpatient_medium(self, service):
        """Test that inpatient encounters have medium priority."""
        encounter = MagicMock(spec=Encounter)
        encounter.encounter_type = "inpatient"
        encounter.discharge_datetime = None

        priority = service._calculate_priority(encounter)

        assert priority >= 5

    def test_calculate_priority_older_encounters_higher(self, service):
        """Test that older encounters get higher priority."""
        encounter = MagicMock(spec=Encounter)
        encounter.encounter_type = "outpatient"
        encounter.discharge_datetime = datetime.now(timezone.utc) - timedelta(days=5)

        priority = service._calculate_priority(encounter)

        assert priority >= 3

    # --- Snapshot Tests ---

    def test_refresh_snapshot_creates_new_version(self, service, mock_db, sample_encounter, sample_patient):
        """Test that refreshing a snapshot creates a new version."""
        queue_item_id = uuid4()
        mock_queue_item = MagicMock(spec=CodingQueueItem)
        mock_queue_item.encounter_id = sample_encounter.id

        mock_current_snapshot = MagicMock(spec=EncounterSnapshot)
        mock_current_snapshot.snapshot_version = 1

        # Mock queries
        def query_side_effect(model):
            mock_query = MagicMock()
            if model == CodingQueueItem:
                mock_query.filter.return_value.first.return_value = mock_queue_item
            elif model == Encounter:
                mock_query.filter.return_value.first.return_value = sample_encounter
            elif model == EncounterSnapshot:
                mock_query.filter.return_value.order_by.return_value.first.return_value = mock_current_snapshot
            elif model == Patient:
                mock_query.filter.return_value.first.return_value = sample_patient
            else:
                mock_query.filter.return_value.all.return_value = []
            return mock_query

        mock_db.query.side_effect = query_side_effect

        result = service.refresh_snapshot(queue_item_id)

        # Should create a new snapshot with version 2
        mock_db.add.assert_called()

    def test_get_latest_snapshot(self, service, mock_db):
        """Test getting the latest snapshot for a queue item."""
        queue_item_id = uuid4()
        mock_snapshot = MagicMock(spec=EncounterSnapshot)
        mock_snapshot.snapshot_version = 3

        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_snapshot

        result = service.get_latest_snapshot(queue_item_id)

        assert result == mock_snapshot
