"""Tests for HL7 v2.x parser."""
import pytest
from datetime import date

from app.domains.encounters.hl7 import HL7Parser, HL7BatchParser


# Sample ADT^A01 (Admit) message
SAMPLE_ADT_A01 = """MSH|^~\\&|EPIC|HOSPITAL|MEDCODE|CODING|20251215120000||ADT^A01|MSG00001|P|2.5
PID|1||12345678^^^MRN||Smith^John^A||19800515|M|||123 Main St^^Chicago^IL^60601
PV1|1|I|4N^401^A^^^N||||1234567^Jones^Mary^MD|||SUR||||||||V123456789^^^VISIT|||||||||||||||||||||||||20251215100000"""

# Sample ADT^A03 (Discharge) message
SAMPLE_ADT_A03 = """MSH|^~\\&|EPIC|HOSPITAL|MEDCODE|CODING|20251217150000||ADT^A03|MSG00002|P|2.5
PID|1||12345678^^^MRN||Smith^John^A||19800515|M
PV1|1|I|4N^401^A^^^N||||1234567^Jones^Mary^MD|||SUR||||||||V123456789^^^VISIT|||||||||||||||||||||||||20251215100000|20251217140000"""

# Sample ORU^R01 (Observation Result) message
SAMPLE_ORU_R01 = """MSH|^~\\&|LAB|HOSPITAL|MEDCODE|CODING|20251216080000||ORU^R01|MSG00003|P|2.5
PID|1||12345678^^^MRN||Smith^John^A||19800515|M
PV1|1|I|4N^401^A|||||||||||||||V123456789^^^VISIT
ORC|RE|ORD001|FIL001||CM||||20251216070000|^Ordering^Doctor
OBR|1|ORD001|FIL001|80053^METABOLIC PANEL^CPT|||20251216070000||||||||^Ordering^Doctor||||||20251216080000|||F||||||LAB
OBX|1|NM|2345-7^GLUCOSE^LN||95|mg/dL|70-100|N|||F|||20251216075500
OBX|2|NM|2160-0^CREATININE^LN||1.1|mg/dL|0.7-1.3|N|||F|||20251216075500"""

# Sample ORM^O01 (Order) message
SAMPLE_ORM_O01 = """MSH|^~\\&|EHR|HOSPITAL|MEDCODE|CODING|20251216100000||ORM^O01|MSG00004|P|2.5
PID|1||12345678^^^MRN||Smith^John^A||19800515|M
PV1|1|I|4N^401^A|||||||||||||||V123456789^^^VISIT
ORC|NW|ORD002||||||20251216100000|^Ordering^Doctor
OBR|1|ORD002||71046^CHEST X-RAY^CPT|||20251216100000|||||||||||||||RAD"""

# Sample batch file with multiple messages
SAMPLE_BATCH = SAMPLE_ADT_A01 + "\n" + SAMPLE_ORU_R01


