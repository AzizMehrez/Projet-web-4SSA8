import concurrent.futures
from uuid import uuid4
from unittest.mock import MagicMock

from app.repositories.event_repository import EventRepository


def test_duplicate_event_prevention(event_processor, test_repo):
    """
    Ensure the same eventId is never processed twice.
    The second call must return skipped and never dispatch an email.
    """
    event_id = str(uuid4())
    payload = {
        "eventId": event_id,
        "applicationId": 555,
        "candidateId": 444,
        "jobId": 333,
        "email": "idempotency.test@esprit.tn",
        "occurredAt": "2026-11-15T12:00:00Z",
    }

    # First delivery
    success1, msg1 = event_processor.process_event(payload, routing_key="application.created")
    assert success1 is True
    assert "successfully" in msg1

    # Verify 1 record in repository
    assert test_repo.is_event_processed(event_id) is True
    logs1 = test_repo.get_recent_logs(limit=10)
    assert len(logs1) == 1

    # Mock email service to verify it is NOT called on duplicate
    event_processor.email_service.send_email = MagicMock()

    # Second delivery with same eventId (duplicate event)
    success2, msg2 = event_processor.process_event(payload, routing_key="application.created")
    assert success2 is True
    assert "Duplicate event" in msg2

    # Verify email was NOT sent a second time
    event_processor.email_service.send_email.assert_not_called()

    # Still only 1 log entry in repository
    logs2 = test_repo.get_recent_logs(limit=10)
    assert len(logs2) == 1


def test_idempotency_survives_restart(temp_db_path, email_service, template_service, test_settings):
    """
    Verify processed event IDs survive service restarts.
    We simulate this by closing repository and opening a new one on the same DB.
    """
    event_id = str(uuid4())

    # Step 1: Process with repo 1
    repo1 = EventRepository(db_path=temp_db_path)
    repo1.record_event_processed(event_id=event_id, event_type="ApplicationCreated")
    assert repo1.is_event_processed(event_id) is True

    # Step 2: Simulate restart by instantiating repo 2 on same DB
    repo2 = EventRepository(db_path=temp_db_path)
    assert repo2.is_event_processed(event_id) is True


def test_concurrent_event_processing(test_repo):
    """
    Ensure thread safety under concurrent writes.
    """
    num_events = 25

    def record_task(idx):
        eid = str(uuid4())
        return test_repo.record_event_processed(eid, "TestConcurrentEvent")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(record_task, i) for i in range(num_events)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert all(results)
    assert test_repo.get_event_count() == num_events

