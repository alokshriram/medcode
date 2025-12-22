# PDD-001: HL7 Ingestion and Codable Encounters

**Status:** Approved
**Created:** 2025-12-21
**Authors:** Product & Engineering
**Domain:** Encounters, Records, Workflow

---

## 1. Overview

### 1.1 Problem Statement

Medical coders need access to clinical data from hospital information systems to perform coding. This data arrives as HL7 v2.x messages from integration engines (Mirth, Rhapsody, Qvera). We need to:

1. Ingest HL7 messages from file uploads
2. Parse and correlate messages into patient encounters
3. Create codable work items for the coding workflow

### 1.2 Feature Summary

Add a "Manage Data" panel on the home page (accessible to users with `coder` role) that allows uploading files containing HL7 messages. The backend parses these messages, correlates them by encounter, and creates coding queue items when encounters are ready.

---

## 2. User Experience

### 2.1 Access Control

- **Tile visibility:** Users with the `coder` role
- **Location:** Home page, "Manage Data" panel

### 2.2 Upload Flow

1. User clicks "Manage Data" tile
2. User selects "Upload from local file share"
3. User selects one or more files containing HL7 messages
4. System processes files asynchronously
5. User receives feedback on processing status (messages parsed, encounters created/updated, errors)

---

## 3. HL7 Message Processing

### 3.1 Supported Message Types

| Message Type | Purpose | Key Data Extracted |
|--------------|---------|-------------------|
| **ADT** | Admit/Discharge/Transfer | Patient demographics, encounter creation, admit/discharge events |
| **ORU** | Observation Results | Lab results, radiology reports, clinical observations |
| **ORM** | Orders | Procedures ordered, tests ordered |
| **MDM** | Medical Documents | Clinical documents, transcriptions |
| **SIU** | Scheduling | Appointment context |

### 3.2 File Format Assumptions

- Files may contain **multiple HL7 messages** (batch format)
- **Multiple files** may be uploaded at once
- **No patient/encounter affinity per file** — messages are distributed randomly across files
- Files are similar to log captures from integration engines (periodic writes)

### 3.3 Idempotency

- **Message Control ID (MSH-10)** is used for idempotency
- Duplicate messages (same MSH-10) are logged but not reprocessed
- Raw messages are stored for audit/debugging regardless of duplicate status

---

## 4. Data Model

### 4.1 New Bounded Context: `encounters`

A new schema `encounters` is introduced to handle clinical data aggregation. This is separate from `records` (which handles higher-level medical record abstractions and AI summarization).

**Relationship flow:**
```
HL7 Files → encounters schema → records schema → workflow schema
                (raw clinical      (codable         (work items,
                 aggregation)       snapshots)       assignments)
```

### 4.2 Schema: `encounters`

#### `hl7_messages` (Raw Audit Log)
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| message_control_id | VARCHAR(100) | MSH-10, used for idempotency |
| message_type | VARCHAR(10) | ADT, ORU, ORM, MDM, SIU |
| event_type | VARCHAR(10) | A01, A03, R01, etc. |
| raw_content | TEXT | Original HL7 message |
| file_source | VARCHAR(500) | Source filename |
| processing_status | VARCHAR(50) | pending, processed, error, duplicate |
| error_message | TEXT | Error details if failed |
| created_at | TIMESTAMPTZ | Ingestion timestamp |

#### `patients`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| mrn | VARCHAR(100) | Medical Record Number (unique) |
| name_family | VARCHAR(255) | Last name |
| name_given | VARCHAR(255) | First name |
| date_of_birth | DATE | DOB |
| gender | VARCHAR(10) | M, F, O, U |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

#### `encounters` (Core Linking Entity)
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| patient_id | UUID | FK to patients |
| visit_number | VARCHAR(100) | PV1-19, unique identifier |
| encounter_type | VARCHAR(50) | inpatient, outpatient, emergency, observation |
| service_line | VARCHAR(100) | Derived via rules |
| payer_identifier | VARCHAR(100) | Insurance/payer info |
| admit_datetime | TIMESTAMPTZ | |
| discharge_datetime | TIMESTAMPTZ | |
| admitting_diagnosis | TEXT | |
| discharge_disposition | VARCHAR(50) | |
| status | VARCHAR(50) | open, closed, ready_to_code, coded |
| ready_to_code_at | TIMESTAMPTZ | When became ready |
| ready_to_code_reason | VARCHAR(50) | discharge, timeout_manual, manual_override |
| last_message_at | TIMESTAMPTZ | For timeout detection |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

