"""Tests for HL7 file upload endpoint."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.core.security import TokenPayload, verify_token
from app.core.database import get_db


# Sample HL7 messages for testing
SAMPLE_ADT_A01 = b"""MSH|^~\\&|EPIC|HOSPITAL|MEDCODE|CODING|20251215120000||ADT^A01|MSG00001|P|2.5
PID|1||12345678^^^MRN||Smith^John^A||19800515|M|||123 Main St^^Chicago^IL^60601
PV1|1|I|4N^401^A^^^N||||1234567^Jones^Mary^MD|||SUR||||||||V123456789^^^VISIT|||||||||||||||||||||||||20251215100000"""

SAMPLE_ORU_R01 = b"""MSH|^~\\&|LAB|HOSPITAL|MEDCODE|CODING|20251216080000||ORU^R01|MSG00003|P|2.5
PID|1||12345678^^^MRN||Smith^John^A||19800515|M
PV1|1|I|4N^401^A|||||||||||||||V123456789^^^VISIT
ORC|RE|ORD001|FIL001||CM||||20251216070000|^Ordering^Doctor
OBR|1|ORD001|FIL001|80053^METABOLIC PANEL^CPT|||20251216070000||||||||^Ordering^Doctor||||||20251216080000|||F||||||LAB
OBX|1|NM|2345-7^GLUCOSE^LN||95|mg/dL|70-100|N|||F|||20251216075500"""

SAMPLE_BATCH = SAMPLE_ADT_A01 + b"\n" + SAMPLE_ORU_R01


def make_token_payload(sub: str, email: str, roles: list[str]) -> TokenPayload:
    """Create a TokenPayload with default expiration."""
    return TokenPayload(
        sub=sub,
        exp=datetime.now(timezone.utc) + timedelta(hours=1),
        email=email,
        roles=roles,
    )


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session."""
    mock_session = MagicMock()
    return mock_session


@pytest.fixture
def coder_client(mock_db):
    """Client with coder authentication."""
    def override_verify_token():
        return make_token_payload(
            sub="test-user-id",
            email="coder@example.com",
            roles=["coder"],
        )

    def override_get_db():
        return mock_db

    app.dependency_overrides[verify_token] = override_verify_token
    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(mock_db):
    """Client with admin authentication."""
    def override_verify_token():
        return make_token_payload(
            sub="admin-user-id",
            email="admin@example.com",
            roles=["admin"],
        )

    def override_get_db():
        return mock_db

    app.dependency_overrides[verify_token] = override_verify_token
    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def viewer_client(mock_db):
    """Client with viewer authentication (no coder role)."""
    def override_verify_token():
        return make_token_payload(
            sub="viewer-user-id",
            email="viewer@example.com",
            roles=["viewer"],
        )

    def override_get_db():
        return mock_db

    app.dependency_overrides[verify_token] = override_verify_token
    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()