class TestHL7Parser:
    """Tests for HL7Parser class."""

    def setup_method(self):
        self.parser = HL7Parser()

    def test_parse_adt_a01_message_header(self):
        """Test parsing ADT^A01 message header."""
        result = self.parser.parse(SAMPLE_ADT_A01)

        assert result.message_control_id == "MSG00001"
        assert result.message_type == "ADT"
        assert result.event_type == "A01"
        assert result.sending_application == "EPIC"
        assert result.sending_facility == "HOSPITAL"

    def test_parse_adt_a01_patient(self):
        """Test parsing patient from ADT^A01."""
        result = self.parser.parse(SAMPLE_ADT_A01)

        assert result.patient is not None
        assert result.patient.mrn == "12345678"
        assert result.patient.name_family == "Smith"
        assert result.patient.name_given == "John"
        assert result.patient.date_of_birth == date(1980, 5, 15)
        assert result.patient.gender == "M"

    def test_parse_adt_a01_encounter(self):
        """Test parsing encounter from ADT^A01."""
        result = self.parser.parse(SAMPLE_ADT_A01)

        assert result.encounter is not None
        assert result.encounter.visit_number == "V123456789"
        assert result.encounter.encounter_type == "inpatient"
        assert result.encounter.hospital_service == "SUR"

    def test_parse_adt_a03_is_discharge(self):
        """Test that ADT^A03 is identified as discharge event."""
        result = self.parser.parse(SAMPLE_ADT_A03)

        assert result.message_type == "ADT"
        assert result.event_type == "A03"
        assert result.is_discharge_event is True

    def test_parse_adt_a01_is_not_discharge(self):
        """Test that ADT^A01 is not a discharge event."""
        result = self.parser.parse(SAMPLE_ADT_A01)

        assert result.is_discharge_event is False

    def test_parse_oru_r01_observations(self):
        """Test parsing observations from ORU^R01."""
        result = self.parser.parse(SAMPLE_ORU_R01)

        assert result.message_type == "ORU"
        assert result.event_type == "R01"
        assert len(result.observations) == 2

        # Check first observation (glucose)
        glucose = result.observations[0]
        assert glucose.set_id == 1
        assert glucose.observation_identifier == "2345-7"
        assert glucose.observation_value == "95"
        assert glucose.units == "mg/dL"
        assert glucose.reference_range == "70-100"
        assert glucose.abnormal_flags == "N"
        assert glucose.result_status == "F"

    def test_parse_oru_r01_orders(self):
        """Test parsing orders from ORU^R01."""
        result = self.parser.parse(SAMPLE_ORU_R01)

        assert len(result.orders) >= 1
        order = result.orders[0]
        assert order.order_control == "RE"
        assert order.placer_order_number == "ORD001"
        assert order.filler_order_number == "FIL001"
        assert order.diagnostic_service_section == "LAB"

    def test_parse_orm_o01_order(self):
        """Test parsing order from ORM^O01."""
        result = self.parser.parse(SAMPLE_ORM_O01)

        assert result.message_type == "ORM"
        assert len(result.orders) >= 1

        order = result.orders[0]
        assert order.order_control == "NW"
        assert order.placer_order_number == "ORD002"
        assert order.order_type_code == "71046"
        assert "CHEST" in order.order_type.upper()
        assert order.diagnostic_service_section == "RAD"

    def test_parse_invalid_message(self):
        """Test parsing invalid message adds errors."""
        result = self.parser.parse("This is not HL7")

        # Should have errors but not crash
        assert len(result.parse_errors) > 0 or result.message_control_id == "UNKNOWN"

    def test_has_patient_property(self):
        """Test has_patient property."""
        result = self.parser.parse(SAMPLE_ADT_A01)
        assert result.has_patient is True

        result = self.parser.parse("MSH|^~\\&|TEST|||||||ADT^A01|123|P|2.5")
        assert result.has_patient is False

    def test_has_encounter_property(self):
        """Test has_encounter property."""
        result = self.parser.parse(SAMPLE_ADT_A01)
        assert result.has_encounter is True


class TestHL7BatchParser:
    """Tests for HL7BatchParser class."""

    def setup_method(self):
        self.parser = HL7BatchParser()

    def test_parse_single_message(self):
        """Test parsing file with single message."""
        results = self.parser.parse_file_content(SAMPLE_ADT_A01)

        assert len(results) == 1
        assert results[0].message_control_id == "MSG00001"

    def test_parse_batch_file(self):
        """Test parsing file with multiple messages."""
        results = self.parser.parse_file_content(SAMPLE_BATCH)

        assert len(results) == 2
        assert results[0].message_type == "ADT"
        assert results[1].message_type == "ORU"

    def test_parse_empty_content(self):
        """Test parsing empty content."""
        results = self.parser.parse_file_content("")
        assert len(results) == 0

    def test_parse_handles_different_line_endings(self):
        """Test parser handles various line endings."""
        # Unix style
        unix = SAMPLE_ADT_A01.replace("\r\n", "\n")
        results = self.parser.parse_file_content(unix)
        assert len(results) == 1

        # Windows style
        windows = SAMPLE_ADT_A01.replace("\n", "\r\n")
        results = self.parser.parse_file_content(windows)
        assert len(results) == 1
