# Coding Workbench Implementation Context

## Summary

This document captures the context from implementing the Coding Workbench feature - a split-screen UI for medical coders to view clinical documentation and enter diagnosis/procedure codes.

## Implementation Overview

### What Was Built

A full-stack coding workbench with:
- **Split-screen paradigm**: Clinical documentation on left (~50%), coding workbench on right (~50%)
- **Dynamic layouts**: Adapts based on `billing_component` (facility uses ICD-10-PCS, professional uses CPT)
- **Document viewer**: Shows clinical data from encounter snapshots
- **Code entry panel**: Diagnosis (ICD-10-CM) and procedure codes with POA indicators
- **Code persistence**: CodingResult table stores codes with user tracking

### Key Decisions Made

1. **Snapshot Timing**: Snapshots are created on "ready-to-code" event (not when workbench opens)
2. **Code Persistence**: Uses dedicated `CodingResult` table with `coded_by` user tracking
3. **Queue Architecture**: Leveraged existing `CodingQueueItem` and `EncounterSnapshot` models (they existed but had no API)

## Files Created/Modified

### Backend

| File | Description |
|------|-------------|
| `backend/app/domains/workflow/coding_queue_router.py` | **NEW** - API endpoints for queue operations |
| `backend/app/domains/workflow/schemas.py` | Added queue item, snapshot, and coding result schemas |
| `backend/app/domains/workflow/coding_queue_service.py` | Added `list_queue_items_with_patient`, `save_coding_results`, `get_coding_results` |
| `backend/app/domains/workflow/models.py` | Added `CodingResult` model |
| `backend/app/main.py` | Registered coding queue router |
| `backend/alembic/versions/20260117_add_coding_results.py` | **NEW** - Migration for coding_results table |

### Frontend

