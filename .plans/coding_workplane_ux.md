The Typical Medical Coding Workstation Layout
Most coding interfaces follow a split-screen paradigm with three to four major zones. Think of it like an IDE for healthcare—you've got your source material on one side, your "code editor" on the other, and validation/output panels below.
Zone 1: Clinical Documentation Viewer (Left Panel, ~40-50% of screen)
This is where coders read the source material. It typically includes:
Document Tree/Navigator

Discharge summary
H&P (History & Physical)
Progress notes (expandable by date)
Operative reports
Consultation notes
Lab results (often collapsed by default)
Radiology reports
Pathology reports

The viewer itself usually has:

Text highlighting capability (coder marks phrases that support codes)
Sticky notes/annotations
Search within documents
"Jump to" links when CDI has flagged specific sections

Rural hospital reality: Your coders often deal with scanned PDFs from paper charts, faxed consult notes, and handwritten physician orders. The document viewer needs to handle image-based documents, not just structured text.
Zone 2: Code Entry Panel (Right Panel, ~40-50% of screen)
This is the coder's primary workspace, typically organized as:
Diagnosis Codes Section (ICD-10-CM)
Principal Diagnosis: [___________] 🔍
  └── I21.09 - STEMI involving other coronary artery of anterior wall
      POA: Y ▼  |  Remove

Secondary Diagnoses:
  1. [___________] 🔍
     └── E11.9 - Type 2 diabetes mellitus without complications
         POA: Y ▼  |  Remove
  2. [___________] 🔍
     └── I10 - Essential hypertension
         POA: Y ▼  |  Remove
  [+ Add Diagnosis]
Procedure Codes Section (ICD-10-PCS for facility / CPT for professional)
Principal Procedure: [___________] 🔍
  └── 02703DZ - Dilation of coronary artery, one artery, percutaneous
      Date: 01/15/2026  |  Surgeon: Dr. Smith  |  Remove

Secondary Procedures:
  [+ Add Procedure]
Key UI elements in the code entry area:

Code search field (the 🔍) - This is heavily used. Coders search by:

Code number (I21.09)
Keywords ("STEMI", "myocardial infarction")
Alphabetic index navigation


POA (Present on Admission) indicator dropdown - Required for every diagnosis:

Y = Yes, present on admission
N = No, developed during stay
U = Unknown/insufficient documentation
W = Clinically undetermined
Exempt (certain codes don't require POA)


Code validation indicators - Real-time feedback:

✓ Green = Valid code, no conflicts
⚠️ Yellow = Warning (check excludes, missing laterality)
❌ Red = Invalid (non-billable code, edit conflict)



Zone 3: Validation & Grouper Panel (Bottom or Right-Side Panel)
This shows the coder what their code selections produce:
DRG/APC Calculator (updates in real-time)
┌─────────────────────────────────────────────────┐
│  MS-DRG: 247                                    │
│  Description: Perc Cardiovasc Proc w Drug-      │
│               Eluting Stent w/o MCC             │
│  Relative Weight: 2.0124                        │
│  Expected Reimbursement: ~$18,450               │
│                                                 │
│  ⚠️ If you add MCC diagnosis, DRG shifts to 246│
│     (+$4,200 estimated impact)                  │
└─────────────────────────────────────────────────┘
Edit Checker / Claim Scrubber
┌─────────────────────────────────────────────────┐
│  NCCI Edits: ✓ Pass                             │
│  MUE Check: ✓ Pass                              │
│  Code Specificity: ⚠️ E11.9 - Consider more     │
│                       specific diabetes code     │
│  Excludes Check: ✓ Pass                         │
│  Sequencing: ✓ Correct                          │
└─────────────────────────────────────────────────┘
Zone 4: Worklist/Queue Panel (Often a Collapsible Sidebar or Top Bar)
Coders work through accounts from a queue:
Today's Queue: 23 accounts remaining
┌──────┬────────────┬──────────┬─────────┬──────────┐
│ Acct │ Patient    │ Type     │ DOS     │ Priority │
├──────┼────────────┼──────────┼─────────┼──────────┤
│►1234 │ Smith, J   │ IP-Surg  │ 01/15   │ 🔴 STAT  │
│ 1235 │ Jones, M   │ IP-Med   │ 01/14   │ Normal   │
│ 1236 │ Davis, R   │ Obs      │ 01/15   │ Normal   │
│ 1237 │ Wilson, P  │ ED       │ 01/15   │ Normal   │
└──────┴────────────┴──────────┴─────────┴──────────┘
Queue metadata typically includes:

Account/encounter number
Patient name and MRN
Encounter type (Inpatient, Outpatient, ED, Observation)
Discharge date
Days in DNFB (Discharged Not Final Billed)
Priority flags (STAT = high-dollar or compliance-sensitive)
CDI query status (pending physician response?)


What Makes Coders Fast or Slow
Here's what separates a 45-account-per-day coder from a 25-account-per-day coder:
Speed boosters:

Keyboard shortcuts for common actions
Code search that's fast and smart (autocomplete, fuzzy matching)
One-click to copy codes from previous encounters
Smart suggestions based on documentation ("Did you mean to code the CHF?")
Inline code validation (don't make me click Submit to find errors)

Speed killers (things your system should avoid):

Slow document loading (especially scanned images)
Having to scroll between documentation and code entry
Modal pop-ups that interrupt workflow
Requiring mouse clicks for things that should be keyboard-driven
Unclear error messages ("Code invalid" vs. "I21.09 requires 5th character for laterality")


Technical Requirements This Implies
For your React frontend:

Split-pane layout with resizable panels (react-split-pane or similar)
Virtualized lists for document navigation and code search results (large code tables)
Debounced search on the code lookup (coders type fast)
Optimistic UI updates for code entry (don't wait for server roundtrip)
Keyboard navigation throughout—Tab, Enter, arrow keys, shortcuts like Ctrl+D for "add diagnosis"

For your FastAPI backend:

Sub-100ms response on code search endpoints (index your ICD-10 table properly)
Real-time DRG calculation endpoint (or client-side if you can handle the grouper logic)
Batch validation endpoint that checks all codes at once against NCCI/MUE edits
WebSocket or polling for CDI query status updates