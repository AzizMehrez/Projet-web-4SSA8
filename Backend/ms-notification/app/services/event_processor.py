import json
import logging
from typing import Any, Dict, Optional, Tuple, Union
from uuid import UUID

from pydantic import ValidationError

from app.config.settings import Settings, get_settings
from app.repositories.event_repository import EventRepository, get_event_repository
from app.schemas.application_schema import ApplicationCreatedEvent, ApplicationStatusChangedEvent
from app.schemas.event_schema import PermanentEventError, TemporaryEventError
from app.schemas.interview_schema import InterviewCancelledEvent, InterviewScheduledEvent
from app.schemas.job_schema import JobAvailabilityChangedEvent
from app.services.email_service import EmailService, get_email_service
from app.services.template_service import TemplateService, get_template_service

logger = logging.getLogger("ms-notification.event_processor")


class EventProcessor:
    """
    Core event processing orchestrator.
    Handles deserialization, validation, idempotency, email rendering, and delivery.
    """

    def __init__(
        self,
        repository: Optional[EventRepository] = None,
        email_service: Optional[EmailService] = None,
        template_service: Optional[TemplateService] = None,
        settings: Optional[Settings] = None,
    ):
        self.repository = repository or get_event_repository()
        self.email_service = email_service or get_email_service()
        self.template_service = template_service or get_template_service()
        self.settings = settings or get_settings()

    def process_event(
        self,
        raw_body: Union[bytes, str, dict],
        routing_key: str = "",
        headers: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """
        Process an incoming AMQP message.
        Returns (success: bool, message: str).
        Raises PermanentEventError for malformed payloads.
        Raises TemporaryEventError for transient failures.
        """
        # Step 1: Parse JSON
        if isinstance(raw_body, (bytes, bytearray)):
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except Exception as exc:
                logger.error(f"Failed to decode or parse JSON payload: {exc}")
                raise PermanentEventError(f"Invalid JSON payload: {exc}") from exc
        elif isinstance(raw_body, str):
            try:
                payload = json.loads(raw_body)
            except Exception as exc:
                logger.error(f"Failed to parse JSON string: {exc}")
                raise PermanentEventError(f"Invalid JSON string: {exc}") from exc
        elif isinstance(raw_body, dict):
            payload = raw_body
        else:
            raise PermanentEventError(f"Unsupported payload type: {type(raw_body)}")

        # Step 2: Validate eventId
        event_id_raw = payload.get("eventId")
        if not event_id_raw:
            logger.error("Rejecting event: missing required 'eventId'")
            raise PermanentEventError("Missing required 'eventId' field in event payload")

        try:
            event_uuid = UUID(str(event_id_raw))
            event_id_str = str(event_uuid)
        except (ValueError, TypeError) as exc:
            logger.error(f"Rejecting event: invalid UUID eventId '{event_id_raw}'")
            raise PermanentEventError(f"Field 'eventId' must be a valid UUID: {exc}") from exc

        # Step 3: Idempotency check
        if self.repository.is_event_processed(event_id_str):
            logger.info(
                f"[IDEMPOTENCY] Event {event_id_str} has already been processed. "
                "Skipping duplicate execution to prevent duplicate emails."
            )
            return True, f"Duplicate event {event_id_str} ignored"

        # Step 4: Determine Event Type and Process
        event_type = self._resolve_event_type(payload, routing_key)
        logger.info(f"Processing event: ID={event_id_str}, type='{event_type}', routing_key='{routing_key}'")

        try:
            if event_type in ("ApplicationCreated", "application.created"):
                self._handle_application_created(payload, event_id_str)
            elif event_type in ("ApplicationStatusChanged", "application.status.changed"):
                self._handle_application_status_changed(payload, event_id_str)
            elif event_type in ("InterviewScheduled", "interview.scheduled"):
                self._handle_interview_scheduled(payload, event_id_str)
            elif event_type in ("InterviewCancelled", "interview.cancelled"):
                self._handle_interview_cancelled(payload, event_id_str)
            elif event_type in ("JobAvailabilityChanged", "job.availability.changed"):
                self._handle_job_availability_changed(payload, event_id_str)
            else:
                logger.warning(f"Unrecognized event type '{event_type}'. No action taken.")
                self.repository.record_event_processed(event_id_str, event_type, status="SKIPPED")
                return True, f"Unrecognized event type {event_type} skipped"

            # Step 5: Mark event as successfully processed in local store
            self.repository.record_event_processed(event_id_str, event_type, status="SUCCESS")
            return True, f"Event {event_id_str} successfully processed"

        except ValidationError as exc:
            logger.error(f"Validation error for event {event_id_str} of type '{event_type}': {exc}")
            self.repository.record_event_processed(event_id_str, event_type, status="FAILED_VALIDATION")
            raise PermanentEventError(f"Schema validation failed: {exc}") from exc

        except TemporaryEventError:
            # Re-raise transient errors to let RabbitMQ consumer handle retry
            raise

        except PermanentEventError:
            self.repository.record_event_processed(event_id_str, event_type, status="FAILED_PERMANENT")
            raise

        except Exception as exc:
            logger.exception(f"Unexpected error processing event {event_id_str}: {exc}")
            raise TemporaryEventError(f"Unexpected processing error: {exc}") from exc

    def _resolve_event_type(self, payload: Dict[str, Any], routing_key: str) -> str:
        """Infer the event type from the payload or routing key."""
        if payload.get("eventType"):
            return str(payload["eventType"])
        if routing_key:
            return routing_key
        # Check payload keys signature
        if "candidateId" in payload and "jobId" in payload and "email" in payload:
            return "ApplicationCreated"
        if "fromStatus" in payload and "toStatus" in payload:
            return "ApplicationStatusChanged"
        if "slot" in payload and "meetingUrl" in payload:
            return "InterviewScheduled"
        if "reason" in payload and "interviewId" in payload:
            return "InterviewCancelled"
        if "jobId" in payload and "available" in payload:
            return "JobAvailabilityChanged"
        return "UnknownEvent"

    def _handle_application_created(self, payload: Dict[str, Any], event_id: str) -> None:
        """Process ApplicationCreated: Send confirmation email to candidate."""
        event = ApplicationCreatedEvent(**payload)
        context = {
            "applicationId": event.applicationId,
            "candidateId": event.candidateId,
            "jobId": event.jobId,
            "candidateName": event.candidateName or "Candidat",
            "jobTitle": event.jobTitle or f"Offre #{event.jobId}",
            "occurredAt": event.occurredAt.strftime("%d/%m/%Y à %H:%M"),
        }
        subject = f"Confirmation de votre candidature #{event.applicationId} — TalentConnect"
        html_body = self.template_service.render("application_created.html", context)
        text_body = self.template_service.html_to_plain_text(html_body)

        try:
            self.email_service.send_email(
                to_email=event.email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            self.repository.record_notification_log(
                event_id=event_id,
                channel="EMAIL",
                recipient=event.email,
                subject=subject,
                status="SENT" if self.settings.SMTP_ENABLED else "SIMULATED",
                template_name="application_created.html",
                payload=payload,
            )
        except Exception as exc:
            self.repository.record_notification_log(
                event_id=event_id,
                channel="EMAIL",
                recipient=event.email,
                subject=subject,
                status="FAILED",
                template_name="application_created.html",
                error_message=str(exc),
                payload=payload,
            )
            raise

    def _handle_application_status_changed(self, payload: Dict[str, Any], event_id: str) -> None:
        """Process ApplicationStatusChanged: Send status update email to candidate."""
        event = ApplicationStatusChangedEvent(**payload)
        to_email = event.email or "candidate@talentconnect.esprit.tn"

        context = {
            "applicationId": event.applicationId,
            "fromStatus": event.fromStatus,
            "toStatus": event.toStatus,
            "candidateName": event.candidateName or "Candidat",
            "jobTitle": event.jobTitle,
            "occurredAt": event.occurredAt.strftime("%d/%m/%Y à %H:%M"),
        }
        subject = f"Mise à jour du statut de votre candidature #{event.applicationId} — TalentConnect"
        html_body = self.template_service.render("application_status_changed.html", context)
        text_body = self.template_service.html_to_plain_text(html_body)

        try:
            self.email_service.send_email(
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            self.repository.record_notification_log(
                event_id=event_id,
                channel="EMAIL",
                recipient=to_email,
                subject=subject,
                status="SENT" if self.settings.SMTP_ENABLED else "SIMULATED",
                template_name="application_status_changed.html",
                payload=payload,
            )
        except Exception as exc:
            self.repository.record_notification_log(
                event_id=event_id,
                channel="EMAIL",
                recipient=to_email,
                subject=subject,
                status="FAILED",
                template_name="application_status_changed.html",
                error_message=str(exc),
                payload=payload,
            )
            raise

    def _handle_interview_scheduled(self, payload: Dict[str, Any], event_id: str) -> None:
        """Process InterviewScheduled: Send interview invitation with slot and meeting URL."""
        event = InterviewScheduledEvent(**payload)
        to_email = event.email or "candidate@talentconnect.esprit.tn"

        context = {
            "interviewId": event.interviewId,
            "applicationId": event.applicationId,
            "slot": event.slot,
            "meetingUrl": event.meetingUrl,
            "candidateName": event.candidateName or "Candidat",
            "jobTitle": event.jobTitle,
            "notes": event.notes,
            "occurredAt": event.occurredAt.strftime("%d/%m/%Y à %H:%M"),
        }
        subject = f"Convocation à un entretien — Candidature #{event.applicationId}"
        html_body = self.template_service.render("interview_scheduled.html", context)
        text_body = self.template_service.html_to_plain_text(html_body)

        try:
            self.email_service.send_email(
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            self.repository.record_notification_log(
                event_id=event_id,
                channel="EMAIL",
                recipient=to_email,
                subject=subject,
                status="SENT" if self.settings.SMTP_ENABLED else "SIMULATED",
                template_name="interview_scheduled.html",
                payload=payload,
            )
        except Exception as exc:
            self.repository.record_notification_log(
                event_id=event_id,
                channel="EMAIL",
                recipient=to_email,
                subject=subject,
                status="FAILED",
                template_name="interview_scheduled.html",
                error_message=str(exc),
                payload=payload,
            )
            raise

    def _handle_interview_cancelled(self, payload: Dict[str, Any], event_id: str) -> None:
        """Process InterviewCancelled: Send interview cancellation notification."""
        event = InterviewCancelledEvent(**payload)
        to_email = event.email or "candidate@talentconnect.esprit.tn"

        context = {
            "interviewId": event.interviewId,
            "applicationId": event.applicationId,
            "reason": event.reason or "Annulé par le recruteur",
            "candidateName": event.candidateName or "Candidat",
            "occurredAt": event.occurredAt.strftime("%d/%m/%Y à %H:%M"),
        }
        subject = f"Annulation de votre entretien #{event.interviewId} — TalentConnect"
        html_body = self.template_service.render("interview_cancelled.html", context)
        text_body = self.template_service.html_to_plain_text(html_body)

        try:
            self.email_service.send_email(
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            self.repository.record_notification_log(
                event_id=event_id,
                channel="EMAIL",
                recipient=to_email,
                subject=subject,
                status="SENT" if self.settings.SMTP_ENABLED else "SIMULATED",
                template_name="interview_cancelled.html",
                payload=payload,
            )
        except Exception as exc:
            self.repository.record_notification_log(
                event_id=event_id,
                channel="EMAIL",
                recipient=to_email,
                subject=subject,
                status="FAILED",
                template_name="interview_cancelled.html",
                error_message=str(exc),
                payload=payload,
            )
            raise

    def _handle_job_availability_changed(self, payload: Dict[str, Any], event_id: str) -> None:
        """
        Process JobAvailabilityChanged:
        Official V1 specification states this event decouples consumers (ms-application / ms-notification)
        for state changes. It does not spam candidate inboxes. We record it safely in our local audit log.
        """
        event = JobAvailabilityChangedEvent(**payload)
        logger.info(
            f"Acknowledged JobAvailabilityChanged for jobId={event.jobId}: "
            f"available={event.available}. Storing state awareness log."
        )
        self.repository.record_notification_log(
            event_id=event_id,
            channel="SYSTEM_AUDIT",
            recipient="system@talentconnect.local",
            subject=f"Job {event.jobId} availability changed: {event.available}",
            status="ACKNOWLEDGED",
            template_name=None,
            payload=payload,
        )


_global_event_processor = None


def get_event_processor() -> EventProcessor:
    """Singleton getter for EventProcessor."""
    global _global_event_processor
    if _global_event_processor is None:
        _global_event_processor = EventProcessor()
    return _global_event_processor

