"""HL7 v2.x message parser using hl7apy."""
import logging
import re
from datetime import datetime, date

from hl7apy import parser as hl7_parser
from hl7apy.core import Message, Segment
from hl7apy.exceptions import ParserError

from .types import (
    ParsedHL7Message,
    ParsedPatient,
    ParsedEncounter,
    ParsedDiagnosis,
    ParsedProcedure,
    ParsedObservation,
    ParsedOrder,
    ParsedDocument,
)

logger = logging.getLogger(__name__)

# HL7 message segment delimiter
SEGMENT_DELIMITER = "\r"
# HL7 batch message delimiters - match MSH| at start of line or after \r
MESSAGE_START_PATTERN = re.compile(r"(?:^|\r)MSH\|")


class HL7Parser:
    """Parser for individual HL7 v2.x messages."""

    def parse(self, raw_message: str) -> ParsedHL7Message:
        """
        Parse a single HL7 v2.x message.

        Args:
            raw_message: Raw HL7 message string

        Returns:
            ParsedHL7Message with extracted data
        """
        # Normalize line endings
        normalized = self._normalize_message(raw_message)

        errors: list[str] = []
        parsed = ParsedHL7Message(
            message_control_id="UNKNOWN",
            message_type="UNKNOWN",
            raw_content=raw_message,
        )

        try:
            # Parse with hl7apy
            msg = hl7_parser.parse_message(normalized, find_groups=False)

            # Extract MSH header
            self._parse_msh(msg, parsed)

            # Extract patient from PID
            parsed.patient = self._parse_pid(msg, errors)

            # Extract encounter from PV1
            parsed.encounter = self._parse_pv1(msg, errors)

            # Extract diagnoses from DG1 segments
            parsed.diagnoses = self._parse_dg1_segments(msg, errors)

            # Extract procedures from PR1 segments
            parsed.procedures = self._parse_pr1_segments(msg, errors)

            # Extract observations from OBX segments
            parsed.observations = self._parse_obx_segments(msg, errors)

            # Extract orders from ORC/OBR segments
            parsed.orders = self._parse_order_segments(msg, errors)

            # Extract documents from TXA/OBX (for MDM messages)
            if parsed.message_type == "MDM":
                parsed.documents = self._parse_document_segments(msg, errors)

        except ParserError as e:
            errors.append(f"HL7 parse error: {str(e)}")
            logger.warning(f"Failed to parse HL7 message: {e}")
        except Exception as e:
            errors.append(f"Unexpected error: {str(e)}")
            logger.exception(f"Unexpected error parsing HL7 message: {e}")

        parsed.parse_errors = errors
        return parsed

    def _normalize_message(self, raw: str) -> str:
        """Normalize line endings to HL7 standard (carriage return)."""
        # Replace various line ending combinations with \r
        normalized = raw.replace("\r\n", "\r").replace("\n", "\r")
        # Remove leading/trailing whitespace but preserve internal structure
        return normalized.strip()

    def _parse_msh(self, msg: Message, parsed: ParsedHL7Message) -> None:
        """Extract message header information from MSH segment."""
        try:
            msh = msg.msh
            parsed.sending_application = self._get_field_value(msh, "msh_3")
            parsed.sending_facility = self._get_field_value(msh, "msh_4")

            # Message datetime (MSH-7)
            dt_str = self._get_field_value(msh, "msh_7")
            if dt_str:
                parsed.message_datetime = self._parse_datetime(dt_str)

            # Message type (MSH-9) - e.g., "ADT^A01"
            msg_type = self._get_field_value(msh, "msh_9")
            if msg_type:
                parts = msg_type.split("^")
                parsed.message_type = parts[0] if parts else "UNKNOWN"
                parsed.event_type = parts[1] if len(parts) > 1 else None

            # Message control ID (MSH-10) - unique identifier
            parsed.message_control_id = self._get_field_value(msh, "msh_10") or "UNKNOWN"

        except Exception as e:
            logger.debug(f"Error parsing MSH: {e}")

    def _parse_pid(self, msg: Message, errors: list[str]) -> ParsedPatient | None:
        """Extract patient demographics from PID segment."""
        try:
            pid = self._get_segment(msg, "PID")
            if not pid:
                return None

            # PID-3: Patient ID (MRN)
            mrn = self._get_field_value(pid, "pid_3")
            if not mrn:
                errors.append("PID segment missing patient ID (PID-3)")
                return None

            # Extract first component if composite
            if "^" in mrn:
                mrn = mrn.split("^")[0]

            patient = ParsedPatient(mrn=mrn)

            # PID-5: Patient Name (Family^Given^Middle)
            name = self._get_field_value(pid, "pid_5")
            if name:
                parts = name.split("^")
                patient.name_family = parts[0] if parts else None
                patient.name_given = parts[1] if len(parts) > 1 else None

            # PID-7: Date of Birth
            dob_str = self._get_field_value(pid, "pid_7")
            if dob_str:
                patient.date_of_birth = self._parse_date(dob_str)

            # PID-8: Gender
            patient.gender = self._get_field_value(pid, "pid_8")

            return patient

        except Exception as e:
            errors.append(f"Error parsing PID: {str(e)}")
            return None

    def _parse_pv1(self, msg: Message, errors: list[str]) -> ParsedEncounter | None:
        """Extract encounter information from PV1 segment."""
        try:
            pv1 = self._get_segment(msg, "PV1")
            if not pv1:
                return None

            # PV1-19: Visit Number (hl7apy may map this to pv1_18 or pv1_19 depending on empty fields)
            visit_number = self._get_field_value(pv1, "pv1_19")
            if not visit_number:
                # Try alternative field position (hl7apy sometimes shifts due to empty fields)
                visit_number = self._get_field_value(pv1, "pv1_18")

            if not visit_number:
                # Search all fields for something that looks like a visit number
                visit_number = self._find_visit_number(pv1)

            if not visit_number:
                errors.append("PV1 segment missing visit number (PV1-19)")
                return None

            # Extract first component if composite
            if "^" in visit_number:
                visit_number = visit_number.split("^")[0]

            encounter = ParsedEncounter(visit_number=visit_number)

            # PV1-2: Patient Class (I=inpatient, O=outpatient, E=emergency, etc.)
            patient_class = self._get_field_value(pv1, "pv1_2")
            encounter.encounter_type = self._map_patient_class(patient_class)

            # PV1-7: Attending Physician
            attending = self._get_field_value(pv1, "pv1_7")
            if attending:
                parts = attending.split("^")
                encounter.attending_physician_id = parts[0] if parts else None
                if len(parts) > 1:
                    encounter.attending_physician = f"{parts[1]} {parts[2]}" if len(parts) > 2 else parts[1]

            # PV1-10: Hospital Service
            encounter.hospital_service = self._get_field_value(pv1, "pv1_10")

            # PV1-44: Admit Date/Time (may shift to 43 in hl7apy)
            admit_str = self._get_field_value(pv1, "pv1_44") or self._get_field_value(pv1, "pv1_43")
            if admit_str:
                encounter.admit_datetime = self._parse_datetime(admit_str)

            # PV1-45: Discharge Date/Time (may shift to 44 in hl7apy)
            discharge_str = self._get_field_value(pv1, "pv1_45") or self._get_field_value(pv1, "pv1_44")
            # Avoid using admit datetime as discharge
            if discharge_str and discharge_str == admit_str:
                discharge_str = self._get_field_value(pv1, "pv1_45")
            if discharge_str:
                encounter.discharge_datetime = self._parse_datetime(discharge_str)

            return encounter

        except Exception as e:
            errors.append(f"Error parsing PV1: {str(e)}")
            return None

    def _find_visit_number(self, pv1: Segment) -> str | None:
        """Search PV1 fields for visit number (contains VISIT identifier pattern)."""
        for i in range(15, 25):
            val = self._get_field_value(pv1, f"pv1_{i}")
            if val and ("VISIT" in val.upper() or val.startswith("V")):
                return val
        return None

    def _parse_dg1_segments(self, msg: Message, errors: list[str]) -> list[ParsedDiagnosis]:
        """Extract diagnoses from DG1 segments."""
        diagnoses = []
        try:
            for segment in self._get_segments(msg, "DG1"):
                diag = ParsedDiagnosis()

                # DG1-1: Set ID
                set_id = self._get_field_value(segment, "dg1_1")
                if set_id:
                    try:
                        diag.set_id = int(set_id)
                    except ValueError:
                        pass

                # DG1-3: Diagnosis Code
                code = self._get_field_value(segment, "dg1_3")
                if code:
                    parts = code.split("^")
                    diag.diagnosis_code = parts[0] if parts else None
                    diag.diagnosis_description = parts[1] if len(parts) > 1 else None
                    diag.coding_method = parts[2] if len(parts) > 2 else None

                # DG1-6: Diagnosis Type
                diag.diagnosis_type = self._get_field_value(segment, "dg1_6")

                diagnoses.append(diag)

        except Exception as e:
            errors.append(f"Error parsing DG1 segments: {str(e)}")

        return diagnoses

    def _parse_pr1_segments(self, msg: Message, errors: list[str]) -> list[ParsedProcedure]:
        """Extract procedures from PR1 segments."""
        procedures = []
        try:
            for segment in self._get_segments(msg, "PR1"):
                proc = ParsedProcedure()

                # PR1-1: Set ID
                set_id = self._get_field_value(segment, "pr1_1")
                if set_id:
                    try:
                        proc.set_id = int(set_id)
                    except ValueError:
                        pass

                # PR1-3: Procedure Code
                code = self._get_field_value(segment, "pr1_3")
                if code:
                    parts = code.split("^")
                    proc.procedure_code = parts[0] if parts else None
                    proc.procedure_description = parts[1] if len(parts) > 1 else None

                # PR1-5: Procedure Date/Time
                dt_str = self._get_field_value(segment, "pr1_5")
                if dt_str:
                    proc.procedure_datetime = self._parse_datetime(dt_str)

                # PR1-8: Surgeon
                surgeon = self._get_field_value(segment, "pr1_8")
                if surgeon:
                    parts = surgeon.split("^")
                    proc.performing_physician_id = parts[0] if parts else None
                    if len(parts) > 1:
                        proc.performing_physician = f"{parts[1]} {parts[2]}" if len(parts) > 2 else parts[1]

                procedures.append(proc)

        except Exception as e:
            errors.append(f"Error parsing PR1 segments: {str(e)}")

        return procedures

    def _parse_obx_segments(self, msg: Message, errors: list[str]) -> list[ParsedObservation]:
        """Extract observations from OBX segments."""
        observations = []
        try:
            for segment in self._get_segments(msg, "OBX"):
                obs = ParsedObservation()

                # OBX-1: Set ID
                set_id = self._get_field_value(segment, "obx_1")
                if set_id:
                    try:
                        obs.set_id = int(set_id)
                    except ValueError:
                        pass

                # OBX-3: Observation Identifier
                identifier = self._get_field_value(segment, "obx_3")
                if identifier:
                    parts = identifier.split("^")
                    obs.observation_identifier = parts[0] if parts else None
                    obs.observation_identifier_text = parts[1] if len(parts) > 1 else None

                # OBX-5: Observation Value
                obs.observation_value = self._get_field_value(segment, "obx_5")

                # OBX-6: Units
                obs.units = self._get_field_value(segment, "obx_6")

                # OBX-7: Reference Range
                obs.reference_range = self._get_field_value(segment, "obx_7")

                # OBX-8: Abnormal Flags
                obs.abnormal_flags = self._get_field_value(segment, "obx_8")

                # OBX-11: Observation Result Status
                obs.result_status = self._get_field_value(segment, "obx_11")

                # OBX-14: Date/Time of Observation
                dt_str = self._get_field_value(segment, "obx_14")
                if dt_str:
                    obs.observation_datetime = self._parse_datetime(dt_str)

                observations.append(obs)

        except Exception as e:
            errors.append(f"Error parsing OBX segments: {str(e)}")

        return observations

    def _parse_order_segments(self, msg: Message, errors: list[str]) -> list[ParsedOrder]:
        """Extract orders from ORC and OBR segments."""
        orders = []
        try:
            # Get all ORC segments
            orc_segments = list(self._get_segments(msg, "ORC"))
            obr_segments = list(self._get_segments(msg, "OBR"))

            # Match ORC with OBR (they usually appear in pairs)
            for i, orc in enumerate(orc_segments):
                order = ParsedOrder()

                # ORC-1: Order Control
                order.order_control = self._get_field_value(orc, "orc_1")

                # ORC-2: Placer Order Number
                order.placer_order_number = self._get_field_value(orc, "orc_2")

                # ORC-3: Filler Order Number
                order.filler_order_number = self._get_field_value(orc, "orc_3")

                # ORC-5: Order Status
                order.order_status = self._get_field_value(orc, "orc_5")

                # ORC-9: Date/Time of Transaction
                dt_str = self._get_field_value(orc, "orc_9")
                if dt_str:
                    order.order_datetime = self._parse_datetime(dt_str)

                # ORC-12: Ordering Provider
                provider = self._get_field_value(orc, "orc_12")
                if provider:
                    parts = provider.split("^")
                    order.ordering_provider_id = parts[0] if parts else None
                    if len(parts) > 1:
                        order.ordering_provider = f"{parts[1]} {parts[2]}" if len(parts) > 2 else parts[1]

                # Try to get corresponding OBR
                if i < len(obr_segments):
                    obr = obr_segments[i]
                    self._parse_obr_into_order(obr, order)

                orders.append(order)

            # Handle OBR segments without matching ORC
            if len(obr_segments) > len(orc_segments):
                for obr in obr_segments[len(orc_segments):]:
                    order = ParsedOrder()
                    order.placer_order_number = self._get_field_value(obr, "obr_2")
                    order.filler_order_number = self._get_field_value(obr, "obr_3")
                    self._parse_obr_into_order(obr, order)
                    orders.append(order)

        except Exception as e:
            errors.append(f"Error parsing ORC/OBR segments: {str(e)}")

        return orders

    def _parse_obr_into_order(self, obr: Segment, order: ParsedOrder) -> None:
        """Parse OBR segment fields into order object."""
        # OBR-4: Universal Service ID
        service_id = self._get_field_value(obr, "obr_4")
        if service_id:
            parts = service_id.split("^")
            order.order_type_code = parts[0] if parts else None
            order.order_type = parts[1] if len(parts) > 1 else None

        # OBR-24: Diagnostic Service Section ID
        # hl7apy may shift field positions, so check multiple potential locations
        diag_section = self._get_field_value(obr, "obr_24")
        if not diag_section or len(diag_section) <= 2:
            # Try obr_30 which sometimes contains the diagnostic section
            diag_section = self._get_field_value(obr, "obr_30")
        if not diag_section:
            # Search for common diagnostic section codes
            diag_section = self._find_diagnostic_section(obr)

        order.diagnostic_service_section = diag_section

    def _find_diagnostic_section(self, obr: Segment) -> str | None:
        """Search OBR fields for diagnostic service section."""
        known_sections = {"LAB", "RAD", "CARD", "PATH", "NUC", "MRI", "CT", "US"}
        for i in range(20, 35):
            val = self._get_field_value(obr, f"obr_{i}")
            if val and val.upper() in known_sections:
                return val.upper()
        return None

    def _parse_document_segments(self, msg: Message, errors: list[str]) -> list[ParsedDocument]:
        """Extract documents from TXA segment (MDM messages)."""
        documents = []
        try:
            for segment in self._get_segments(msg, "TXA"):
                doc = ParsedDocument()

                # TXA-2: Document Type
                doc_type = self._get_field_value(segment, "txa_2")
                if doc_type:
                    parts = doc_type.split("^")
                    doc.document_type_code = parts[0] if parts else None
                    doc.document_type = parts[1] if len(parts) > 1 else None

                # TXA-17: Document Completion Status
                doc.document_status = self._get_field_value(segment, "txa_17")

                # TXA-4: Activity Date/Time
                dt_str = self._get_field_value(segment, "txa_4")
                if dt_str:
                    doc.origination_datetime = self._parse_datetime(dt_str)

                # TXA-9: Originator Code/Name
                author = self._get_field_value(segment, "txa_9")
                if author:
                    parts = author.split("^")
                    doc.author_id = parts[0] if parts else None
                    if len(parts) > 1:
                        doc.author = f"{parts[1]} {parts[2]}" if len(parts) > 2 else parts[1]

                # Get document content from associated OBX segments
                # (typically OBX-5 with value type TX or FT)
                content_parts = []
                for obx in self._get_segments(msg, "OBX"):
                    value_type = self._get_field_value(obx, "obx_2")
                    if value_type in ("TX", "FT", "ST"):
                        content = self._get_field_value(obx, "obx_5")
                        if content:
                            content_parts.append(content)

                if content_parts:
                    doc.content = "\n".join(content_parts)

                documents.append(doc)

        except Exception as e:
            errors.append(f"Error parsing TXA segments: {str(e)}")

        return documents

    def _get_segment(self, msg: Message, segment_name: str) -> Segment | None:
        """Get first segment of given type from message."""
        try:
            segments = list(self._get_segments(msg, segment_name))
            return segments[0] if segments else None
        except Exception:
            return None

    def _get_segments(self, msg: Message, segment_name: str):
        """Yield all segments of given type from message."""
        try:
            for child in msg.children:
                if hasattr(child, "name") and child.name.upper() == segment_name.upper():
                    yield child
        except Exception:
            pass

    def _get_field_value(self, segment: Segment, field_name: str) -> str | None:
        """Safely get field value from segment."""
        try:
            field = getattr(segment, field_name, None)
            if field is None:
                return None

            # Get the string value
            value = str(field.value) if hasattr(field, "value") else str(field)

            # Clean up empty values
            if value in ("", '""', "None"):
                return None

            return value.strip()
        except Exception:
            return None

    def _parse_datetime(self, dt_str: str) -> datetime | None:
        """Parse HL7 datetime format (YYYYMMDD[HHMM[SS[.S[S[S[S]]]]]][+/-ZZZZ])."""
        if not dt_str:
            return None

        # Remove timezone offset if present
        dt_str = dt_str.split("+")[0].split("-")[0]

        # Try various formats
        formats = [
            "%Y%m%d%H%M%S.%f",
            "%Y%m%d%H%M%S",
            "%Y%m%d%H%M",
            "%Y%m%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(dt_str[:len(datetime.now().strftime(fmt))], fmt)
            except ValueError:
                continue

        return None

    def _parse_date(self, dt_str: str) -> date | None:
        """Parse HL7 date format (YYYYMMDD)."""
        if not dt_str or len(dt_str) < 8:
            return None

        try:
            return datetime.strptime(dt_str[:8], "%Y%m%d").date()
        except ValueError:
            return None

    def _map_patient_class(self, code: str | None) -> str | None:
        """Map HL7 patient class code to encounter type."""
        if not code:
            return None

        mapping = {
            "I": "inpatient",
            "O": "outpatient",
            "E": "emergency",
            "P": "preadmit",
            "R": "recurring",
            "B": "observation",
        }
        return mapping.get(code.upper(), code)


class HL7BatchParser:
    """Parser for batch HL7 files containing multiple messages."""

    def __init__(self):
        self.parser = HL7Parser()

    def parse_file_content(self, content: str) -> list[ParsedHL7Message]:
        """
        Parse file content containing one or more HL7 messages.

        Args:
            content: File content (may contain multiple messages)

        Returns:
            List of parsed messages
        """
        messages = self._split_messages(content)
        return [self.parser.parse(msg) for msg in messages if msg.strip()]

    def _split_messages(self, content: str) -> list[str]:
        """Split batch content into individual messages."""
        # Normalize line endings
        normalized = content.replace("\r\n", "\r").replace("\n", "\r")

        # Find all MSH segment starts
        matches = list(MESSAGE_START_PATTERN.finditer(normalized))

        if not matches:
            # No MSH found, return as single message (may be invalid)
            return [normalized] if normalized.strip() else []

        messages = []
        for i, match in enumerate(matches):
            # Get the actual start of MSH (skip the optional \r prefix)
            start = match.start()
            if normalized[start] == "\r":
                start += 1

            # End is either the start of next message or end of content
            if i + 1 < len(matches):
                end = matches[i + 1].start()
                if normalized[end] == "\r":
                    end += 1
            else:
                end = len(normalized)

            msg = normalized[start:end].strip()
            if msg:
                messages.append(msg)

        return messages