#### `diagnoses`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| encounter_id | UUID | FK to encounters |
| hl7_message_id | UUID | Source message |
| set_id | INTEGER | DG1-1 |
| diagnosis_code | VARCHAR(20) | ICD code if present |
| diagnosis_description | TEXT | |
| diagnosis_type | VARCHAR(50) | admitting, working, final |
| coding_method | VARCHAR(20) | ICD-10-CM, etc. |
| created_at | TIMESTAMPTZ | |

#### `procedures`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| encounter_id | UUID | FK to encounters |
| hl7_message_id | UUID | Source message |
| set_id | INTEGER | PR1-1 |
| procedure_code | VARCHAR(20) | CPT/ICD-PCS if present |
| procedure_description | TEXT | |
| procedure_datetime | TIMESTAMPTZ | |
| performing_physician | VARCHAR(255) | |
| performing_physician_id | VARCHAR(50) | |
| created_at | TIMESTAMPTZ | |

#### `observations`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| encounter_id | UUID | FK to encounters |
| hl7_message_id | UUID | Source message |
| set_id | INTEGER | OBX-1 |
| observation_identifier | VARCHAR(100) | OBX-3 |
| observation_value | TEXT | OBX-5 |
| units | VARCHAR(50) | OBX-6 |
| reference_range | VARCHAR(100) | OBX-7 |
| abnormal_flags | VARCHAR(20) | OBX-8 |
| observation_datetime | TIMESTAMPTZ | |
| result_status | VARCHAR(10) | OBX-11 |
| created_at | TIMESTAMPTZ | |

#### `orders`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| encounter_id | UUID | FK to encounters |
| hl7_message_id | UUID | Source message |
| order_control | VARCHAR(10) | ORC-1 |
| placer_order_number | VARCHAR(100) | ORC-2 |
| filler_order_number | VARCHAR(100) | ORC-3 |
| order_status | VARCHAR(20) | |
| order_datetime | TIMESTAMPTZ | |
| ordering_provider | VARCHAR(255) | |
| order_type | VARCHAR(100) | OBR-4 Universal Service ID |
| created_at | TIMESTAMPTZ | |

#### `documents`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| encounter_id | UUID | FK to encounters |
| hl7_message_id | UUID | Source message |
| document_type | VARCHAR(100) | TXA-2 |
| document_status | VARCHAR(50) | |
| origination_datetime | TIMESTAMPTZ | |
| author | VARCHAR(255) | |
| content | TEXT | Document text from OBX |
| created_at | TIMESTAMPTZ | |

---

## 5. Encounter Ready-to-Code Logic

### 5.1 Hybrid Trigger Model

An encounter becomes "ready to code" when:

| Trigger | Condition | `ready_to_code_reason` |
|---------|-----------|------------------------|
| **Discharge** | ADT^A03 (or similar discharge event) received | `discharge` |
| **Timeout** | No messages received for 72 hours AND flagged for review | `timeout_manual` |
| **Manual** | User explicitly marks ready | `manual_override` |

### 5.2 Timeout Handling

- Background job checks for encounters where `last_message_at < NOW() - 72 hours`
- These are flagged as `status = 'stale'` (or similar)
- User reviews and can manually move to `ready_to_code` state
- Reason is recorded as `timeout_manual`

---

## 6. Snapshot Model

### 6.1 Decision: Snapshot on Ready-to-Code

When an encounter reaches `ready_to_code` state:
1. A **snapshot** of all encounter data is created in the `records` schema
2. This snapshot represents point-in-time clinical data
3. Coders work against the snapshot, not live `encounters` data

### 6.2 Rationale

- **Audit defensibility:** Documentation of what coder had access to
- **Consistency:** Data doesn't change during coding session
- **Legal protection:** Point-in-time record for disputes

### 6.3 Snapshot Refresh

- Users can request a "refresh" to pull latest encounter data
- Creates a new snapshot version
- Logs who refreshed and when
- May reset work item status if significant changes detected

---

## 7. Coding Queue Work Items

### 7.1 Professional vs. Facility Billing

A single encounter can generate multiple work items based on billing components:

| Component | Who Bills | Claim Form | Primary Codes |
|-----------|-----------|------------|---------------|
| **Facility** | Hospital | UB-04 | ICD-10, Revenue codes |
| **Professional** | Physician | CMS-1500 | CPT (modifier 26) |

### 7.2 Work Item Creation Logic

#### Facility Work Item
- **Default:** Always created when encounter reaches `ready_to_code`
- **Configurable:** `always_create_facility` setting (default: true)

#### Professional Work Item
- **Default:** Created conditionally
- **Conditions (any):**
  - Interpreting physician identified (OBR-32, OBR-33)
  - Performing surgeon identified (PR1-8)
  - Service line in `professional_component_services` list
