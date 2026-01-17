# HL7 to Codable Packet Generation - Product Specification
**Version:** 1.0  
**Target Market:** Rural Hospitals, Critical Access Hospitals (CAHs), 25-100 bed facilities  
**Last Updated:** January 2026

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [System Architecture Overview](#system-architecture-overview)
3. [Data Models](#data-models)
4. [HL7 Message Processing Rules](#hl7-message-processing-rules)
5. [Codable Packet Generation Logic](#codable-packet-generation-logic)
6. [Configuration Parameters](#configuration-parameters)
7. [Hospital Onboarding Requirements](#hospital-onboarding-requirements)
8. [Technical Implementation Guide](#technical-implementation-guide)
9. [Edge Cases & Error Handling](#edge-cases--error-handling)
10. [Future Enhancements (V2)](#future-enhancements-v2)

---

## Executive Summary

### Purpose
This specification defines how to process HL7 v2.x message streams from hospital systems (via Mirth Connect middleware) and generate **codable packets** for medical coding workflows. The system splits encounters into:
- **Facility Coding Packets** (for UB-04 hospital bills)
- **Professional Fee (ProFee) Coding Packets** (for CMS-1500 physician bills)

### Design Philosophy (80/20 Rule)
- **Optimize for:** Hospital-employed physician model (Scenario A - most common in rural hospitals)
- **Start simple:** Default to split billing (technical + professional components)
- **Configuration:** Minimal but sufficient - provider employment type, encounter type triggers
- **Defer complexity:** Per-CPT charge rules, real-time eligibility, advanced validation → V2

### Key Assumptions
1. **HL7 messages arrive via Mirth Connect** (batch processing with varying cadences)
2. **Out-of-order messages are possible** (e.g., charges arrive before discharge)
3. **Provider roster is pre-loaded** (NPI table with employment status)
4. **Packet readiness:** Immediate after discharge (don't wait for completeness checks)
5. **Primary use case:** Hospital employs physicians and handles both facility and ProFee billing

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Hospital Source Systems                       │
│  (EMR: Epic, Cerner, Meditech | Lab: Sunquest | Radiology: etc) │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ HL7 v2.x Messages
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Mirth Connect                               │
│  - Message normalization                                         │
│  - Format standardization                                        │
│  - Routing to medcode platform                                   │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ Normalized HL7 (Batch or Stream)
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 medcode HL7 Ingestion Engine                     │
│  - Parse HL7 messages                                            │
│  - Validate message structure                                    │
│  - Handle out-of-order messages                                  │
│  - Extract clinical/billing data                                 │
└────────────┬────────────────────────────────────────────────────┘
             │
             ├─────────────────┬──────────────────────────────────┐
             ▼                 ▼                                  ▼
    ┌────────────────┐  ┌──────────────┐              ┌──────────────────┐
    │   Encounter     │  │   Order      │              │   Charge         │
    │   Management    │  │   Tracking   │              │   Capture        │
    └────────┬────────┘  └──────┬───────┘              └────────┬─────────┘
             │                  │                               │
             └──────────────────┴───────────────────────────────┘
                                │
                                ▼
             ┌──────────────────────────────────────────┐
             │   Codable Packet Generation Engine       │
             │   - Determine Facility vs ProFee         │
             │   - Apply configuration rules            │
             │   - Generate coding work queue items     │
             └──────┬───────────────────────────────────┘
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
┌────────────────────┐  ┌──────────────────────┐
│  Facility Coding   │  │  ProFee Coding       │
│  Work Queue        │  │  Work Queue          │
│  (UB-04 claims)    │  │  (CMS-1500 claims)   │
└────────────────────┘  └──────────────────────┘
```

---

## Data Models

### 1. NPI Provider Registry

**Purpose:** Master table of all providers (physicians, NPPs) with employment status

**Source:** 
- NPPES (National Plan and Provider Enumeration System) - Public CMS database
- Hospital HR system for employment status
- Manual configuration during onboarding

**Schema:**

```python
class NPIProvider(BaseModel):
    """
    National Provider Identifier registry with employment metadata
    """
    npi: str  # Primary key, 10-digit NPI (e.g., "1234567890")
    
    # From NPPES public data
    first_name: str
    last_name: str
    credential: str | None  # "MD", "DO", "NP", "PA", etc.
    taxonomy_code: str  # NUCC taxonomy (e.g., "207R00000X" = Internal Medicine)
    specialty: str  # Human-readable specialty
    
    # Hospital-specific configuration
    hospital_id: str  # Foreign key to Hospital table
    employment_type: EmploymentType
    active_status: bool  # Is this provider currently active?
    
    # Billing configuration
    individual_npi: str  # Provider's individual NPI
    billing_npi: str | None  # Group/hospital NPI if applicable
    
    # Metadata
    created_at: datetime
    updated_at: datetime

class EmploymentType(str, Enum):
    """
    Provider relationship to hospital - determines ProFee billing routing
    """
    HOSPITAL_EMPLOYED = "HOSPITAL_EMPLOYED"  # Hospital bills ProFee under hospital NPI or provider individual NPI
    INDEPENDENT_CONTRACTOR = "INDEPENDENT_CONTRACTOR"  # External group bills ProFee (not in our system)
    HOSPITAL_PRIVILEGES_ONLY = "HOSPITAL_PRIVILEGES_ONLY"  # Surgeon with privileges, bills own ProFee
    LOCUM_TENENS = "LOCUM_TENENS"  # Temporary provider, typically hospital-employed for billing
```

**Configuration Rules:**
- **HOSPITAL_EMPLOYED:** System creates ProFee codable packets for this provider's services
- **INDEPENDENT_CONTRACTOR:** System does NOT create ProFee packets (external billing)
- **HOSPITAL_PRIVILEGES_ONLY:** System does NOT create ProFee packets (physician bills independently)
- **LOCUM_TENENS:** System creates ProFee packets (treated as hospital-employed)

**80/20 Rule Application:**
- V1: Only support HOSPITAL_EMPLOYED vs. all others (binary: create ProFee packet or don't)
- V2: Add nuanced routing for different employment types

---

### 2. Encounter Table

**Purpose:** Parent record representing a patient's visit/admission. All HL7 messages link to an encounter.

**Schema:**

```python
class Encounter(BaseModel):
    """
    Core encounter record - represents one patient visit
    Links to all HL7 messages, orders, charges, and codable packets
    """
    # Identifiers
    encounter_id: str  # Primary key (UUID or auto-increment)
    pv_id: str  # Unique from HL7 PV1-19 (Patient Visit ID) - INDEX THIS
    mrn: str  # Medical Record Number from PID-3
    account_number: str | None  # From PID-18 or PV1-50
    
    hospital_id: str  # Foreign key to Hospital configuration
    
    # Patient demographics (from PID segment)
    patient_first_name: str
    patient_last_name: str
    date_of_birth: date
    sex: str  # "M", "F", "U"
    
    # Encounter metadata (from PV1 segment)
    patient_class: PatientClass  # "I" (Inpatient), "O" (Outpatient), "E" (Emergency), "R" (Recurring)
    admission_type: str | None  # "1" (Emergency), "2" (Urgent), "3" (Elective)
    hospital_service: str | None  # "MED", "SUR", "OBS", etc.
    
    # Dates/times
    admit_datetime: datetime  # From PV1-44
    discharge_datetime: datetime | None  # From PV1-45
    
    # Location tracking
    current_location: str | None  # Bed/room from PV1-3
    
    # Providers (from PV1 segment)
    attending_provider_npi: str | None  # PV1-7
    admitting_provider_npi: str | None  # PV1-17
    referring_provider_npi: str | None  # PV1-8
    
    # Insurance (from IN1 segment)
    primary_payer: str | None
    primary_policy_number: str | None
    
    # Encounter status
    status: EncounterStatus
    
    # Coding workflow triggers
    facility_coding_required: bool  # Always True for IP/OBS, configurable for OP/ER
    profee_coding_required: bool  # True if attending provider is HOSPITAL_EMPLOYED
    
    # Timestamps
    created_at: datetime
    updated_at: datetime

class PatientClass(str, Enum):
    INPATIENT = "I"
    OUTPATIENT = "O"
    EMERGENCY = "E"
    OBSERVATION = "O"  # Often encoded as "O" in PV1-2, distinguish via PV1-10
    RECURRING = "R"
    PREADMIT = "P"

class EncounterStatus(str, Enum):
    OPEN = "OPEN"  # Patient still in hospital
    DISCHARGED = "DISCHARGED"  # ADT^A03 received, patient left
    PENDING_CODING = "PENDING_CODING"  # Codable packets generated, awaiting coder assignment
    CODING_IN_PROGRESS = "CODING_IN_PROGRESS"  # Coder working on it
    CODING_COMPLETE = "CODING_COMPLETE"  # All coding done
    BILLED = "BILLED"  # Claim submitted
    CANCELLED = "CANCELLED"  # Encounter cancelled (ADT^A11)
```

---

### 3. HL7 Message Log

**Purpose:** Audit trail of all received HL7 messages, linked to encounters

**Schema:**

```python
class HL7MessageLog(BaseModel):
    """
    Complete audit trail of all HL7 messages received
    """
    message_id: str  # Primary key (UUID)
    
    # Message metadata
    message_control_id: str  # From MSH-10 (unique ID from sending system)
    message_type: str  # From MSH-9 (e.g., "ADT^A01", "ORM^O01")
    
    # Association
    encounter_id: str | None  # Foreign key - may be null for unmatched messages
    pv_id: str | None  # From PV1-19 for linking
    
    # Raw message
    raw_message: str  # Full HL7 message text (for debugging/audit)
    
    # Processing metadata
    received_at: datetime
    processed_at: datetime | None
    processing_status: ProcessingStatus
    error_message: str | None  # If processing failed
    
    # Mirth metadata (if available)
    mirth_channel_id: str | None
    mirth_message_id: str | None

class ProcessingStatus(str, Enum):
    RECEIVED = "RECEIVED"  # Message arrived, queued for processing
    PROCESSING = "PROCESSING"  # Currently parsing
    PROCESSED = "PROCESSED"  # Successfully processed
    FAILED = "FAILED"  # Processing error
    IGNORED = "IGNORED"  # Message type not relevant (e.g., SIU scheduling)
```

---

### 4. Order Tracking Table

**Purpose:** Track clinical orders (labs, radiology, procedures) from ORM messages and their results from ORU messages

**Schema:**

```python
class ClinicalOrder(BaseModel):
    """
    Clinical orders from ORM^O01 messages
    Linked to results from ORU^R01 messages
    """
    order_id: str  # Primary key (UUID)
    
    # Association
    encounter_id: str  # Foreign key to Encounter
    pv_id: str  # From PV1-19
    
    # Order details (from OBR segment)
    placer_order_number: str  # OBR-2 (hospital's order ID)
    filler_order_number: str | None  # OBR-3 (lab/radiology system's order ID)
    
    universal_service_id: str  # OBR-4 (procedure code, e.g., "CBC", "CHEST_XRAY")
    universal_service_name: str  # OBR-4.2 (human-readable name)
    
    # Provider
    ordering_provider_npi: str | None  # OBR-16
    
    # Timing
    order_datetime: datetime  # OBR-6 (when ordered)
    observation_datetime: datetime | None  # OBR-7 (when performed)
    results_datetime: datetime | None  # OBR-22 (when resulted)
    
    # Order status
    order_status: OrderStatus  # OBR-25
    
    # Result association
    has_results: bool  # True if ORU message received
    result_interpretation: str | None  # "Normal", "Abnormal", "Critical"
    
    # Billing relevance
    billable_to_facility: bool  # True for most ancillary services
    billable_to_profee: bool  # True if requires physician interpretation (radiology reads, EKG interpretation)
    
    # Metadata
    created_at: datetime
    updated_at: datetime

class OrderStatus(str, Enum):
    ORDERED = "ORDERED"  # ORM received, order placed
    IN_PROGRESS = "IP"  # Test in progress
    COMPLETED = "CM"  # Test complete, results available
    CANCELLED = "CA"  # Order cancelled
    HELD = "HD"  # Order on hold
```

**Business Rule:**
- When `billable_to_profee = True`, this order should appear in the **ProFee Codable Packet** (if attending provider is HOSPITAL_EMPLOYED)
- Common ProFee interpretation services:
  - Radiology (X-rays, CT, MRI, Ultrasound) → CPT with modifier 26
  - Cardiology (EKG, Echo, Stress test) → CPT with modifier 26
  - Pulmonary function tests → CPT with modifier 26
  - Sleep studies → Professional interpretation

---

### 5. Charge Capture Table

**Purpose:** Store charges from DFT^P03 messages (both pre-coded and post-coded)

**Schema:**

```python
class Charge(BaseModel):
    """
    Charges from DFT^P03 messages
    May arrive before or after coding (system must handle both)
    """
    charge_id: str  # Primary key (UUID)
    
    # Association
    encounter_id: str  # Foreign key to Encounter
    pv_id: str  # From PV1-19
    
    # Charge details (from FT1 segment)
    transaction_id: str  # FT1-1 (unique charge ID from source system)
    transaction_type: str  # FT1-6 (e.g., "CG" = Charge, "CD" = Credit)
    transaction_code: str  # FT1-7 (internal hospital charge code)
    transaction_description: str  # FT1-7.2
    
    # Financial details
    transaction_quantity: int  # FT1-10 (quantity, e.g., 2 units of blood)
    transaction_amount: Decimal  # FT1-11 (unit price)
    total_charge_amount: Decimal  # quantity * amount
    
    # Clinical coding (may be null if pre-coded)
    procedure_code: str | None  # FT1-25 (CPT/HCPCS code if present)
    procedure_modifier: str | None  # FT1-25 modifiers
    diagnosis_code: str | None  # FT1-19 (ICD-10 if present)
    
    # Billing classification
    charge_type: ChargeType  # Facility vs ProFee
    revenue_code: str | None  # For facility charges (e.g., "0450" for ER)
    
    # Provider
    performing_provider_npi: str | None  # FT1-21
    
    # Status
    coding_status: CodingStatus
    
    # Metadata
    service_date: date  # FT1-4
    posted_datetime: datetime  # When DFT message received
    created_at: datetime
    updated_at: datetime

class ChargeType(str, Enum):
    FACILITY = "FACILITY"  # Technical component, hospital resources
    PROFEE = "PROFEE"  # Professional component, physician service
    BOTH = "BOTH"  # Global billing (rare, but possible)

class CodingStatus(str, Enum):
    UNCODED = "UNCODED"  # Charge posted without CPT/ICD-10
    AUTO_CODED = "AUTO_CODED"  # System applied default codes
    HUMAN_CODED = "HUMAN_CODED"  # Medical coder reviewed and assigned codes
    VALIDATED = "VALIDATED"  # Coding supervisor reviewed
```

**Business Logic:**
- **Pre-coded charges:** DFT arrives with CPT/ICD-10 codes already populated (common for ancillary services like lab, radiology)
  - System validates codes against NCCI edits
  - Flags for coder review if validation fails
- **Uncoded charges:** DFT arrives without codes (common for OR cases, complex procedures)
  - Charge appears in codable packet for manual coding

---

### 6. Codable Packet Table

**Purpose:** Aggregated view of all clinical/billing data needed for medical coding

**Schema:**

```python
class CodablePacket(BaseModel):
    """
    Codable packet: All data a medical coder needs to assign codes
    Two types: Facility and ProFee (or both for same encounter)
    """
    packet_id: str  # Primary key (UUID)
    
    # Association
    encounter_id: str  # Foreign key to Encounter
    packet_type: PacketType
    
    # Packet readiness
    status: PacketStatus
    ready_for_coding_at: datetime | None  # When packet became available
    
    # Assigned coder
    assigned_coder_id: str | None
    assigned_at: datetime | None
    
    # Coding completion
    coding_started_at: datetime | None
    coding_completed_at: datetime | None
    
    # Data snapshot (JSON field containing all relevant data at time of packet creation)
    clinical_data: dict  # Diagnosis indicators, labs, vitals, etc.
    orders_data: list[dict]  # All clinical orders and results
    charges_data: list[dict]  # All charges for this packet type
    provider_data: dict  # Attending, admitting, consulting providers
    
    # Configuration at time of packet creation
    hospital_configuration: dict  # Capture rules that were active
    
    # Metadata
    created_at: datetime
    updated_at: datetime

class PacketType(str, Enum):
    FACILITY = "FACILITY"  # UB-04 claim coding
    PROFEE = "PROFEE"  # CMS-1500 claim coding

class PacketStatus(str, Enum):
    PENDING = "PENDING"  # Created but not yet ready (encounter still open)
    READY = "READY"  # Ready for coder assignment
    ASSIGNED = "ASSIGNED"  # Coder working on it
    COMPLETE = "COMPLETE"  # Coding finished
    ON_HOLD = "ON_HOLD"  # Awaiting documentation, query response, etc.
    CANCELLED = "CANCELLED"  # Encounter cancelled
```

**Data Aggregation Rules:**

**Facility Packet `clinical_data` structure:**
```json
{
  "encounter_summary": {
    "pv_id": "12345",
    "mrn": "MRN987654",
    "admit_date": "2026-01-05T08:30:00Z",
    "discharge_date": "2026-01-09T14:00:00Z",
    "length_of_stay": 4,
    "patient_class": "INPATIENT",
    "hospital_service": "MED",
    "attending_provider": {
      "npi": "1234567890",
      "name": "Smith, John MD",
      "specialty": "Internal Medicine"
    }
  },
  "diagnoses_indicators": {
    "documented_diagnoses": ["Heart failure mentioned in H&P", "Acute kidney injury in progress notes"],
    "lab_indicators": [
      {"test": "Creatinine", "value": 2.3, "date": "2026-01-05", "abnormal": true},
      {"test": "BNP", "value": 850, "date": "2026-01-05", "abnormal": true}
    ],
    "vital_indicators": [
      {"vital": "O2_saturation", "value": 88, "date": "2026-01-05", "abnormal": true},
      {"vital": "O2_requirement", "value": "6L NC", "date": "2026-01-05", "abnormal": true}
    ]
  },
  "payer_info": {
    "primary_payer": "Medicare Part A",
    "policy_number": "1234567890A",
    "authorization_number": null
  }
}
```

**ProFee Packet `charges_data` structure:**
```json
[
  {
    "charge_id": "CHG001",
    "service_date": "2026-01-05",
    "description": "Emergency Department Visit",
    "performing_provider_npi": "1234567890",
    "current_code": "99285",  // If pre-coded
    "coding_status": "NEEDS_VALIDATION",
    "revenue_code": null,  // Not applicable to ProFee
    "suggested_diagnosis": ["I50.23", "N17.9"]  // AI suggestions if available
  },
  {
    "charge_id": "CHG002",
    "service_date": "2026-01-06",
    "description": "Subsequent Hospital Visit",
    "performing_provider_npi": "1234567890",
    "current_code": null,  // Uncoded
    "coding_status": "UNCODED"
  }
]
```

---

## HL7 Message Processing Rules

### Message Type Handling Matrix

| Message Type | Trigger | Action | Creates Encounter? | Updates Encounter? | Triggers Packet? |
|--------------|---------|--------|-------------------|-------------------|------------------|
| **ADT^A01** | Patient admitted | Create encounter record | ✅ Yes | - | ❌ No (patient still in-house) |
| **ADT^A03** | Patient discharged | Update encounter, trigger packet generation | ❌ No | ✅ Yes | ✅ Yes |
| **ADT^A04** | Patient registered (outpatient) | Create encounter if doesn't exist | ✅ Yes | - | Depends on config |
| **ADT^A08** | Update patient info | Update demographics, insurance | ❌ No | ✅ Yes | ❌ No |
| **ADT^A02** | Patient transfer (location change) | Update location | ❌ No | ✅ Yes | ❌ No |
| **ADT^A06** | Outpatient to Inpatient | Update patient_class, may change billing | ❌ No | ✅ Yes | ❌ No |
| **ADT^A11** | Cancel admit | Cancel encounter | ❌ No | ✅ Yes (cancel) | ❌ No |
| **ORM^O01** | Order placed | Create order record | ❌ No | ❌ No | ❌ No |
| **ORU^R01** | Results available | Update order with results | ❌ No | ❌ No | ❌ No |
| **DFT^P03** | Charge posted | Create charge record | ❌ No | ❌ No | ❌ No |

---

### Detailed Message Processing Logic

#### 1. ADT^A01 (Admit Patient)

**Purpose:** Create new encounter when patient is admitted

**Required Segments:**
- MSH (Message Header)
- EVN (Event Type)
- PID (Patient Identification)
- PV1 (Patient Visit)
- IN1 (Insurance - optional but recommended)

**Processing Steps:**

```python
def process_adt_a01(hl7_message: HL7Message) -> Encounter:
    """
    Process ADT^A01 (Admit) message
    Creates new encounter or updates if exists (handles duplicate sends)
    """
    
    # Step 1: Extract PV ID (unique encounter identifier)
    pv_id = hl7_message.PV1[19].value
    
    # Step 2: Check if encounter already exists (idempotency)
    existing_encounter = db.query(Encounter).filter_by(pv_id=pv_id).first()
    
    if existing_encounter:
        logger.warning(f"Duplicate ADT^A01 for PV ID {pv_id}, updating existing encounter")
        encounter = existing_encounter
    else:
        encounter = Encounter(encounter_id=generate_uuid(), pv_id=pv_id)
    
    # Step 3: Extract patient demographics from PID segment
    encounter.mrn = hl7_message.PID[3].value  # PID-3: Patient ID
    encounter.patient_first_name = hl7_message.PID[5][2]  # PID-5.2: Given name
    encounter.patient_last_name = hl7_message.PID[5][1]  # PID-5.1: Family name
    encounter.date_of_birth = parse_date(hl7_message.PID[7].value)  # PID-7: DOB
    encounter.sex = hl7_message.PID[8].value  # PID-8: Sex
    
    # Step 4: Extract encounter details from PV1 segment
    encounter.patient_class = hl7_message.PV1[2].value  # "I", "O", "E"
    encounter.admission_type = hl7_message.PV1[4].value  # "1", "2", "3"
    encounter.hospital_service = hl7_message.PV1[10].value  # "MED", "SUR", etc.
    encounter.admit_datetime = parse_datetime(hl7_message.PV1[44].value)
    encounter.current_location = hl7_message.PV1[3].value  # Bed/Room
    
    # Step 5: Extract provider information
    encounter.attending_provider_npi = extract_npi(hl7_message.PV1[7])  # PV1-7: Attending
    encounter.admitting_provider_npi = extract_npi(hl7_message.PV1[17])  # PV1-17: Admitting
    encounter.referring_provider_npi = extract_npi(hl7_message.PV1[8])  # PV1-8: Referring
    
    # Step 6: Extract insurance from IN1 segment (if present)
    if hl7_message.has_segment('IN1'):
        encounter.primary_payer = hl7_message.IN1[4].value  # IN1-4: Insurance company name
        encounter.primary_policy_number = hl7_message.IN1[36].value  # IN1-36: Policy number
    
    # Step 7: Set initial status
    encounter.status = EncounterStatus.OPEN
    
    # Step 8: Determine coding requirements based on patient class
    encounter.facility_coding_required = should_create_facility_packet(encounter)
    encounter.profee_coding_required = should_create_profee_packet(encounter)
    
    # Step 9: Save to database
    db.session.add(encounter)
    db.session.commit()
    
    logger.info(f"Created encounter {encounter.encounter_id} for PV ID {pv_id}")
    
    return encounter

def should_create_facility_packet(encounter: Encounter) -> bool:
    """
    Business rule: When does this encounter need facility coding?
    """
    # Always code inpatient, observation
    if encounter.patient_class in ['I', 'O']:  # Inpatient or Observation
        return True
    
    # Check hospital configuration for other types
    hospital_config = get_hospital_config(encounter.hospital_id)
    
    # Emergency department - configurable
    if encounter.patient_class == 'E':
        return hospital_config.code_emergency_visits
    
    # Outpatient - configurable (some hospitals code all OP, others only procedures)
    if encounter.patient_class == 'O':
        return hospital_config.code_outpatient_visits
    
    # Default: don't code
    return False

def should_create_profee_packet(encounter: Encounter) -> bool:
    """
    Business rule: When does this encounter need ProFee coding?
    Requires: Attending provider is HOSPITAL_EMPLOYED
    """
    if not encounter.attending_provider_npi:
        return False
    
    # Look up provider employment status
    provider = db.query(NPIProvider).filter_by(
        npi=encounter.attending_provider_npi,
        hospital_id=encounter.hospital_id
    ).first()
    
    if not provider:
        logger.warning(f"Provider NPI {encounter.attending_provider_npi} not found in registry")
        return False
    
    # V1: Simple rule - only HOSPITAL_EMPLOYED generates ProFee packets
    return provider.employment_type == EmploymentType.HOSPITAL_EMPLOYED
```

---

#### 2. ADT^A03 (Discharge Patient)

**Purpose:** Mark encounter as discharged and trigger codable packet generation

**Processing Steps:**

```python
def process_adt_a03(hl7_message: HL7Message) -> Encounter:
    """
    Process ADT^A03 (Discharge) message
    Triggers codable packet generation (CRITICAL FOR WORKFLOW)
    """
    
    # Step 1: Find encounter
    pv_id = hl7_message.PV1[19].value
    encounter = db.query(Encounter).filter_by(pv_id=pv_id).first()
    
    if not encounter:
        logger.error(f"ADT^A03 received but no encounter found for PV ID {pv_id}")
        # Could be out-of-order - create encounter from discharge message
        encounter = create_encounter_from_discharge(hl7_message)
    
    # Step 2: Update discharge information
    encounter.discharge_datetime = parse_datetime(hl7_message.PV1[45].value)
    encounter.status = EncounterStatus.DISCHARGED
    
    # Step 3: Update final location/disposition
    encounter.discharge_disposition = hl7_message.PV1[36].value  # "01" (home), "03" (SNF), etc.
    
    db.session.commit()
    
    logger.info(f"Encounter {encounter.encounter_id} discharged at {encounter.discharge_datetime}")
    
    # Step 4: TRIGGER CODABLE PACKET GENERATION
    # This is the critical step - as soon as patient is discharged, create coding work
    generate_codable_packets(encounter)
    
    return encounter

def generate_codable_packets(encounter: Encounter):
    """
    Create codable packets based on encounter configuration
    Called immediately after ADT^A03 (discharge)
    """
    packets_created = []
    
    # Generate Facility packet (if required)
    if encounter.facility_coding_required:
        facility_packet = create_facility_codable_packet(encounter)
        packets_created.append(facility_packet)
        logger.info(f"Created FACILITY codable packet {facility_packet.packet_id}")
    
    # Generate ProFee packet (if required)
    if encounter.profee_coding_required:
        profee_packet = create_profee_codable_packet(encounter)
        packets_created.append(profee_packet)
        logger.info(f"Created PROFEE codable packet {profee_packet.packet_id}")
    
    # Update encounter status
    if packets_created:
        encounter.status = EncounterStatus.PENDING_CODING
        db.session.commit()
    
    return packets_created
```

---

#### 3. ORM^O01 (Order Message)

**Purpose:** Track clinical orders (labs, imaging, procedures)

**Processing Steps:**

```python
def process_orm_o01(hl7_message: HL7Message) -> ClinicalOrder:
    """
    Process ORM^O01 (Order) message
    Creates order tracking record
    """
    
    # Step 1: Find associated encounter
    pv_id = hl7_message.PV1[19].value
    encounter = db.query(Encounter).filter_by(pv_id=pv_id).first()
    
    if not encounter:
        logger.warning(f"ORM^O01 received but no encounter found for PV ID {pv_id}")
        # Could be outpatient order before registration - handle gracefully
        return None
    
    # Step 2: Extract order details from OBR segment
    order = ClinicalOrder(
        order_id=generate_uuid(),
        encounter_id=encounter.encounter_id,
        pv_id=pv_id
    )
    
    order.placer_order_number = hl7_message.OBR[2].value  # Hospital's order ID
    order.filler_order_number = hl7_message.OBR[3].value  # Lab/Rad system order ID
    
    order.universal_service_id = hl7_message.OBR[4][1]  # Procedure code
    order.universal_service_name = hl7_message.OBR[4][2]  # Procedure name
    
    order.ordering_provider_npi = extract_npi(hl7_message.OBR[16])
    
    order.order_datetime = parse_datetime(hl7_message.OBR[6].value)
    order.observation_datetime = parse_datetime(hl7_message.OBR[7].value) if hl7_message.OBR[7] else None
    
    order.order_status = OrderStatus.ORDERED
    
    # Step 3: Determine billing relevance
    order.billable_to_facility = True  # Almost all ancillary services are facility charges
    order.billable_to_profee = requires_physician_interpretation(order.universal_service_id)
    
    db.session.add(order)
    db.session.commit()
    
    logger.info(f"Created order {order.order_id} for service {order.universal_service_name}")
    
    return order

def requires_physician_interpretation(service_id: str) -> bool:
    """
    Business rule: Does this order require ProFee coding for physician interpretation?
    """
    PROFEE_INTERPRETATION_SERVICES = [
        'RAD',      # Radiology (X-rays, CT, MRI)
        'US',       # Ultrasound
        'ECHO',     # Echocardiogram
        'EKG',      # Electrocardiogram
        'STRESS',   # Stress test
        'PFT',      # Pulmonary function test
        'SLEEP',    # Sleep study
        'HOLTER',   # Holter monitor
        'EEG',      # Electroencephalogram
    ]
    
    # Check if service ID starts with any ProFee service prefix
    return any(service_id.startswith(prefix) for prefix in PROFEE_INTERPRETATION_SERVICES)
```

---

#### 4. ORU^R01 (Result Message)

**Purpose:** Update order with results

**Processing Steps:**

```python
def process_oru_r01(hl7_message: HL7Message) -> ClinicalOrder:
    """
    Process ORU^R01 (Results) message
    Links results to existing order
    """
    
    # Step 1: Find the order using filler order number (from lab/rad system)
    filler_order_number = hl7_message.OBR[3].value
    
    order = db.query(ClinicalOrder).filter_by(
        filler_order_number=filler_order_number
    ).first()
    
    if not order:
        # Order might not exist yet (ORM hasn't arrived) - out-of-order scenario
        logger.warning(f"ORU^R01 received but no order found for filler #{filler_order_number}")
        # Create a placeholder order or queue for later matching
        return None
    
    # Step 2: Update order with result information
    order.results_datetime = parse_datetime(hl7_message.OBR[22].value)
    order.order_status = OrderStatus.COMPLETED
    order.has_results = True
    
    # Step 3: Extract result interpretation (if available)
    # OBX segments contain individual result values
    abnormal_flags = []
    for obx in hl7_message.get_all_segments('OBX'):
        abnormal_flag = obx[8].value  # OBX-8: Abnormal flags ("H", "L", "A", etc.)
        if abnormal_flag:
            abnormal_flags.append(abnormal_flag)
    
    if 'H' in abnormal_flags or 'A' in abnormal_flags:
        order.result_interpretation = 'Abnormal'
    elif 'L' in abnormal_flags:
        order.result_interpretation = 'Abnormal'
    else:
        order.result_interpretation = 'Normal'
    
    db.session.commit()
    
    logger.info(f"Updated order {order.order_id} with results")
    
    return order
```

---

#### 5. DFT^P03 (Charge Posting)

**Purpose:** Capture charges (both pre-coded and uncoded)

**Processing Steps:**

```python
def process_dft_p03(hl7_message: HL7Message) -> list[Charge]:
    """
    Process DFT^P03 (Charge Posting) message
    May contain multiple charges (multiple FT1 segments)
    """
    
    # Step 1: Find encounter
    pv_id = hl7_message.PV1[19].value
    encounter = db.query(Encounter).filter_by(pv_id=pv_id).first()
    
    if not encounter:
        logger.warning(f"DFT^P03 received but no encounter found for PV ID {pv_id}")
        return []
    
    charges = []
    
    # Step 2: Process each FT1 segment (one per charge)
    for ft1_segment in hl7_message.get_all_segments('FT1'):
        charge = Charge(
            charge_id=generate_uuid(),
            encounter_id=encounter.encounter_id,
            pv_id=pv_id
        )
        
        # Transaction details
        charge.transaction_id = ft1_segment[1].value  # FT1-1: Set ID
        charge.transaction_type = ft1_segment[6].value  # FT1-6: Transaction type
        charge.transaction_code = ft1_segment[7][1]  # FT1-7.1: Internal charge code
        charge.transaction_description = ft1_segment[7][2]  # FT1-7.2: Description
        
        # Financial details
        charge.transaction_quantity = int(ft1_segment[10].value or 1)
        charge.transaction_amount = Decimal(ft1_segment[11].value or 0)
        charge.total_charge_amount = charge.transaction_quantity * charge.transaction_amount
        
        # Clinical coding (may be present or may be null)
        if ft1_segment[25]:  # FT1-25: Procedure code
            charge.procedure_code = ft1_segment[25][1]  # CPT/HCPCS code
            charge.procedure_modifier = ft1_segment[25][2] if len(ft1_segment[25]) > 1 else None
            charge.coding_status = CodingStatus.AUTO_CODED  # System assigned, needs validation
        else:
            charge.coding_status = CodingStatus.UNCODED  # Needs manual coding
        
        if ft1_segment[19]:  # FT1-19: Diagnosis code
            charge.diagnosis_code = ft1_segment[19][1]  # ICD-10 code
        
        # Provider
        charge.performing_provider_npi = extract_npi(ft1_segment[21]) if ft1_segment[21] else None
        
        # Revenue code (for facility charges)
        if ft1_segment[26]:  # FT1-26: Revenue code (UB-04)
            charge.revenue_code = ft1_segment[26].value
        
        # Determine charge type
        charge.charge_type = determine_charge_type(charge)
        
        # Service date
        charge.service_date = parse_date(ft1_segment[4].value)
        charge.posted_datetime = datetime.now()
        
        db.session.add(charge)
        charges.append(charge)
    
    db.session.commit()
    
    logger.info(f"Created {len(charges)} charges for encounter {encounter.encounter_id}")
    
    return charges

def determine_charge_type(charge: Charge) -> ChargeType:
    """
    Business rule: Is this charge Facility, ProFee, or Both?
    Based on revenue code, procedure code, and performing provider
    """
    
    # If revenue code present, likely facility charge
    if charge.revenue_code:
        return ChargeType.FACILITY
    
    # Check procedure code for professional component modifier
    if charge.procedure_modifier == '26':  # Professional component
        return ChargeType.PROFEE
    
    if charge.procedure_modifier == 'TC':  # Technical component
        return ChargeType.FACILITY
    
    # Check if performing provider is employed (indicates ProFee)
    if charge.performing_provider_npi:
        provider = db.query(NPIProvider).filter_by(
            npi=charge.performing_provider_npi
        ).first()
        
        if provider and provider.employment_type == EmploymentType.HOSPITAL_EMPLOYED:
            # Could be both facility and ProFee (e.g., procedures)
            # Default to BOTH, let coder decide
            return ChargeType.BOTH
    
    # Default: Facility charge
    return ChargeType.FACILITY
```

---

## Codable Packet Generation Logic

### When Packets Are Created

**Trigger Event:** ADT^A03 (Discharge) message received

**Timing:** Immediate (don't wait for "completeness")

**Rationale (80/20 Rule):**
- Rural hospitals often have delays in charge posting, result finalization
- Coders are accustomed to working with incomplete data and following up
- Waiting for "completeness" causes DNFB (Discharged Not Final Billed) aging
- Codable packets can be updated if late charges arrive

---

### Facility Codable Packet Creation

**Purpose:** Aggregate all data needed for UB-04 facility claim coding

```python
def create_facility_codable_packet(encounter: Encounter) -> CodablePacket:
    """
    Create facility codable packet
    Contains: All facility charges, diagnosis indicators, provider info
    """
    
    packet = CodablePacket(
        packet_id=generate_uuid(),
        encounter_id=encounter.encounter_id,
        packet_type=PacketType.FACILITY,
        status=PacketStatus.READY,
        ready_for_coding_at=datetime.now()
    )
    
    # Aggregate clinical data
    packet.clinical_data = build_clinical_data_snapshot(encounter)
    
    # Aggregate orders/results
    orders = db.query(ClinicalOrder).filter_by(
        encounter_id=encounter.encounter_id
    ).all()
    
    packet.orders_data = [serialize_order(order) for order in orders]
    
    # Aggregate FACILITY charges only
    facility_charges = db.query(Charge).filter_by(
        encounter_id=encounter.encounter_id,
        charge_type=ChargeType.FACILITY
    ).all()
    
    # Also include BOTH type charges (coder will split)
    both_charges = db.query(Charge).filter_by(
        encounter_id=encounter.encounter_id,
        charge_type=ChargeType.BOTH
    ).all()
    
    all_charges = facility_charges + both_charges
    packet.charges_data = [serialize_charge(charge) for charge in all_charges]
    
    # Provider information
    packet.provider_data = build_provider_snapshot(encounter)
    
    # Hospital configuration (capture current state)
    hospital_config = get_hospital_config(encounter.hospital_id)
    packet.hospital_configuration = serialize_config(hospital_config)
    
    db.session.add(packet)
    db.session.commit()
    
    logger.info(f"Created FACILITY packet {packet.packet_id} with {len(all_charges)} charges")
    
    return packet

def build_clinical_data_snapshot(encounter: Encounter) -> dict:
    """
    Build snapshot of all clinical data for coding
    """
    
    # Get all lab results for this encounter
    lab_orders = db.query(ClinicalOrder).filter_by(
        encounter_id=encounter.encounter_id,
        has_results=True
    ).filter(
        ClinicalOrder.universal_service_id.like('LAB%')
    ).all()
    
    lab_indicators = []
    for order in lab_orders:
        if order.result_interpretation == 'Abnormal':
            lab_indicators.append({
                'test_name': order.universal_service_name,
                'result_status': 'Abnormal',
                'result_date': order.results_datetime.isoformat()
            })
    
    # Get vital signs (if available from HL7 messages - often in OBX segments)
    # For V1, we may not have structured vitals - placeholder for future
    
    return {
        'encounter_summary': {
            'pv_id': encounter.pv_id,
            'mrn': encounter.mrn,
            'admit_date': encounter.admit_datetime.isoformat(),
            'discharge_date': encounter.discharge_datetime.isoformat() if encounter.discharge_datetime else None,
            'length_of_stay': (encounter.discharge_datetime - encounter.admit_datetime).days if encounter.discharge_datetime else None,
            'patient_class': encounter.patient_class,
            'admission_type': encounter.admission_type,
            'hospital_service': encounter.hospital_service,
            'discharge_disposition': encounter.discharge_disposition if hasattr(encounter, 'discharge_disposition') else None
        },
        'patient_demographics': {
            'name': f"{encounter.patient_last_name}, {encounter.patient_first_name}",
            'dob': encounter.date_of_birth.isoformat(),
            'sex': encounter.sex,
            'age': calculate_age(encounter.date_of_birth, encounter.admit_datetime)
        },
        'provider_info': {
            'attending_npi': encounter.attending_provider_npi,
            'admitting_npi': encounter.admitting_provider_npi,
            'referring_npi': encounter.referring_provider_npi
        },
        'diagnoses_indicators': {
            'lab_indicators': lab_indicators,
            # Future: Add vitals, medications, procedures
        },
        'payer_info': {
            'primary_payer': encounter.primary_payer,
            'policy_number': encounter.primary_policy_number
        }
    }

def serialize_order(order: ClinicalOrder) -> dict:
    """
    Convert order to JSON-serializable dict for packet
    """
    return {
        'order_id': order.order_id,
        'service_name': order.universal_service_name,
        'service_code': order.universal_service_id,
        'order_date': order.order_datetime.isoformat(),
        'result_date': order.results_datetime.isoformat() if order.results_datetime else None,
        'result_status': order.result_interpretation,
        'ordering_provider_npi': order.ordering_provider_npi,
        'billable_to_facility': order.billable_to_facility,
        'billable_to_profee': order.billable_to_profee
    }

def serialize_charge(charge: Charge) -> dict:
    """
    Convert charge to JSON-serializable dict for packet
    """
    return {
        'charge_id': charge.charge_id,
        'transaction_id': charge.transaction_id,
        'service_date': charge.service_date.isoformat(),
        'description': charge.transaction_description,
        'quantity': charge.transaction_quantity,
        'amount': float(charge.total_charge_amount),
        'revenue_code': charge.revenue_code,
        'current_procedure_code': charge.procedure_code,
        'current_modifier': charge.procedure_modifier,
        'current_diagnosis_code': charge.diagnosis_code,
        'coding_status': charge.coding_status.value,
        'performing_provider_npi': charge.performing_provider_npi
    }
```

---

### ProFee Codable Packet Creation

**Purpose:** Aggregate all data needed for CMS-1500 professional fee claim coding

```python
def create_profee_codable_packet(encounter: Encounter) -> CodablePacket:
    """
    Create ProFee codable packet
    Contains: ProFee charges, E/M visit documentation needs, physician services
    """
    
    packet = CodablePacket(
        packet_id=generate_uuid(),
        encounter_id=encounter.encounter_id,
        packet_type=PacketType.PROFEE,
        status=PacketStatus.READY,
        ready_for_coding_at=datetime.now()
    )
    
    # Clinical data (same as facility, but focus on physician decision-making)
    packet.clinical_data = build_clinical_data_snapshot(encounter)
    
    # Orders that require physician interpretation (ProFee billable)
    profee_orders = db.query(ClinicalOrder).filter_by(
        encounter_id=encounter.encounter_id,
        billable_to_profee=True
    ).all()
    
    packet.orders_data = [serialize_order(order) for order in profee_orders]
    
    # Aggregate PROFEE charges only
    profee_charges = db.query(Charge).filter_by(
        encounter_id=encounter.encounter_id,
        charge_type=ChargeType.PROFEE
    ).all()
    
    # Also include BOTH type charges (coder will split)
    both_charges = db.query(Charge).filter_by(
        encounter_id=encounter.encounter_id,
        charge_type=ChargeType.BOTH
    ).all()
    
    all_charges = profee_charges + both_charges
    
    # Add E/M visit charges (if not already present)
    # ProFee coders often need to code the physician visit itself (99221-99223, etc.)
    em_charge = create_em_placeholder_charge(encounter)
    if em_charge:
        all_charges.append(em_charge)
    
    packet.charges_data = [serialize_charge(charge) for charge in all_charges]
    
    # Provider information (attending physician)
    packet.provider_data = build_provider_snapshot(encounter)
    
    # Hospital configuration
    hospital_config = get_hospital_config(encounter.hospital_id)
    packet.hospital_configuration = serialize_config(hospital_config)
    
    db.session.add(packet)
    db.session.commit()
    
    logger.info(f"Created PROFEE packet {packet.packet_id} with {len(all_charges)} charges")
    
    return packet

def create_em_placeholder_charge(encounter: Encounter) -> Charge | None:
    """
    Create a placeholder charge for E/M (Evaluation & Management) visit
    ProFee coders will assign the appropriate CPT code based on documentation
    
    Examples:
    - Inpatient: 99221-99223 (Initial hospital care)
    - ER: 99281-99285 (Emergency department visit)
    - Observation: 99217-99220 (Observation care)
    """
    
    # Check if E/M charge already exists (might have come from DFT)
    existing_em = db.query(Charge).filter_by(
        encounter_id=encounter.encounter_id,
        charge_type=ChargeType.PROFEE
    ).filter(
        Charge.procedure_code.like('992%')  # E/M codes start with 992xx
    ).first()
    
    if existing_em:
        return None  # Already have E/M charge
    
    # Create placeholder based on patient class
    if encounter.patient_class == 'I':  # Inpatient
        description = "Initial Hospital Care (99221-99223)"
    elif encounter.patient_class == 'E':  # Emergency
        description = "Emergency Department Visit (99281-99285)"
    elif encounter.patient_class == 'O' and encounter.hospital_service == 'OBS':  # Observation
        description = "Observation Care (99217-99220)"
    else:
        return None  # No E/M for this encounter type
    
    charge = Charge(
        charge_id=generate_uuid(),
        encounter_id=encounter.encounter_id,
        pv_id=encounter.pv_id,
        transaction_id=f"EM-{encounter.pv_id}",
        transaction_type="CG",
        transaction_code="EM_VISIT",
        transaction_description=description,
        transaction_quantity=1,
        transaction_amount=Decimal(0),  # Will be set after coding
        total_charge_amount=Decimal(0),
        charge_type=ChargeType.PROFEE,
        coding_status=CodingStatus.UNCODED,
        performing_provider_npi=encounter.attending_provider_npi,
        service_date=encounter.admit_datetime.date(),
        posted_datetime=datetime.now()
    )
    
    db.session.add(charge)
    db.session.commit()
    
    return charge
```

---

## Configuration Parameters

### Hospital-Level Configuration

**Purpose:** Define hospital-specific rules for packet generation

```python
class HospitalConfiguration(BaseModel):
    """
    Hospital-specific configuration for codable packet generation
    Configurable via admin UI during onboarding
    """
    hospital_id: str  # Primary key
    hospital_name: str
    
    # Encounter type coding rules
    code_inpatient: bool = True  # Always True (required for reimbursement)
    code_observation: bool = True  # Always True (required for reimbursement)
    code_emergency_visits: bool = True  # Configurable (some hospitals code all ER, others only admissions)
    code_outpatient_visits: bool = False  # Configurable (most rural hospitals don't code simple OP visits)
    code_outpatient_procedures: bool = True  # Configurable (surgical procedures, infusions, etc.)
    
    # ProFee billing model
    profee_billing_model: ProFeeBillingModel = ProFeeBillingModel.HOSPITAL_EMPLOYED
    
    # Charge capture timing
    wait_for_charge_completeness: bool = False  # V1: Always False (immediate packet generation)
    completeness_wait_hours: int = 24  # V2: If enabled, how long to wait
    
    # Default providers (for encounters with missing provider info)
    default_attending_npi: str | None = None  # Fallback if PV1-7 is null
    
    # Payer-specific rules (V2)
    apply_payer_specific_rules: bool = False  # V2 feature
    
    # Configuration metadata
    created_at: datetime
    updated_at: datetime

class ProFeeBillingModel(str, Enum):
    """
    How does this hospital handle ProFee billing?
    """
    HOSPITAL_EMPLOYED = "HOSPITAL_EMPLOYED"  # Hospital employs physicians, bills ProFee
    INDEPENDENT_GROUPS = "INDEPENDENT_GROUPS"  # Physicians are independent, no ProFee packets
    HYBRID = "HYBRID"  # Some employed, some independent (check per-provider)
```

**Configuration UI (Admin Dashboard):**

During hospital onboarding, admin sets:
- ✅ "Code all emergency department visits?" (Yes/No)
- ✅ "Code outpatient visits?" (Yes/No)
- ✅ "ProFee billing model" (Dropdown: Hospital-employed / Independent / Hybrid)
- ✅ "Default attending physician NPI" (Text input, optional)

---

### Provider-Level Configuration

**Purpose:** Define employment status per provider

```python
# During onboarding, hospital provides provider roster
# System pre-loads from NPPES, hospital HR updates employment status

# Example CSV import:
# NPI, First Name, Last Name, Specialty, Employment Type, Active
# 1234567890, John, Smith, Internal Medicine, HOSPITAL_EMPLOYED, True
# 9876543210, Jane, Doe, Emergency Medicine, INDEPENDENT_CONTRACTOR, True
```

**Provider Management UI:**
- Admin can add/edit providers
- Bulk CSV upload for initial roster
- Mark providers as active/inactive
- Change employment status (triggers re-routing of future encounters)

---

## Hospital Onboarding Requirements

### Phase 1: Pre-Integration Planning (Week 1-2)

**Hospital provides:**

1. **HL7 Interface Specifications**
   - Source systems (EMR, lab, radiology)
   - Message types available (ADT, ORM, ORU, DFT, others?)
   - Sample HL7 messages (anonymized)
   - HL7 version (2.3, 2.5, 2.7, etc.)

2. **Provider Roster**
   - All physicians/NPPs who see patients
   - NPI for each provider
   - Employment status (employed vs. contracted vs. privileges-only)
   - Specialty/department

3. **Encounter Type Policies**
   - "Do you code all ER visits, or only those resulting in admission?"
   - "Do you code outpatient clinic visits, or only procedures?"
   - "Do you use observation status? How is it coded in HL7?"

4. **Billing Model Confirmation**
   - "Are physicians employed by the hospital?"
   - "Who handles ProFee billing? (Hospital billing office or physician group?)"
   - "Do you split-bill (facility + ProFee) or global bill?"

---

### Phase 2: Mirth Connect Configuration (Week 2-3)

**Mirth Connect setup (hospital IT team):**

1. **Create Channels for Each Message Type**
   - ADT channel (A01, A03, A04, A08, A02, A06, A11)
   - ORM channel (O01)
   - ORU channel (R01)
   - DFT channel (P03)

2. **Message Normalization**
   - Standardize date/time formats (ISO 8601)
   - Ensure PV1-19 (Patient Visit ID) is consistently populated
   - Map provider identifiers to NPI (some EMRs use internal IDs)

3. **Routing to medcode Platform**
   - HTTP/REST endpoint: `POST https://api.medcode.com/v1/hl7/ingest`
   - Or SFTP batch file drop (if hospital prefers)
   - Authentication: API key per hospital

4. **Error Handling**
   - Retry logic for failed messages
   - Dead-letter queue for unparseable messages
   - Alerting to hospital IT if interface goes down

**Sample Mirth Transformer (JavaScript):**

```javascript
// Normalize date/time to ISO 8601
var admitDateTime = msg['PV1']['PV1.44']['PV1.44.1'].toString();
admitDateTime = convertHL7DateToISO(admitDateTime);  // Function to convert YYYYMMDDHHMMSS → ISO

// Map internal provider ID to NPI
var attendingProviderID = msg['PV1']['PV1.7']['PV1.7.1'].toString();
var attendingNPI = lookupNPI(attendingProviderID);  // Custom function using hospital's provider mapping table

// Output normalized JSON
var normalizedMessage = {
  "message_type": "ADT^A01",
  "pv_id": msg['PV1']['PV1.19']['PV1.19.1'].toString(),
  "admit_datetime": admitDateTime,
  "attending_provider_npi": attendingNPI,
  // ... rest of fields
};

// Send to medcode API
router.routeMessage('medcode_api_destination', JSON.stringify(normalizedMessage));
```

---

### Phase 3: Data Migration & Testing (Week 3-4)

**Steps:**

1. **Provider Roster Import**
   - Hospital uploads CSV of providers
   - System validates against NPPES
   - Admin reviews and confirms employment types

2. **Historical Data Backfill (Optional)**
   - If hospital wants to backfill open encounters (patients currently in-house)
   - Mirth sends historical ADT messages
   - System creates encounters for in-progress stays

3. **Test Message Flow**
   - Hospital sends test ADT^A01 → Verify encounter created
   - Hospital sends test ADT^A03 → Verify packets generated
   - Hospital sends test ORM/ORU → Verify orders tracked
   - Hospital sends test DFT → Verify charges captured

4. **Coder Training**
   - Demo codable packet interface
   - Show how facility vs. ProFee packets appear
   - Train on workflow (assign → code → validate → submit)

---

### Phase 4: Go-Live (Week 4-5)

**Cutover plan:**

1. **Parallel Run (1 week)**
   - Hospital continues existing coding workflow
   - medcode system runs in parallel
   - Compare: Are packets generating correctly? Any missing data?

2. **Go-Live**
   - Switch coders to medcode platform
   - Monitor for issues (missing encounters, incomplete packets)
   - Daily check-ins with hospital coding manager

3. **Post-Go-Live Support**
   - 30-day hyper-care period
   - Weekly calls with hospital
   - Adjust configurations based on feedback

---

### HL7 Integration Specification Document

**What hospitals receive during onboarding:**

```markdown
# HL7 Integration Specification - [Hospital Name]

## Overview
This document specifies the HL7 v2.x message requirements for integration with the medcode Revenue Cycle Management platform.

## Required Message Types

### ADT (Admit/Discharge/Transfer) Messages
- **ADT^A01** - Admit Patient (Required)
- **ADT^A03** - Discharge Patient (Required)
- **ADT^A08** - Update Patient Information (Recommended)
- **ADT^A02** - Transfer Patient (Optional)
- **ADT^A06** - Change Outpatient to Inpatient (Optional)
- **ADT^A11** - Cancel Admit (Optional)

### ORM (Order Entry) Messages
- **ORM^O01** - General Order Message (Recommended)

### ORU (Observation Result) Messages
- **ORU^R01** - Unsolicited Observation Result (Recommended)

### DFT (Detailed Financial Transaction) Messages
- **DFT^P03** - Post Detail Financial Transactions (Required)

## Message Segment Requirements

### All Messages Must Include:
- **MSH** (Message Header) - Required fields:
  - MSH-9: Message Type
  - MSH-10: Message Control ID (unique)
  - MSH-7: Date/Time of Message

- **PID** (Patient Identification) - Required fields:
  - PID-3: Patient Identifier (MRN)
  - PID-5: Patient Name
  - PID-7: Date of Birth
  - PID-8: Sex

- **PV1** (Patient Visit) - Required fields:
  - PV1-2: Patient Class (I, O, E, R)
  - PV1-19: Visit Number (Patient Visit ID) **[CRITICAL - Must be unique and consistent]**
  - PV1-44: Admit Date/Time
  - PV1-45: Discharge Date/Time (for ADT^A03)

### Provider Identification (Required)
- **PV1-7**: Attending Doctor (NPI preferred, or internal ID we can map)
- **PV1-17**: Admitting Doctor (NPI preferred)

### Insurance Information (Recommended)
- **IN1** segment: Insurance details

## Data Format Standards

### Date/Time Fields
- **Preferred**: ISO 8601 format (`YYYY-MM-DDTHH:MM:SS`)
- **Accepted**: HL7 format (`YYYYMMDDHHMMSS`)

### Provider Identifiers
- **Preferred**: 10-digit NPI in PV1-7.1, PV1-17.1, OBR-16.1, etc.
- **If using internal IDs**: Provide mapping table (Internal ID → NPI)

## Mirth Connect Configuration

### Recommended Channels:
1. **ADT Channel**: Route ADT^A01, A03, A04, A08 to medcode
2. **ORM/ORU Channel**: Route orders and results to medcode
3. **DFT Channel**: Route charges to medcode

### Destination Configuration:
- **URL**: `https://api.medcode.com/v1/hl7/ingest`
- **Method**: POST
- **Authentication**: API Key (provided during onboarding)
- **Content-Type**: `application/json` or `text/plain` (raw HL7)

### Sample API Request:
```http
POST /v1/hl7/ingest HTTP/1.1
Host: api.medcode.com
Authorization: Bearer {API_KEY}
Content-Type: text/plain

MSH|^~\&|EPIC|HOSPITAL|medcode|medcode|20260109120000||ADT^A01|12345|P|2.5
EVN|A01|20260109120000
PID|1||MRN123456||Doe^John||19600101|M
PV1|1|I|ICU^101^A|||||||MED||||||||1234567890^Smith^Jane^MD||HOSP123|||||||||||||||||||||||20260109080000
```

## Testing Requirements

Before go-live, please send test messages for:
1. ✅ Inpatient admission (ADT^A01) → Discharge (ADT^A03)
2. ✅ Emergency visit (ADT^A04) → Discharge (ADT^A03)
3. ✅ Observation admission → Discharge
4. ✅ Order (ORM^O01) → Result (ORU^R01)
5. ✅ Charge posting (DFT^P03) with coded and uncoded charges

## Support

Technical questions: integrations@medcode.com
Phone: 1-800-MEDCODE
```

---

## Technical Implementation Guide

### API Endpoint Specification

**POST /v1/hl7/ingest**

**Request:**
```http
POST /v1/hl7/ingest
Authorization: Bearer {api_key}
Content-Type: text/plain

{raw_hl7_message}
```

**Response (Success):**
```json
{
  "status": "success",
  "message_id": "msg_abc123",
  "message_type": "ADT^A01",
  "encounter_id": "enc_xyz789",
  "processing_time_ms": 45
}
```

**Response (Error):**
```json
{
  "status": "error",
  "error_code": "INVALID_MESSAGE_STRUCTURE",
  "error_message": "PV1-19 (Patient Visit ID) is required but missing",
  "message_control_id": "12345"
}
```

---

### Database Schema Summary

**Core Tables:**
1. `npi_provider_registry` - Provider master data
2. `encounters` - Patient visits
3. `hl7_message_log` - Audit trail
4. `clinical_orders` - Orders and results
5. `charges` - Financial transactions
6. `codable_packets` - Coding work queue items
7. `hospital_configuration` - Per-hospital settings

**Indexes (Performance Critical):**
- `encounters.pv_id` - Unique index (most queries use this)
- `encounters.mrn` - Index for patient lookup
- `clinical_orders.encounter_id` - Foreign key index
- `charges.encounter_id` - Foreign key index
- `codable_packets.status` - For work queue filtering
- `hl7_message_log.message_control_id` - For deduplication

---

## Edge Cases & Error Handling

### 1. Out-of-Order Messages

**Scenario:** ADT^A03 (discharge) arrives before ADT^A01 (admit)

**Handling:**
```python
def handle_out_of_order_discharge(hl7_message: HL7Message):
    """
    If discharge message arrives before admit, create encounter from discharge data
    """
    pv_id = hl7_message.PV1[19].value
    
    # Check if encounter exists
    encounter = db.query(Encounter).filter_by(pv_id=pv_id).first()
    
    if not encounter:
        logger.warning(f"Out-of-order: ADT^A03 received before ADT^A01 for PV ID {pv_id}")
        
        # Create encounter with available data
        encounter = Encounter(
            encounter_id=generate_uuid(),
            pv_id=pv_id,
            status=EncounterStatus.DISCHARGED,  # Already discharged
            discharge_datetime=parse_datetime(hl7_message.PV1[45].value),
            # Extract other fields from discharge message
        )
        
        # Mark for review (might be missing critical admit data)
        encounter.needs_review = True
        encounter.review_reason = "Created from discharge message (admit message not received)"
        
        db.session.add(encounter)
        db.session.commit()
        
        # Still generate codable packets (coders will work with available data)
        generate_codable_packets(encounter)
    
    return encounter
```

---

### 2. Duplicate Messages

**Scenario:** Same message sent twice (Mirth retry logic)

**Handling:**
```python
def is_duplicate_message(hl7_message: HL7Message) -> bool:
    """
    Check if we've already processed this exact message
    Use MSH-10 (Message Control ID) for deduplication
    """
    message_control_id = hl7_message.MSH[10].value
    
    existing = db.query(HL7MessageLog).filter_by(
        message_control_id=message_control_id,
        processing_status=ProcessingStatus.PROCESSED
    ).first()
    
    return existing is not None

# In main ingestion handler:
if is_duplicate_message(hl7_message):
    logger.info(f"Duplicate message {message_control_id}, skipping")
    return {"status": "duplicate", "message": "Message already processed"}
```

---

### 3. Missing Provider NPI

**Scenario:** PV1-7 (Attending Doctor) is null or contains internal ID, not NPI

**Handling:**
```python
def resolve_provider_npi(provider_field: str, hospital_id: str) -> str | None:
    """
    Attempt to resolve provider identifier to NPI
    """
    if not provider_field:
        # Use hospital default (if configured)
        hospital_config = get_hospital_config(hospital_id)
        return hospital_config.default_attending_npi
    
    # Check if it's already a valid NPI (10 digits)
    if provider_field.isdigit() and len(provider_field) == 10:
        return provider_field
    
    # Look up in provider mapping table (internal ID → NPI)
    provider_mapping = db.query(ProviderIDMapping).filter_by(
        hospital_id=hospital_id,
        internal_provider_id=provider_field
    ).first()
    
    if provider_mapping:
        return provider_mapping.npi
    
    logger.warning(f"Could not resolve provider ID {provider_field} to NPI")
    return None
```

---

### 4. Charges Arrive After Packet Created

**Scenario:** Codable packet created at discharge, but charges trickle in over next 24-48 hours

**Handling:**
```python
def handle_late_charge(charge: Charge):
    """
    If charge arrives after codable packet was created, update the packet
    """
    encounter = db.query(Encounter).filter_by(
        encounter_id=charge.encounter_id
    ).first()
    
    # Find existing codable packets for this encounter
    packets = db.query(CodablePacket).filter_by(
        encounter_id=encounter.encounter_id,
        status=PacketStatus.READY  # Only update if not yet assigned to coder
    ).all()
    
    for packet in packets:
        # Determine if this charge belongs in facility or ProFee packet
        if charge.charge_type == ChargeType.FACILITY and packet.packet_type == PacketType.FACILITY:
            # Add charge to packet
            packet.charges_data.append(serialize_charge(charge))
            packet.updated_at = datetime.now()
            logger.info(f"Added late charge {charge.charge_id} to packet {packet.packet_id}")
        
        elif charge.charge_type == ChargeType.PROFEE and packet.packet_type == PacketType.PROFEE:
            packet.charges_data.append(serialize_charge(charge))
            packet.updated_at = datetime.now()
            logger.info(f"Added late charge {charge.charge_id} to packet {packet.packet_id}")
    
    db.session.commit()
```

---

### 5. Encounter with No Discharge Message

**Scenario:** Patient discharged but ADT^A03 never arrives (interface failure)

**Handling:**
```python
# Scheduled job (runs daily at 2am)
def close_stale_encounters():
    """
    Find encounters still marked as OPEN but likely discharged
    Based on: No activity in 48+ hours, or hospital reports discharge in ADT^A08
    """
    
    cutoff_time = datetime.now() - timedelta(hours=48)
    
    stale_encounters = db.query(Encounter).filter(
        Encounter.status == EncounterStatus.OPEN,
        Encounter.updated_at < cutoff_time
    ).all()
    
    for encounter in stale_encounters:
        logger.warning(f"Stale encounter {encounter.encounter_id} - no discharge message received")
        
        # Mark for manual review
        encounter.status = EncounterStatus.PENDING_CODING  # Allow coding to proceed
        encounter.needs_review = True
        encounter.review_reason = "No discharge message received - auto-closed after 48 hours"
        
        # Estimate discharge time (last HL7 message received + 2 hours)
        last_message = db.query(HL7MessageLog).filter_by(
            encounter_id=encounter.encounter_id
        ).order_by(HL7MessageLog.received_at.desc()).first()
        
        encounter.discharge_datetime = last_message.received_at + timedelta(hours=2) if last_message else None
        
        # Generate codable packets
        generate_codable_packets(encounter)
    
    db.session.commit()
    
    return len(stale_encounters)
```

---

## Future Enhancements (V2)

**Not in scope for V1, but planned:**

### 1. Payer-Specific Rules
- Configuration: "For Medicare, always split radiology. For Medicaid, bundle."
- Requires: Payer identification in IN1 segment, rules engine

### 2. Real-Time Completeness Validation
- Don't create packet until all expected charges/results present
- Requires: Define "expected" charges per encounter type (ML model?)

### 3. MDM Message Support (Physician Notes)
- Parse MDM^T02 (clinical documents)
- Extract diagnosis statements, procedure descriptions
- Include in codable packet for coder context

### 4. CDI Integration
- Create CDI work queue (concurrent review while patient in-house)
- Query management workflow (CDI ↔ Physician)
- Track DRG impact of CDI queries

### 5. AI-Assisted Code Suggestions
- NLP on clinical notes (from MDM messages)
- Suggest ICD-10 codes based on documentation
- Flaggers for missing POA indicators, specificity issues

### 6. Advanced Charge Capture Rules
- Per-CPT configuration: "CPT 93000 → Always split 26/TC"
- Per-location: "ER procedures → Always ProFee, Inpatient procedures → Sometimes ProFee"

---

## Appendix A: Sample HL7 Messages

### ADT^A01 (Admit)
```
MSH|^~\&|EPIC|MAINHOSP|medcode|medcode|20260109083000||ADT^A01|MSG001|P|2.5
EVN|A01|20260109083000
PID|1||MRN123456||Doe^John^A||19600515|M|||123 Main St^^Ruralville^MT^59000||555-1234|||M
PV1|1|I|3N^301^B|1||||||MED|||||A|1234567890^Smith^Jane^MD^^^NPI||HOSP123456|||||||||||||||||||||||||20260109080000
IN1|1||INS001|Medicare Part A||||||12345678A
```

### ADT^A03 (Discharge)
```
MSH|^~\&|EPIC|MAINHOSP|medcode|medcode|20260112140000||ADT^A03|MSG010|P|2.5
EVN|A03|20260112140000
PID|1||MRN123456||Doe^John^A||19600515|M
PV1|1|I|3N^301^B|||||||MED|||||A|1234567890^Smith^Jane^MD^^^NPI||HOSP123456|||||||||||||||||||||||||20260109080000|20260112140000
```

### ORM^O01 (Order)
```
MSH|^~\&|LAB|MAINHOSP|medcode|medcode|20260109090000||ORM^O01|MSG002|P|2.5
PID|1||MRN123456||Doe^John^A||19600515|M
PV1|1|I|3N^301^B|||||||MED||||||1234567890^Smith^Jane^MD^^^NPI||HOSP123456
ORC|NW|ORD123|FIL456||IP
OBR|1|ORD123|FIL456|CBC^Complete Blood Count^L|||20260109090000
```

### ORU^R01 (Result)
```
MSH|^~\&|LAB|MAINHOSP|medcode|medcode|20260109110000||ORU^R01|MSG003|P|2.5
PID|1||MRN123456||Doe^John^A||19600515|M
PV1|1|I|3N^301^B|||||||MED||||||1234567890^Smith^Jane^MD^^^NPI||HOSP123456
OBR|1|ORD123|FIL456|CBC^Complete Blood Count^L|||20260109090000||||||||20260109110000|||F
OBX|1|NM|WBC^White Blood Cell Count||15.2|k/uL|4.0-11.0|H|||F
OBX|2|NM|HGB^Hemoglobin||12.5|g/dL|12.0-16.0|N|||F
```

### DFT^P03 (Charge - Uncoded)
```
MSH|^~\&|BILLING|MAINHOSP|medcode|medcode|20260110080000||DFT^P03|MSG005|P|2.5
PID|1||MRN123456||Doe^John^A||19600515|M
PV1|1|I|3N^301^B|||||||MED||||||1234567890^Smith^Jane^MD^^^NPI||HOSP123456
FT1|1||CG|20260109|20260109|CG|450^Emergency Room^L|||1|125.00|||||||0450|||||1234567890^Smith^Jane^MD^^^NPI
```

### DFT^P03 (Charge - Pre-Coded)
```
MSH|^~\&|BILLING|MAINHOSP|medcode|medcode|20260110090000||DFT^P03|MSG006|P|2.5
PID|1||MRN123456||Doe^John^A||19600515|M
PV1|1|I|3N^301^B|||||||MED||||||1234567890^Smith^Jane^MD^^^NPI||HOSP123456
FT1|1||CG|20260109|20260109|CG|300^Laboratory^L|||1|45.00|||||||0300|||I50.23^Acute on chronic systolic heart failure^I10|85025^Complete Blood Count^CPT||1234567890^Smith^Jane^MD^^^NPI
```

---

## Appendix B: Decision Matrix - Configuration vs. Hard-Coded

| Feature | V1 Approach | Configurability | Rationale (80/20) |
|---------|-------------|-----------------|-------------------|
| **Encounter types that trigger facility coding** | Configurable | ✅ Hospital admin sets | Different hospitals code ER differently |
| **ProFee billing model** | Configurable | ✅ Hospital admin sets | Employment models vary significantly |
| **Provider employment type** | Configurable | ✅ Per-provider setting | Required for ProFee routing |
| **Packet creation timing** | Hard-coded (immediate) | ❌ Always after discharge | 80% of hospitals want immediate coding |
| **Charge type determination (Facility/ProFee)** | Hard-coded logic | ❌ Revenue code + modifier rules | Universal billing standards |
| **ProFee interpretation services** | Hard-coded list | ❌ Predefined CPT categories | Standard across all hospitals |
| **Default attending physician** | Configurable | ✅ Optional hospital setting | Safety net for missing data |
| **Payer-specific rules** | Not in V1 | 🔮 V2 feature | Complex, deferred to V2 |
| **Per-CPT charge capture rules** | Not in V1 | 🔮 V2 feature | Rare edge cases, not worth complexity |

---

## Summary

This specification defines a **pragmatic, 80/20 approach** to processing HL7 messages and generating codable packets for rural hospitals:

✅ **What's included (V1):**
- Facility and ProFee packet creation
- Hospital-employed physician model (Scenario A)
- Immediate packet generation after discharge
- Provider roster with employment types
- Out-of-order message handling
- Comprehensive onboarding documentation

❌ **What's deferred (V2):**
- Complex payer-specific rules
- Real-time completeness validation
- Advanced CDI workflows
- MDM message parsing
- Per-CPT charge capture configurations

This approach gets rural hospitals up and running quickly while maintaining flexibility for future enhancements.

---

**Document Version:** 1.0  
**Effective Date:** January 2026  
**Contact:** product@medcode.com