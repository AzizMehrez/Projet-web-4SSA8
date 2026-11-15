import json
from uuid import uuid4
import pytest
from app.schemas.event_schema import PermanentEventError


def test_process_application_created(event_processor, test_repo):
    """Test ApplicationCreated event triggers email and stores in repo."""
    event_id = str(uuid4())
    payload = {
        "eventId": event_id,
        "applicationId": 101,
        "candidateId": 202,
        "jobId": 303,
        "email": "dhia.jbali@esprit.tn",
        "candidateName": "Dhia Jbali",
        "jobTitle": "DevOps Engineer",
        "occurredAt": "2026-11-15T10:00:00Z",
    }
    success, message = event_processor.process_event(
        raw_body=payload,
        routing_key="application.created"
    )
    assert success is True
    assert test_repo.is_event_processed(event_id) is True

    logs = test_repo.get_recent_logs(limit=1)
    assert len(logs) == 1
    assert logs[0]["recipient"] == "dhia.jbali@esprit.tn"
    assert "Confirmation" in logs[0]["subject"]
    assert logs[0]["template_name"] == "application_created.html"


def test_process_application_status_changed(event_processor, test_repo):
    """Test ApplicationStatusChanged event sends email and records log."""
    event_id = str(uuid4())
    payload = {
        "eventId": event_id,
        "applicationId": 101,
        "fromStatus": "SUBMITTED",
        "toStatus": "SHORTLISTED",
        "email": "candidate@talentconnect.tn",
        "candidateName": "Amine",
        "occurredAt": "2026-11-15T11:00:00Z",
    }
    success, message = event_processor.process_event(
        raw_body=payload,
        routing_key="application.status.changed"
    )
    assert success is True
    assert test_repo.is_event_processed(event_id) is True

    logs = test_repo.get_recent_logs(limit=1)
    assert len(logs) == 1
    assert logs[0]["recipient"] == "candidate@talentconnect.tn"
    assert "Mise à jour" in logs[0]["subject"]


def test_process_interview_scheduled(event_processor, test_repo):
    """Test InterviewScheduled event sends invitation email with slot and URL."""
    event_id = str(uuid4())
    payload = {
        "eventId": event_id,
        "interviewId": 505,
        "applicationId": 101,
        "slot": "2026-11-20 14:00",
        "meetingUrl": "https://meet.google.com/xyz-abc-123",
        "email": "candidate.interview@esprit.tn",
        "candidateName": "Sarah",
        "notes": "Présenter votre portfolio GitHub.",
        "occurredAt": "2026-11-15T12:00:00Z",
    }
    success, message = event_processor.process_event(
        raw_body=payload,
        routing_key="interview.scheduled"
    )
    assert success is True
    assert test_repo.is_event_processed(event_id) is True

    logs = test_repo.get_recent_logs(limit=1)
    assert len(logs) == 1
    assert "Convocation" in logs[0]["subject"]
    assert logs[0]["template_name"] == "interview_scheduled.html"


def test_process_interview_cancelled(event_processor, test_repo):
    """Test InterviewCancelled event sends cancellation notice."""
    event_id = str(uuid4())
    payload = {
        "eventId": event_id,
        "interviewId": 505,
        "applicationId": 101,
        "reason": "Recruteur indisponible",
        "email": "candidate.interview@esprit.tn",
        "candidateName": "Sarah",
        "occurredAt": "2026-11-15T13:00:00Z",
    }
    success, message = event_processor.process_event(
        raw_body=payload,
        routing_key="interview.cancelled"
    )
    assert success is True
    assert test_repo.is_event_processed(event_id) is True

    logs = test_repo.get_recent_logs(limit=1)
    assert len(logs) == 1
    assert "Annulation" in logs[0]["subject"]


def test_process_job_availability_changed(event_processor, test_repo):
    """Test JobAvailabilityChanged does not spam candidate but logs audit record."""
    event_id = str(uuid4())
    payload = {
        "eventId": event_id,
        "jobId": 303,
        "available": False,
        "occurredAt": "2026-11-15T14:00:00Z",
    }
    success, message = event_processor.process_event(
        raw_body=payload,
        routing_key="job.availability.changed"
    )
    assert success is True
    assert test_repo.is_event_processed(event_id) is True

    logs = test_repo.get_recent_logs(limit=1)
    assert len(logs) == 1
    assert logs[0]["channel"] == "SYSTEM_AUDIT"
    assert logs[0]["status"] == "ACKNOWLEDGED"


def test_missing_event_id_raises_permanent_error(event_processor):
    """Event missing eventId must raise PermanentEventError to route to DLQ."""
    payload = {
        "applicationId": 101,
        "candidateId": 202,
        "jobId": 303,
        "email": "test@esprit.tn",
    }
    with pytest.raises(PermanentEventError):
        event_processor.process_event(payload, routing_key="application.created")


def test_invalid_uuid_raises_permanent_error(event_processor):
    """Event with non-UUID eventId must raise PermanentEventError."""
    payload = {
        "eventId": "not-a-valid-uuid-string",
        "applicationId": 101,
    }
    with pytest.raises(PermanentEventError):
        event_processor.process_event(payload, routing_key="application.created")


def test_corrupted_json_bytes_raises_permanent_error(event_processor):
    """Corrupted bytes payload must raise PermanentEventError."""
    bad_bytes = b'{"eventId": "malformed json without closing brace'
    with pytest.raises(PermanentEventError):
        event_processor.process_event(bad_bytes, routing_key="application.created")


def test_invalid_schema_raises_permanent_error(event_processor):
    """Missing required business fields (e.g. invalid email) must route to DLQ."""
    event_id = str(uuid4())
    payload = {
        "eventId": event_id,
        "applicationId": 101,
        "candidateId": 202,
        "jobId": 303,
        "email": "invalid-email-format-without-at",
    }
    with pytest.raises(PermanentEventError):
        event_processor.process_event(payload, routing_key="application.created")