- **Configurable:**
  - `always_create_professional` setting (default: false)
  - `professional_component_services` list (default: radiology, pathology, cardiology, surgery)
  - `professional_physician_fields` list

### 7.3 Queue Metadata

Work items include metadata for queue filtering:

| Field | Source | Purpose |
|-------|--------|---------|
| `billing_component` | facility / professional | Split queues |
| `encounter_type` | From encounter | Filter by inpatient/outpatient/ED |
| `service_line` | Derived via rules | Specialty queues |
| `payer_identifier` | From encounter | Payer-specific queues |
| `priority` | Calculated | Work prioritization |

---

## 8. Service Line Derivation

### 8.1 Challenge

Service line is rarely explicit in HL7; must be derived from available fields.

### 8.2 Rule-Based Approach

A configurable `service_line_rules` table:

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| rule_type | VARCHAR(50) | diagnostic_section, department, procedure_range, default |
| match_pattern | VARCHAR(255) | Pattern to match |
| service_line | VARCHAR(100) | Resulting service line |
| priority | INTEGER | Lower = evaluated first |
| is_active | BOOLEAN | Enable/disable rule |

### 8.3 Default Rules

| Priority | Rule Type | Match | Service Line |
|----------|-----------|-------|--------------|
| 1 | diagnostic_section | RAD | Radiology |
| 1 | diagnostic_section | LAB | Laboratory |
| 1 | diagnostic_section | CARD | Cardiology |
| 2 | procedure_range | 70000-79999 | Radiology |
| 2 | procedure_range | 80000-89999 | Laboratory |
| 2 | procedure_range | 90000-99999 | E&M/Medicine |
| 100 | default | * | Unassigned |

### 8.4 Unassigned Handling

- Items with `service_line = 'Unassigned'` go to a triage queue
- Users can manually assign and optionally create new rules

---

## 9. Configuration Surface

### 9.1 System Configuration Table

`coding_configuration` (in `workflow` schema or new `config` schema):

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `always_create_facility` | boolean | true | Create facility work item for all encounters |
| `always_create_professional` | boolean | false | Create professional work item regardless of conditions |
| `professional_component_services` | string[] | [radiology, pathology, cardiology, surgery] | Service lines that trigger professional component |
| `professional_physician_fields` | string[] | [OBR-32, OBR-33, PR1-8] | HL7 fields to check for physician |
| `encounter_timeout_hours` | integer | 72 | Hours before flagging stale encounter |

---

## 10. Security & HIPAA Considerations

### 10.1 PHI Handling

- All HL7 data contains PHI (patient names, MRNs, clinical data)
- Data at rest: Encrypted (database-level encryption)
- Data in transit: HTTPS/TLS only
- File uploads: Secure handling, no client-side storage

### 10.2 Access Control

- Upload feature: `coder` role required
- Encounter data: Role-based access
- Audit logging: All access to PHI logged

### 10.3 Data Retention

- Raw HL7 messages retained for compliance (retention period TBD)
- Snapshots retained indefinitely for audit trail

---

## 11. API Endpoints

### 11.1 New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/encounters/upload` | Upload HL7 files |
| GET | `/api/v1/encounters/upload/{job_id}` | Check upload processing status |
| GET | `/api/v1/encounters` | List encounters (with filters) |
| GET | `/api/v1/encounters/{id}` | Get encounter details |
| POST | `/api/v1/encounters/{id}/ready-to-code` | Manually mark ready to code |
| POST | `/api/v1/encounters/{id}/refresh-snapshot` | Refresh snapshot for coding |

---

## 12. Open Items / Future Considerations

| Item | Status | Notes |
|------|--------|-------|
| HL7 FHIR support | Deferred | Future integration option |
| Real-time streaming | Deferred | Current scope is file upload only |
| AI summarization trigger | Deferred | Will integrate with existing records.medical_records |
| Payer rules engine | Deferred | Payer-specific coding requirements |

---

## 13. Decisions Log

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| 1 | Use PostgreSQL ARRAY for user roles | Fixed small set (coder, admin, supervisor); simpler queries | 2025-12-21 |
| 2 | Create new `encounters` schema | Separates raw clinical aggregation from higher-level records | 2025-12-21 |
| 3 | Snapshot on ready-to-code | Audit defensibility, coder consistency, legal protection | 2025-12-21 |
| 4 | MSH-10 for idempotency | Standard HL7 message identifier; prevents duplicate processing | 2025-12-21 |
| 5 | Hybrid ready-to-code trigger | Discharge event OR 72hr timeout with manual confirmation | 2025-12-21 |
| 6 | Configurable professional/facility split | Organizations have different billing structures | 2025-12-21 |
| 7 | Rule-based service line derivation | HL7 doesn't reliably include service line; needs flexibility | 2025-12-21 |