| File | Description |
|------|-------------|
| `frontend/src/api/codingQueue.ts` | **NEW** - API client for coding queue endpoints |
| `frontend/src/hooks/useCodingQueue.ts` | **NEW** - React Query hooks for queue operations |
| `frontend/src/components/coding/SplitPane.tsx` | **NEW** - Resizable split container |
| `frontend/src/components/coding/DocumentViewer/DocumentViewer.tsx` | **NEW** - Main document viewer |
| `frontend/src/components/coding/DocumentViewer/DocumentTree.tsx` | **NEW** - Category navigation tree |
| `frontend/src/components/coding/DocumentViewer/DocumentContent.tsx` | **NEW** - Content display with search |
| `frontend/src/components/coding/CodingPanel/CodingPanel.tsx` | **NEW** - Main coding panel |
| `frontend/src/components/coding/CodingPanel/DiagnosisEntry.tsx` | **NEW** - ICD-10-CM entry with POA |
| `frontend/src/components/coding/CodingPanel/ProcedureEntry.tsx` | **NEW** - ICD-10-PCS or CPT entry |
| `frontend/src/components/coding/CodingPanel/CodeSearchInput.tsx` | **NEW** - Autocomplete code search |
| `frontend/src/components/coding/index.ts` | **NEW** - Component exports |
| `frontend/src/pages/CodingWorkbenchPage.tsx` | **NEW** - Main workbench page |
| `frontend/src/pages/CodePage.tsx` | Updated to use queue API with filters |
| `frontend/src/App.tsx` | Added `/code/:queueItemId` route |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/workflow/queue` | List queue items with filters |
| GET | `/api/v1/workflow/queue/{id}` | Get queue item with snapshot |
| POST | `/api/v1/workflow/queue/{id}/assign` | Assign to coder |
| POST | `/api/v1/workflow/queue/{id}/complete` | Mark coding complete |
| POST | `/api/v1/workflow/queue/{id}/refresh-snapshot` | Refresh snapshot data |
| GET | `/api/v1/workflow/queue/{id}/codes` | Get saved codes |
| POST | `/api/v1/workflow/queue/{id}/codes` | Save coding results |

## Data Models

### CodingResult Table

```sql
CREATE TABLE workflow.coding_results (
    id UUID PRIMARY KEY,
    tenant_id UUID,
    queue_item_id UUID NOT NULL REFERENCES workflow.coding_queue_items(id),
    code VARCHAR(20) NOT NULL,
    code_type VARCHAR(20) NOT NULL,  -- ICD-10-CM, ICD-10-PCS, CPT
    description TEXT NOT NULL,
    code_category VARCHAR(20) NOT NULL,  -- diagnosis, procedure
    is_principal BOOLEAN DEFAULT FALSE,
    poa_indicator VARCHAR(5),  -- Y, N, U, W, 1 (exempt)
    sequence INTEGER NOT NULL,
    procedure_date TIMESTAMP WITH TIME ZONE,
    coded_by UUID NOT NULL,
    coded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### React Query Hooks

```typescript
// List queue items with filters
useCodingQueue({ status, billingComponent, assignedToMe, skip, limit })

// Get single queue item with snapshot
useCodingQueueItem(queueItemId)

// Mutations
useAssignQueueItem()
useCompleteQueueItem()
useRefreshSnapshot()
useSaveCodingResults()
useCodingResults(queueItemId)
```

## Component Architecture

```
/code                     (work list - queue items)
/code/:queueItemId        (coding workbench)
      |
      +-- CodingWorkbenchPage
           |
           +-- SplitPane (resizable left/right)
                |
                +-- DocumentViewer (left 50%)
                |    +-- DocumentTree (sidebar)
                |    +-- DocumentContent (main area)
                |
                +-- CodingPanel (right 50%)
                     +-- DiagnosisEntry (ICD-10-CM + POA)
                     +-- ProcedureEntry (ICD-10-PCS or CPT based on billing_component)
                     +-- CodeSearchInput (uses existing catalog API)
```

## Data Flow

1. `CodePage` loads → `useCodingQueue()` fetches queue items with patient info
2. User clicks row → Navigate to `/code/:queueItemId`
3. `CodingWorkbenchPage` loads → `useCodingQueueItem(id)` fetches item + snapshot
4. If pending → auto-assign via `useAssignQueueItem()`
5. Render SplitPane:
   - Left: `DocumentViewer` with snapshot data
   - Right: `CodingPanel` with billing_component
6. User enters codes via `CodeSearchInput` (uses `useCatalogSearch`)
7. User clicks Save → `useSaveCodingResults()` persists codes
8. User clicks Complete → `useCompleteQueueItem()` marks complete
9. Navigate back to queue

## Key Technical Details

### Billing Component Logic

- **Facility**: Uses ICD-10-PCS for procedures
- **Professional**: Uses CPT for procedures
- Both use ICD-10-CM for diagnoses

### POA Indicators (Present on Admission)

- **Y**: Yes, present at admission
- **N**: No, not present at admission
- **U**: Unknown/insufficient documentation
- **W**: Clinically undetermined
- **1**: Exempt from POA reporting

### Snapshot Data Structure

```typescript
interface SnapshotData {
  patient: {
    mrn: string
    name_given: string
    name_family: string
    date_of_birth: string
    gender: string
  }
  encounter: {
    visit_number: string
    encounter_type: string
    admit_datetime: string
    discharge_datetime: string
    attending_provider: string
    facility_name: string
  }
  diagnoses: Array<{ code, description, type, poa_indicator }>
  procedures: Array<{ code, description, type, date }>
  observations: Array<{ type, value, unit, datetime }>
  orders: Array<{ type, description, status, datetime }>
  documents: Array<{ title, content, datetime, author }>
  snapshot_created_at: string
}
```

## Pending Work / Future Enhancements

- Validation Panel (DRG/APC calculator, NCCI edits)
- Keyboard shortcuts for faster coding
- Text highlighting/annotations in documents
- Multi-user locking for concurrent access
- Code suggestion/validation using AI

## Migration Commands

```bash
# Run the migration to create coding_results table
cd backend
alembic upgrade head
```

## Git History

- Branch: `controller-plane`
- Commit: `cebccf2` - "Add coding workbench with split-pane UI for medical coders"
- Files changed: 22 files, 3210 insertions
