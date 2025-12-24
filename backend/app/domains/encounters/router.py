"""API routes for the encounters domain."""
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Query, UploadFile, File

from app.core.dependencies import CurrentUser, DbSession
from app.domains.encounters.service import EncountersService
from app.domains.encounters.hl7 import HL7BatchParser
from app.domains.encounters.schemas import (
    EncounterResponse,
    EncounterDetailResponse,
    EncounterListResponse,
    EncounterListWithPatientResponse,
    EncounterWithPatientResponse,
    EncounterFilters,
    PatientResponse,
    HL7MessageResponse,
    ServiceLineRuleResponse,
    MarkReadyToCodeRequest,
    UploadResult,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Upload Endpoints ---

@router.post("/upload", response_model=UploadResult)
async def upload_hl7_files(
    db: DbSession,
    current_user: CurrentUser,
    files: list[UploadFile] = File(..., description="HL7 message files to upload"),
):
    """
    Upload one or more files containing HL7 messages.

    Each file can contain multiple HL7 messages (batch format).
    Messages are parsed, validated, and stored. Encounters are created
    or updated based on the message content.

    Requires authentication with 'coder' role.
    """
    # Check for coder role
    if "coder" not in current_user.roles and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Coder role required",
        )

    service = EncountersService(db)
    batch_parser = HL7BatchParser()

    result = UploadResult(
        job_id=str(UUID(int=0)),  # Placeholder - could be async job ID
        files_received=len(files),
        messages_found=0,
        messages_processed=0,
        messages_failed=0,
        encounters_created=0,
        encounters_updated=0,
        errors=[],
    )

    for upload_file in files:
        try:
            # Read file content
            content = await upload_file.read()
            content_str = content.decode("utf-8", errors="replace")

            # Parse messages from file
            parsed_messages = batch_parser.parse_file_content(content_str)
            result.messages_found += len(parsed_messages)

            # Process each message
            for parsed in parsed_messages:
                try:
                    process_result = service.process_hl7_message(
                        parsed=parsed,
                        file_source=upload_file.filename,
                    )

                    if process_result.get("error"):
                        result.messages_failed += 1
                        result.errors.append(
                            f"{upload_file.filename}: {process_result['error']}"
                        )
                    elif process_result.get("is_duplicate"):
                        # Duplicates are counted as processed (idempotent)
                        result.messages_processed += 1
                    else:
                        result.messages_processed += 1
                        if process_result.get("encounter_created"):
                            result.encounters_created += 1
                        else:
                            result.encounters_updated += 1

                except Exception as e:
                    result.messages_failed += 1
                    result.errors.append(
                        f"{upload_file.filename}: Message processing error - {str(e)}"
                    )
                    logger.exception(f"Error processing message from {upload_file.filename}")

        except Exception as e:
            result.errors.append(f"{upload_file.filename}: File read error - {str(e)}")
            logger.exception(f"Error reading file {upload_file.filename}")

    return result


# --- Encounter Endpoints ---

@router.get("/", response_model=EncounterListResponse | EncounterListWithPatientResponse)
def list_encounters(
    db: DbSession,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: str | None = Query(None, description="Filter by status"),
    encounter_type: str | None = Query(None, description="Filter by encounter type"),
    service_line: str | None = Query(None, description="Filter by service line"),
    patient_mrn: str | None = Query(None, description="Filter by patient MRN"),
    visit_number: str | None = Query(None, description="Filter by visit number"),
    include_patient: bool = Query(False, description="Include patient info in response"),
):
    """
    List encounters with optional filters.

    Requires authentication.
    """
    filters = EncounterFilters(
        status=status,
        encounter_type=encounter_type,
        service_line=service_line,
        patient_mrn=patient_mrn,
        visit_number=visit_number,
    )

    service = EncountersService(db)
    encounters, total = service.list_encounters(
        filters=filters, skip=skip, limit=limit, include_patient=include_patient
    )

    if include_patient:
        return EncounterListWithPatientResponse(
            encounters=[EncounterWithPatientResponse.model_validate(e) for e in encounters],
            total=total,
            skip=skip,
            limit=limit,
        )

    return EncounterListResponse(
        encounters=[EncounterResponse.model_validate(e) for e in encounters],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{encounter_id}", response_model=EncounterDetailResponse)
def get_encounter(
    encounter_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get encounter with all related clinical data.

    Requires authentication.
    """
    service = EncountersService(db)
    encounter = service.get_encounter_with_details(encounter_id)

    if not encounter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Encounter not found",
        )

    return encounter


@router.post("/{encounter_id}/ready-to-code", response_model=EncounterResponse)
def mark_ready_to_code(
    encounter_id: UUID,
    request: MarkReadyToCodeRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Manually mark an encounter as ready to code.

    Requires authentication with 'coder' role.
    """
    # Check for coder role
    if "coder" not in current_user.roles and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Coder role required",
        )

    service = EncountersService(db)
    encounter = service.mark_ready_to_code(encounter_id, request.reason)

    if not encounter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Encounter not found",
        )

    return encounter


# --- Patient Endpoints ---

@router.get("/patients/{mrn}", response_model=PatientResponse)
def get_patient_by_mrn(
    mrn: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get patient by MRN.

    Requires authentication.
    """
    service = EncountersService(db)
    patient = service.get_patient_by_mrn(mrn)

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    return patient


# --- Service Line Rules Endpoints ---

@router.get("/config/service-line-rules", response_model=list[ServiceLineRuleResponse])
def list_service_line_rules(
    db: DbSession,
    current_user: CurrentUser,
):
    """
    List all active service line rules.

    Requires authentication.
    """
    service = EncountersService(db)
    return service.get_service_line_rules()


# --- Stale Encounters Endpoint ---

@router.get("/stale", response_model=list[EncounterResponse])
def get_stale_encounters(
    db: DbSession,
    current_user: CurrentUser,
    hours: int = Query(72, ge=1, le=720, description="Hours without activity"),
):
    """
    Get encounters that haven't received messages in the specified hours.

    Requires authentication with 'admin' or 'coder' role.
    """
    if "coder" not in current_user.roles and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Coder or admin role required",
        )

    service = EncountersService(db)
    return service.get_stale_encounters(hours=hours)


@router.post("/stale/flag", response_model=dict)
def flag_stale_encounters(
    db: DbSession,
    current_user: CurrentUser,
    hours: int = Query(72, ge=1, le=720, description="Hours without activity"),
):
    """
    Flag stale encounters for review (changes status to 'stale').

    Requires authentication with 'admin' role.
    """
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    service = EncountersService(db)
    count = service.flag_stale_encounters(hours=hours)

    return {"flagged_count": count}
