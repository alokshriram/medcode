# Requirements Gap Analysis - HL7 to Codable Packet Generation

**Generated:** January 2026
**Compared Against:** `.plans/requirements.md` v1.0
**Codebase Analyzed:** `feature/multi-tenancy` branch

---

## Executive Summary

This document identifies gaps between the product specification (requirements.md) and the current implementation. Each gap includes implementation context and recommended fixes based on existing codebase patterns.

### Gap Severity Legend
- **CRITICAL** - Blocks core V1 functionality
- **HIGH** - Impacts data completeness or workflow accuracy
- **MEDIUM** - Missing message types or secondary features
- **LOW** - Configuration/UX enhancements

---

## Critical Gaps

### GAP-001: NPI Provider Registry Missing

**Severity:** CRITICAL
**Spec Reference:** Section "Data Models > 1. NPI Provider Registry"

**What's Missing:**
- No `NPIProvider` model exists
- No provider employment types (`HOSPITAL_EMPLOYED`, `INDEPENDENT_CONTRACTOR`, `HOSPITAL_PRIVILEGES_ONLY`, `LOCUM_TENENS`)
- No provider roster management (import, CRUD, activation)
- Provider info currently stored as simple strings in clinical records

**Current State:**
- `Procedure.performing_physician` - string field (255 chars)
- `Order.ordering_provider` - string field (255 chars)
- `ParsedEncounter.attending_physician` / `attending_physician_id` - extracted from HL7 but not validated
- No NPI validation or lookup

**Impact:**
- Cannot determine if attending provider is hospital-employed
- Cannot route ProFee packets based on provider employment type
- No way to exclude independent contractors from ProFee queue

**Recommended Fix:**

1. Create new model in `app/domains/users/models.py` (providers are identity-related):

```python
class EmploymentType(str, Enum):
    HOSPITAL_EMPLOYED = "HOSPITAL_EMPLOYED"
    INDEPENDENT_CONTRACTOR = "INDEPENDENT_CONTRACTOR"
    HOSPITAL_PRIVILEGES_ONLY = "HOSPITAL_PRIVILEGES_ONLY"
    LOCUM_TENENS = "LOCUM_TENENS"

class NPIProvider(Base):
    __tablename__ = "npi_providers"
    __table_args__ = {"schema": "users"}

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=True, index=True)
    npi = Column(String(10), nullable=False, index=True)  # 10-digit NPI

    # From NPPES
    first_name = Column(String(100))
    last_name = Column(String(100))
    credential = Column(String(20))  # "MD", "DO", "NP", "PA"
    taxonomy_code = Column(String(20))
    specialty = Column(String(100))

    # Hospital-specific
    employment_type = Column(SQLEnum(EmploymentType), default=EmploymentType.HOSPITAL_EMPLOYED)
    is_active = Column(Boolean, default=True)

    # Billing
    individual_npi = Column(String(10))
    billing_npi = Column(String(10), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('tenant_id', 'npi', name='uq_tenant_npi'),
        {"schema": "users"}
    )
```

2. Add provider service in `app/domains/users/provider_service.py`:
   - `get_provider_by_npi(npi, tenant_id)`
   - `is_hospital_employed(npi, tenant_id)` - returns bool
   - `import_provider_roster(csv_file, tenant_id)` - bulk import
   - `create_provider()`, `update_provider()`, `deactivate_provider()`

3. Add API routes for provider management (admin only)

4. Update `CodingQueueService.create_queue_items_for_encounter()` to check provider employment before creating ProFee items

**Files to Create/Modify:**
- `app/domains/users/models.py` - add NPIProvider
- `app/domains/users/provider_service.py` - new file
- `app/domains/users/provider_schemas.py` - new file
- `app/domains/users/router.py` - add provider endpoints
- `app/domains/workflow/coding_queue_service.py` - check provider employment
- `alembic/versions/YYYYMMDD_add_npi_providers.py` - new migration

---

### GAP-002: Charge Capture (DFT^P03) Not Implemented