class TestUploadEndpoint:
    """Tests for POST /api/v1/encounters/upload."""

    def test_upload_requires_authentication(self, client):
        """Test that upload endpoint requires authentication."""
        files = {"files": ("test.hl7", SAMPLE_ADT_A01, "text/plain")}

        response = client.post("/api/v1/encounters/upload", files=files)

        # Should return 401 or 403 without auth
        assert response.status_code in (401, 403)

    def test_upload_requires_coder_role(self, viewer_client):
        """Test that upload endpoint requires coder role."""
        files = {"files": ("test.hl7", SAMPLE_ADT_A01, "text/plain")}
        response = viewer_client.post("/api/v1/encounters/upload", files=files)

        assert response.status_code == 403
        assert "Coder role required" in response.json()["detail"]

    def test_upload_single_file(self, coder_client):
        """Test uploading a single HL7 file."""
        with patch("app.domains.encounters.router.EncountersService") as MockService:
            mock_service = MockService.return_value
            mock_service.process_hl7_message.return_value = {
                "message_id": "msg-123",
                "is_duplicate": False,
                "encounter_id": "enc-123",
                "encounter_created": True,
                "patient_id": "pat-123",
                "error": None,
            }

            files = {"files": ("test.hl7", SAMPLE_ADT_A01, "text/plain")}
            response = coder_client.post("/api/v1/encounters/upload", files=files)

            assert response.status_code == 200
            data = response.json()
            assert data["files_received"] == 1
            assert data["messages_found"] == 1
            assert data["messages_processed"] == 1
            assert data["encounters_created"] == 1

    def test_upload_multiple_files(self, coder_client):
        """Test uploading multiple HL7 files."""
        with patch("app.domains.encounters.router.EncountersService") as MockService:
            mock_service = MockService.return_value
            mock_service.process_hl7_message.return_value = {
                "message_id": "msg-123",
                "is_duplicate": False,
                "encounter_id": "enc-123",
                "encounter_created": True,
                "patient_id": "pat-123",
                "error": None,
            }

            files = [
                ("files", ("file1.hl7", SAMPLE_ADT_A01, "text/plain")),
                ("files", ("file2.hl7", SAMPLE_ORU_R01, "text/plain")),
            ]
            response = coder_client.post("/api/v1/encounters/upload", files=files)

            assert response.status_code == 200
            data = response.json()
            assert data["files_received"] == 2
            assert data["messages_found"] == 2

    def test_upload_batch_file(self, coder_client):
        """Test uploading a batch file with multiple messages."""
        with patch("app.domains.encounters.router.EncountersService") as MockService:
            mock_service = MockService.return_value
            # First call creates encounter, second updates
            mock_service.process_hl7_message.side_effect = [
                {
                    "message_id": "msg-1",
                    "is_duplicate": False,
                    "encounter_id": "enc-123",
                    "encounter_created": True,
                    "patient_id": "pat-123",
                    "error": None,
                },
                {
                    "message_id": "msg-2",
                    "is_duplicate": False,
                    "encounter_id": "enc-123",
                    "encounter_created": False,  # Same encounter, updated
                    "patient_id": "pat-123",
                    "error": None,
                },
            ]

            files = {"files": ("batch.hl7", SAMPLE_BATCH, "text/plain")}
            response = coder_client.post("/api/v1/encounters/upload", files=files)

            assert response.status_code == 200
            data = response.json()
            assert data["files_received"] == 1
            assert data["messages_found"] == 2
            assert data["messages_processed"] == 2
            assert data["encounters_created"] == 1
            assert data["encounters_updated"] == 1

    def test_upload_handles_duplicate_messages(self, coder_client):
        """Test that duplicate messages are handled gracefully."""
        with patch("app.domains.encounters.router.EncountersService") as MockService:
            mock_service = MockService.return_value
            mock_service.process_hl7_message.return_value = {
                "message_id": "msg-123",
                "is_duplicate": True,  # Message already exists
                "encounter_id": None,
                "encounter_created": False,
                "patient_id": None,
                "error": None,
            }

            files = {"files": ("test.hl7", SAMPLE_ADT_A01, "text/plain")}
            response = coder_client.post("/api/v1/encounters/upload", files=files)

            assert response.status_code == 200
            data = response.json()
            assert data["messages_processed"] == 1  # Counted as processed
            assert data["encounters_created"] == 0

    def test_upload_handles_processing_errors(self, coder_client):
        """Test that processing errors are captured in the response."""
        with patch("app.domains.encounters.router.EncountersService") as MockService:
            mock_service = MockService.return_value
            mock_service.process_hl7_message.return_value = {
                "message_id": "msg-123",
                "is_duplicate": False,
                "encounter_id": None,
                "encounter_created": False,
                "patient_id": None,
                "error": "Missing patient data",
            }

            files = {"files": ("test.hl7", SAMPLE_ADT_A01, "text/plain")}
            response = coder_client.post("/api/v1/encounters/upload", files=files)

            assert response.status_code == 200
            data = response.json()
            assert data["messages_failed"] == 1
            assert len(data["errors"]) == 1
            assert "Missing patient data" in data["errors"][0]

    def test_admin_can_upload(self, admin_client):
        """Test that admin role can also upload files."""
        with patch("app.domains.encounters.router.EncountersService") as MockService:
            mock_service = MockService.return_value
            mock_service.process_hl7_message.return_value = {
                "message_id": "msg-123",
                "is_duplicate": False,
                "encounter_id": "enc-123",
                "encounter_created": True,
                "patient_id": "pat-123",
                "error": None,
            }

            files = {"files": ("test.hl7", SAMPLE_ADT_A01, "text/plain")}
            response = admin_client.post("/api/v1/encounters/upload", files=files)

            assert response.status_code == 200