**Severity:** CRITICAL
**Spec Reference:** Section "Data Models > 5. Charge Capture Table" and "HL7 Message Processing > DFT^P03"

**What's Missing:**
- No `Charge` model
- No DFT^P03 message parsing
- No charge types (FACILITY, PROFEE, BOTH)
- No revenue codes, procedure codes on charges
- No coding status tracking (UNCODED, AUTO_CODED, HUMAN_CODED, VALIDATED)

**Current State:**
- HL7 parser (`app/domains/encounters/hl7/parser.py`) does not handle FT1 segments
- No financial transaction data captured
- Codable packets have no charges to code

**Impact:**
- Coders have no charges to assign codes to
- Cannot split facility vs professional component charges
- Cannot track pre-coded vs uncoded charges

**Recommended Fix:**

1. Add `Charge` model to `app/domains/encounters/models.py`:

```python
class ChargeType(str, Enum):
    FACILITY = "FACILITY"
    PROFEE = "PROFEE"
    BOTH = "BOTH"

class CodingStatus(str, Enum):
    UNCODED = "UNCODED"
    AUTO_CODED = "AUTO_CODED"
    HUMAN_CODED = "HUMAN_CODED"
    VALIDATED = "VALIDATED"

class Charge(Base):
    __tablename__ = "charges"
    __table_args__ = {"schema": "encounters"}

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=True, index=True)
    encounter_id = Column(UUID, ForeignKey("encounters.encounters.id"), nullable=False, index=True)
    hl7_message_id = Column(UUID, ForeignKey("encounters.hl7_messages.id"), nullable=True)

    # From FT1 segment
    transaction_id = Column(String(50))  # FT1-1
    transaction_type = Column(String(10))  # FT1-6 ("CG", "CD")
    transaction_code = Column(String(50))  # FT1-7.1
    transaction_description = Column(String(255))  # FT1-7.2

    # Financial
    transaction_quantity = Column(Integer, default=1)
    transaction_amount = Column(Numeric(12, 2))
    total_charge_amount = Column(Numeric(12, 2))

    # Clinical coding
    procedure_code = Column(String(20), nullable=True)  # FT1-25 CPT/HCPCS
    procedure_modifier = Column(String(10), nullable=True)
    diagnosis_code = Column(String(20), nullable=True)  # FT1-19 ICD-10

    # Billing classification
    charge_type = Column(SQLEnum(ChargeType), default=ChargeType.FACILITY)
    revenue_code = Column(String(10), nullable=True)  # UB-04

    # Provider
    performing_provider_npi = Column(String(10), nullable=True)

    # Status
    coding_status = Column(SQLEnum(CodingStatus), default=CodingStatus.UNCODED)

    # Dates
    service_date = Column(Date)
    posted_datetime = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    encounter = relationship("Encounter", back_populates="charges")
```

2. Add FT1 parsing to `app/domains/encounters/hl7/parser.py`:
   - Parse FT1 segments (can be multiple per message)
   - Extract all fields per spec
   - Add `ParsedCharge` to `types.py`

3. Add `process_dft_p03()` to `app/domains/encounters/service.py`:
   - Find encounter by PV1-19
   - Create Charge records for each FT1 segment
   - Determine charge type based on revenue code and modifier

4. Include charges in snapshot data

**Files to Create/Modify:**
- `app/domains/encounters/models.py` - add Charge model
- `app/domains/encounters/schemas.py` - add ChargeResponse, ChargeCreate
- `app/domains/encounters/hl7/parser.py` - add FT1 parsing
- `app/domains/encounters/hl7/types.py` - add ParsedCharge
- `app/domains/encounters/service.py` - add charge processing
- `app/domains/workflow/coding_queue_service.py` - include charges in snapshot
- `alembic/versions/YYYYMMDD_add_charges.py` - new migration

---

### GAP-003: ProFee Routing Based on Provider Employment

**Severity:** CRITICAL
**Spec Reference:** Section "Codable Packet Generation Logic" and `should_create_profee_packet()`

**What's Missing:**
- ProFee packet creation should check if attending provider is `HOSPITAL_EMPLOYED`
- Current implementation only uses service line configuration
- No `should_create_profee_packet()` function per spec

**Current State:**
In `app/domains/workflow/coding_queue_service.py`:
```python
def create_queue_items_for_encounter(self, encounter, triggered_by):
    # Creates professional item based on:
    # 1. always_create_professional config flag
    # 2. Service line in professional_component_services
    # 3. Presence of performing physician in procedures
```

**Spec Requirement:**
```python
def should_create_profee_packet(encounter: Encounter) -> bool:
    # Check if attending provider is HOSPITAL_EMPLOYED
    provider = db.query(NPIProvider).filter_by(
        npi=encounter.attending_provider_npi
    ).first()
    return provider.employment_type == EmploymentType.HOSPITAL_EMPLOYED
```

**Impact:**
- ProFee packets created for encounters where physician is independent contractor
- ProFee packets NOT created when they should be (if service line doesn't match but provider is employed)

**Recommended Fix:**

1. After implementing GAP-001 (NPI Provider Registry), update `CodingQueueService`:

```python
def _should_create_professional_item(self, encounter) -> bool:
    """
    Business rule: Create ProFee item if attending provider is hospital-employed
    """
    # Check config flag first
    if self.get_config_bool("always_create_professional", False):
        return True

    # Check provider employment type (primary rule per spec)
    if encounter.attending_provider_npi:
        provider_service = ProviderService(self.db)
        if provider_service.is_hospital_employed(
            encounter.attending_provider_npi,
            encounter.tenant_id
        ):
            return True

    # Fallback to service line check
    professional_services = self.get_config_list("professional_component_services", [])
    if encounter.service_line and encounter.service_line.lower() in [s.lower() for s in professional_services]:
        return True

    return False
```

2. Add `attending_provider_npi` field to Encounter model (see GAP-004)

**Files to Modify:**
- `app/domains/workflow/coding_queue_service.py` - update professional item logic
- `app/domains/encounters/models.py` - add attending_provider_npi field

**Dependencies:**
- Requires GAP-001 (NPI Provider Registry) to be implemented first
- Requires GAP-004 (Missing Encounter Fields) for attending_provider_npi

---

## High Severity Gaps

### GAP-004: Missing Encounter Fields

**Severity:** HIGH
**Spec Reference:** Section "Data Models > 2. Encounter Table"

**What's Missing from Encounter Model:**

| Field | Spec | Current | Notes |
|-------|------|---------|-------|
| `account_number` | PID-18 or PV1-50 | Missing | Financial linkage |
| `admission_type` | PV1-4 | Missing | "1" (Emergency), "2" (Urgent), "3" (Elective) |
| `current_location` | PV1-3 | Missing | Bed/room tracking |
| `attending_provider_npi` | PV1-7 | Missing | Critical for ProFee routing |
| `admitting_provider_npi` | PV1-17 | Missing | For provider snapshot |
| `referring_provider_npi` | PV1-8 | Missing | For provider snapshot |
| `primary_payer` | IN1-4 | Missing | Insurance company |
| `primary_policy_number` | IN1-36 | Missing | Policy number |
| `facility_coding_required` | Calculated | Missing | Business rule flag |
| `profee_coding_required` | Calculated | Missing | Business rule flag |
| `discharge_disposition` | PV1-36 | Missing | "01" (home), "03" (SNF), etc. |

**Current State:**
`app/domains/encounters/models.py` has:
- `visit_number` (PV1-19)
- `encounter_type` (patient class from PV1-2)
- `service_line` (derived)
- `payer_identifier` (basic)
- `admit_datetime`, `discharge_datetime`
- `status`

**Recommended Fix:**

1. Add missing columns to Encounter model:

```python
# In app/domains/encounters/models.py, add to Encounter class:

# Financial
account_number = Column(String(50), nullable=True)

# Admission details
admission_type = Column(String(10), nullable=True)  # "1", "2", "3"
current_location = Column(String(50), nullable=True)  # Bed/room
discharge_disposition = Column(String(10), nullable=True)  # "01", "03", etc.

# Providers (NPI references)
attending_provider_npi = Column(String(10), nullable=True, index=True)
admitting_provider_npi = Column(String(10), nullable=True)
referring_provider_npi = Column(String(10), nullable=True)

# Insurance (from IN1 segment)
primary_payer = Column(String(100), nullable=True)
primary_policy_number = Column(String(50), nullable=True)

# Coding workflow flags
facility_coding_required = Column(Boolean, default=True)
profee_coding_required = Column(Boolean, default=False)
```

2. Update HL7 parser to extract these fields:
   - `app/domains/encounters/hl7/parser.py` - extract from PV1, PID, IN1 segments
   - `app/domains/encounters/hl7/types.py` - add fields to ParsedEncounter

3. Update service to populate fields:
   - `app/domains/encounters/service.py` - `get_or_create_encounter()` to set all fields

**Files to Modify:**
- `app/domains/encounters/models.py`
- `app/domains/encounters/schemas.py`
- `app/domains/encounters/hl7/parser.py`
- `app/domains/encounters/hl7/types.py`
- `app/domains/encounters/service.py`
- `alembic/versions/YYYYMMDD_add_encounter_fields.py`

---

### GAP-005: Missing Order Fields for Billing Relevance

**Severity:** HIGH
**Spec Reference:** Section "Data Models > 4. Order Tracking Table"

**What's Missing from Order Model:**

| Field | Purpose | Notes |
|-------|---------|-------|
| `billable_to_facility` | Flag for facility charges | Almost always true for ancillary |
| `billable_to_profee` | Flag for physician interpretation | True for radiology, cardiology, etc. |
| `has_results` | ORU received flag | Links order to results |
| `result_interpretation` | "Normal", "Abnormal", "Critical" | From OBX-8 flags |

**Current State:**
`app/domains/encounters/models.py` Order model has:
- `order_control`, `placer_order_number`, `filler_order_number`
- `order_status`, `order_type`
- `diagnostic_service_section`
- `ordering_provider`

**Impact:**
- Cannot determine which orders require ProFee interpretation coding
- Cannot include only billable orders in appropriate packets

**Recommended Fix:**

1. Add fields to Order model:

```python
# In app/domains/encounters/models.py Order class:

billable_to_facility = Column(Boolean, default=True)
billable_to_profee = Column(Boolean, default=False)
has_results = Column(Boolean, default=False)
result_interpretation = Column(String(20), nullable=True)  # "Normal", "Abnormal", "Critical"
```

2. Add logic to determine `billable_to_profee`:

```python
# In app/domains/encounters/service.py

PROFEE_INTERPRETATION_SERVICES = [
    'RAD', 'US', 'ECHO', 'EKG', 'STRESS', 'PFT', 'SLEEP', 'HOLTER', 'EEG'
]

def _requires_physician_interpretation(self, service_id: str) -> bool:
    return any(service_id.upper().startswith(prefix) for prefix in PROFEE_INTERPRETATION_SERVICES)
```

3. Update ORU processing to link results back to orders and set `has_results`, `result_interpretation`

**Files to Modify:**
- `app/domains/encounters/models.py`
- `app/domains/encounters/service.py`
- `alembic/versions/YYYYMMDD_add_order_billing_fields.py`

---

### GAP-006: Structured Snapshot Data Format

**Severity:** HIGH
**Spec Reference:** Section "Data Models > 6. Codable Packet Table" - clinical_data, orders_data, charges_data structures

**What's Missing:**
Spec defines specific JSON structures for packet data:
- `clinical_data` with `encounter_summary`, `diagnoses_indicators`, `payer_info`
- `orders_data` with billing relevance flags
- `charges_data` with coding status
- `provider_data` with attending/admitting/referring

**Current State:**
`app/domains/workflow/coding_queue_service.py` `_create_encounter_snapshot_data()` creates a generic structure:
```python
{
    "patient": {...},
    "encounter": {...},
    "diagnoses": [...],
    "procedures": [...],
    "observations": [...],
    "orders": [...],
    "documents": [...],
    "snapshot_timestamp": "..."
}
```

**Impact:**
- Frontend/coders don't have spec-defined data organization
- Missing calculated fields like `length_of_stay`, `age`
- Missing provider employment context

**Recommended Fix:**

Update `_create_encounter_snapshot_data()` to match spec structure:

```python
def _create_encounter_snapshot_data(self, encounter) -> dict:
    return {
        "clinical_data": {
            "encounter_summary": {
                "pv_id": encounter.visit_number,
                "mrn": encounter.patient.mrn,
                "admit_date": encounter.admit_datetime.isoformat(),
                "discharge_date": encounter.discharge_datetime.isoformat() if encounter.discharge_datetime else None,
                "length_of_stay": self._calculate_los(encounter),
                "patient_class": encounter.encounter_type,
                "admission_type": encounter.admission_type,
                "hospital_service": encounter.service_line,
                "discharge_disposition": encounter.discharge_disposition,
                "attending_provider": self._get_provider_snapshot(encounter.attending_provider_npi)
            },
            "patient_demographics": {
                "name": f"{encounter.patient.family_name}, {encounter.patient.given_name}",
                "dob": encounter.patient.date_of_birth.isoformat(),
                "sex": encounter.patient.gender,
                "age": self._calculate_age(encounter.patient.date_of_birth, encounter.admit_datetime)
            },
            "diagnoses_indicators": {
                "documented_diagnoses": [...],
                "lab_indicators": [...]
            },
            "payer_info": {
                "primary_payer": encounter.primary_payer,
                "policy_number": encounter.primary_policy_number
            }
        },
        "orders_data": [...],  # With billable_to_facility, billable_to_profee
        "charges_data": [...],  # With coding_status, revenue_code
        "provider_data": {
            "attending_npi": encounter.attending_provider_npi,
            "admitting_npi": encounter.admitting_provider_npi,
            "referring_npi": encounter.referring_provider_npi
        },
        "hospital_configuration": {...},  # Capture active rules
        "snapshot_timestamp": datetime.utcnow().isoformat()
    }
```

**Files to Modify:**
- `app/domains/workflow/coding_queue_service.py`

**Dependencies:**
- Requires GAP-004 (Missing Encounter Fields)
- Requires GAP-005 (Missing Order Fields)
- Requires GAP-002 (Charge Capture)

---

## Medium Severity Gaps

### GAP-007: ADT Message Types Not Handled

**Severity:** MEDIUM
**Spec Reference:** Section "HL7 Message Processing Rules > Message Type Handling Matrix"

**Missing Message Type Handlers:**

| Message | Purpose | Current Status |
|---------|---------|----------------|
| ADT^A08 | Update patient info | Not implemented |
| ADT^A02 | Patient transfer | Not implemented |
| ADT^A06 | Outpatient to Inpatient | Not implemented |
| ADT^A11 | Cancel admit | Not implemented |

**Current State:**
`app/domains/encounters/hl7/parser.py` parses message type but service doesn't differentiate handling:
```python
# parser.py extracts:
message_type = msh_segment[9][0][1].value  # e.g., "ADT"
event_type = msh_segment[9][0][2].value    # e.g., "A01", "A03"
```

`app/domains/encounters/service.py` `process_hl7_message()` treats all messages the same.

**Recommended Fix:**

1. Add message type routing in service:

```python
def process_hl7_message(self, parsed_message: ParsedHL7Message, ...):
    # Store raw message (existing)

    # Route based on message type
    event_type = parsed_message.event_type

    if event_type == "A01":
        return self._process_admit(parsed_message, ...)
    elif event_type == "A03":
        return self._process_discharge(parsed_message, ...)
    elif event_type == "A04":
        return self._process_registration(parsed_message, ...)
    elif event_type == "A08":
        return self._process_update(parsed_message, ...)
    elif event_type == "A02":
        return self._process_transfer(parsed_message, ...)
    elif event_type == "A06":
        return self._process_class_change(parsed_message, ...)
    elif event_type == "A11":
        return self._process_cancel(parsed_message, ...)
    else:
        logger.warning(f"Unhandled message type: {event_type}")
```

2. Implement each handler:
   - `_process_update()` - update demographics, insurance
   - `_process_transfer()` - update location
   - `_process_class_change()` - change patient_class, recalculate coding requirements
   - `_process_cancel()` - set encounter status to CANCELLED, cancel any pending queue items

**Files to Modify:**
- `app/domains/encounters/service.py`

---

### GAP-008: Order-Result Linkage (ORU to ORM)

**Severity:** MEDIUM
**Spec Reference:** Section "HL7 Message Processing > ORU^R01"

**What's Missing:**
- ORU results not linked back to ORM orders
- No mechanism to update Order with results
- `has_results` and `result_interpretation` not set

**Current State:**
- `Observation` model stores OBX data independently
- No `order_id` foreign key on Observation
- Orders and Observations both linked to encounter but not to each other

**Recommended Fix:**

1. Add order linkage to Observation:

```python
# In models.py Observation class:
order_id = Column(UUID, ForeignKey("encounters.orders.id"), nullable=True)
order = relationship("Order", back_populates="observations")
```

2. Update ORU processing to find and update order:

```python
def _process_oru_result(self, parsed_message, encounter):
    # Find order by filler_order_number (OBR-3)
    filler_number = parsed_message.orders[0].filler_order_number if parsed_message.orders else None

    if filler_number:
        order = self.db.query(Order).filter_by(
            encounter_id=encounter.id,
            filler_order_number=filler_number
        ).first()

        if order:
            order.has_results = True
            order.result_interpretation = self._determine_interpretation(parsed_message.observations)

            # Link observations to order
            for obs in observations:
                obs.order_id = order.id
```

**Files to Modify:**
- `app/domains/encounters/models.py`
- `app/domains/encounters/service.py`
- `alembic/versions/YYYYMMDD_add_observation_order_link.py`

---

### GAP-009: HL7 Ingestion REST API Endpoint

**Severity:** MEDIUM
**Spec Reference:** Section "Technical Implementation Guide > API Endpoint Specification"

**What's Missing:**
Spec defines: `POST /v1/hl7/ingest` accepting raw HL7 text
Current implementation only has file upload: `POST /encounters/upload`

**Current State:**
`app/domains/encounters/router.py`:
```python
@router.post("/upload", response_model=UploadResult)
async def upload_hl7_files(files: List[UploadFile], ...)
```

**Spec Requirement:**
```
POST /v1/hl7/ingest
Content-Type: text/plain

{raw_hl7_message}
```

**Recommended Fix:**

Add single-message ingestion endpoint:

```python
@router.post("/ingest", response_model=HL7IngestResponse)
async def ingest_hl7_message(
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    tenant_context: OptionalTenantContextDep = None
):
    """
    Ingest a single HL7 message (for real-time Mirth integration)
    """
    raw_message = await request.body()
    raw_message = raw_message.decode('utf-8')

    service = EncountersService(db, tenant_context)
    parser = HL7Parser()

    parsed = parser.parse_message(raw_message)
    result = service.process_hl7_message(parsed, raw_message, ...)

    return HL7IngestResponse(
        status="success",
        message_id=result.hl7_message_id,
        message_type=parsed.message_type,
        encounter_id=result.encounter_id
    )
```

**Files to Modify:**
- `app/domains/encounters/router.py`
- `app/domains/encounters/schemas.py` - add HL7IngestResponse

---

## Low Severity Gaps

### GAP-010: Per-Hospital Configuration Settings

**Severity:** LOW
**Spec Reference:** Section "Configuration Parameters > Hospital-Level Configuration"

**What's Missing:**

| Config | Purpose |
|--------|---------|
| `code_inpatient` | Always true (assumed) |
| `code_observation` | Always true (assumed) |
| `code_emergency_visits` | Per-hospital setting |
| `code_outpatient_visits` | Per-hospital setting |
| `code_outpatient_procedures` | Per-hospital setting |
| `profee_billing_model` | HOSPITAL_EMPLOYED / INDEPENDENT / HYBRID |
| `default_attending_npi` | Fallback for missing provider |
| `wait_for_charge_completeness` | V2 feature |

**Current State:**
`CodingConfiguration` table has:
- `always_create_facility`
- `always_create_professional`
- `professional_component_services`
- `encounter_timeout_hours`

**Recommended Fix:**

1. Add hospital configuration model (separate from coding config):

```python
class HospitalConfiguration(Base):
    __tablename__ = "hospital_configurations"
    __table_args__ = {"schema": "workflow"}

    id = Column(UUID, primary_key=True)
    tenant_id = Column(UUID, nullable=False, unique=True)
    hospital_name = Column(String(200))

    # Encounter type coding rules
    code_inpatient = Column(Boolean, default=True)
    code_observation = Column(Boolean, default=True)
    code_emergency_visits = Column(Boolean, default=True)
    code_outpatient_visits = Column(Boolean, default=False)
    code_outpatient_procedures = Column(Boolean, default=True)

    # ProFee model
    profee_billing_model = Column(String(50), default="HOSPITAL_EMPLOYED")

    # Defaults
    default_attending_npi = Column(String(10), nullable=True)
```

2. Update queue creation to check hospital config for encounter type rules

**Files to Create/Modify:**
- `app/domains/workflow/models.py` - add HospitalConfiguration
- `app/domains/workflow/coding_queue_service.py` - check hospital config
- `alembic/versions/YYYYMMDD_add_hospital_config.py`

---

### GAP-011: E/M Placeholder Charge Creation

**Severity:** LOW
**Spec Reference:** Section "Codable Packet Generation Logic > create_em_placeholder_charge()"

**What's Missing:**
- No automatic E/M charge creation for ProFee packets
- Coders must manually determine E/M level (99221-99223 for IP, 99281-99285 for ER)

**Current State:**
ProFee queue items created with snapshot but no placeholder charges for E/M visits.

**Recommended Fix:**

After implementing GAP-002 (Charge Capture), add:

```python
def _create_em_placeholder_charge(self, encounter) -> Charge | None:
    """Create placeholder for E/M visit coding"""

    # Check if E/M already exists
    existing = self.db.query(Charge).filter(
        Charge.encounter_id == encounter.id,
        Charge.charge_type == ChargeType.PROFEE,
        Charge.procedure_code.like('992%')
    ).first()

    if existing:
        return None

    # Determine E/M category based on patient class
    if encounter.encounter_type == 'inpatient':
        description = "Initial Hospital Care (99221-99223)"
    elif encounter.encounter_type == 'emergency':
        description = "Emergency Department Visit (99281-99285)"
    elif encounter.encounter_type == 'observation':
        description = "Observation Care (99217-99220)"
    else:
        return None

    return Charge(
        encounter_id=encounter.id,
        transaction_description=description,
        charge_type=ChargeType.PROFEE,
        coding_status=CodingStatus.UNCODED,
        performing_provider_npi=encounter.attending_provider_npi,
        service_date=encounter.admit_datetime.date()
    )
```

**Dependencies:**
- Requires GAP-002 (Charge Capture)

---

### GAP-012: Out-of-Order Message Handling

**Severity:** LOW
**Spec Reference:** Section "Edge Cases > Out-of-Order Messages"

**What's Missing:**
- Explicit handling when ADT^A03 arrives before ADT^A01
- `needs_review` flag for encounters created from discharge

**Current State:**
- Idempotent message storage works
- `get_or_create_encounter()` will create encounter from any message
- No special handling or flagging

**Recommended Fix:**

```python
def _process_discharge(self, parsed_message, ...):
    encounter = self.get_encounter_by_visit_number(parsed_message.encounter.visit_number)

    if not encounter:
        # Out-of-order: discharge before admit
        logger.warning(f"Out-of-order ADT^A03 for visit {parsed_message.encounter.visit_number}")

        encounter = self.get_or_create_encounter(parsed_message.encounter, ...)
        encounter.needs_review = True
        encounter.review_reason = "Created from discharge message (admit not received)"

    # Continue with discharge processing...
```

**Files to Modify:**
- `app/domains/encounters/models.py` - add `needs_review`, `review_reason` fields
- `app/domains/encounters/service.py` - add out-of-order detection

---

### GAP-013: Late Charge Handling

**Severity:** LOW
**Spec Reference:** Section "Edge Cases > Charges Arrive After Packet Created"

**What's Missing:**
- No mechanism to update existing snapshots with late charges
- Charges arriving after packet creation not added to packet

**Recommended Fix:**

After implementing GAP-002, add charge arrival hook:

```python
def handle_late_charge(self, charge: Charge):
    """Add late-arriving charge to existing queue items"""

    # Find queue items for this encounter that are still READY
    queue_items = self.db.query(CodingQueueItem).filter(
        CodingQueueItem.encounter_id == charge.encounter_id,
        CodingQueueItem.status == "pending"  # Not yet assigned
    ).all()

    for item in queue_items:
        if self._charge_belongs_to_item(charge, item):
            # Refresh snapshot to include new charge
            self.refresh_snapshot(item.id, triggered_by="late_charge")
            logger.info(f"Added late charge {charge.id} to queue item {item.id}")
```

**Dependencies:**
- Requires GAP-002 (Charge Capture)

---

## Implementation Priority Order

Based on dependencies and business value:

### Phase 1: Foundation (Critical)
1. **GAP-004** - Missing Encounter Fields (needed for most other fixes)
2. **GAP-001** - NPI Provider Registry (needed for ProFee routing)
3. **GAP-002** - Charge Capture (core billing functionality)

### Phase 2: Business Logic (Critical/High)
4. **GAP-003** - ProFee Routing by Provider Employment (requires GAP-001, GAP-004)
5. **GAP-005** - Order Billing Relevance Fields
6. **GAP-006** - Structured Snapshot Data (requires GAP-002, GAP-004, GAP-005)

### Phase 3: Message Handling (Medium)
7. **GAP-007** - Additional ADT Message Types
8. **GAP-008** - Order-Result Linkage
9. **GAP-009** - REST Ingestion Endpoint

### Phase 4: Configuration & Edge Cases (Low)
10. **GAP-010** - Per-Hospital Configuration
11. **GAP-011** - E/M Placeholder Charges
12. **GAP-012** - Out-of-Order Message Handling
13. **GAP-013** - Late Charge Handling

---

## Summary Statistics

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 3 | Blocks V1 |
| HIGH | 3 | Data completeness |
| MEDIUM | 3 | Secondary features |
| LOW | 4 | Enhancements |
| **TOTAL** | **13** | |

---

## Appendix: File Change Summary

### New Files to Create
- `app/domains/users/provider_service.py`
- `app/domains/users/provider_schemas.py`
- `alembic/versions/YYYYMMDD_add_npi_providers.py`
- `alembic/versions/YYYYMMDD_add_charges.py`
- `alembic/versions/YYYYMMDD_add_encounter_fields.py`
- `alembic/versions/YYYYMMDD_add_order_billing_fields.py`
- `alembic/versions/YYYYMMDD_add_hospital_config.py`

### Existing Files to Modify
- `app/domains/users/models.py` - add NPIProvider
- `app/domains/users/router.py` - add provider endpoints
- `app/domains/encounters/models.py` - add Charge, update Encounter, Order
- `app/domains/encounters/schemas.py` - add Charge schemas, update Encounter
- `app/domains/encounters/hl7/parser.py` - add FT1 parsing, extract more PV1 fields
- `app/domains/encounters/hl7/types.py` - add ParsedCharge
- `app/domains/encounters/service.py` - message type routing, charge processing
- `app/domains/encounters/router.py` - add /ingest endpoint
- `app/domains/workflow/models.py` - add HospitalConfiguration
- `app/domains/workflow/coding_queue_service.py` - provider check, snapshot structure
