import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.config.settings import Settings, get_settings
from app.repositories.event_repository import EventRepository, get_event_repository
from app.services.email_service import EmailService, get_email_service
from app.services.event_processor import EventProcessor, get_event_processor
from app.services.template_service import TemplateService, get_template_service

logger = logging.getLogger("ms-notification.service")


class NotificationService:
    """High-level facade for notification management and manual triggers."""

    def __init__(
        self,
        repository: Optional[EventRepository] = None,
        email_service: Optional[EmailService] = None,
        template_service: Optional[TemplateService] = None,
        event_processor: Optional[EventProcessor] = None,
        settings: Optional[Settings] = None,
    ):
        self.repository = repository or get_event_repository()
        self.email_service = email_service or get_email_service()
        self.template_service = template_service or get_template_service()
        self.event_processor = event_processor or get_event_processor()
        self.settings = settings or get_settings()

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent notification delivery logs."""
        return self.repository.get_recent_logs(limit=limit)

    def send_test_notification(
        self,
        to_email: str,
        template_name: str = "application_created.html",
        custom_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send a test notification using a chosen template.
        Protected for non-production environments.
        """
        test_event_id = str(uuid4())
        context = {
            "applicationId": 9999,
            "candidateId": 8888,
            "jobId": 7777,
            "candidateName": "Candidat Test",
            "jobTitle": "Ingénieur Logiciel Full-Stack",
            "occurredAt": "Aujourd'hui à 12:00",
            "fromStatus": "EN_ATTENTE",
            "toStatus": "ACCEPTEE",
            "interviewId": 1234,
            "slot": "Lundi 20 Novembre 2026 à 14:30",
            "meetingUrl": "https://meet.google.com/test-awd-talentconnect",
            "reason": "Test de notification système",
        }
        if custom_data:
            context.update(custom_data)

        rendered_html = self.template_service.render(template_name, context)
        text_body = self.template_service.html_to_plain_text(rendered_html)
        subject = f"[TEST] Notification TalentConnect — {template_name}"

        self.email_service.send_email(
            to_email=to_email,
            subject=subject,
            html_body=rendered_html,
            text_body=text_body,
        )

        log_id = self.repository.record_notification_log(
            event_id=test_event_id,
            channel="EMAIL_TEST",
            recipient=to_email,
            subject=subject,
            status="SENT" if self.settings.SMTP_ENABLED else "SIMULATED",
            template_name=template_name,
            payload=context,
        )

        return {
            "status": "success",
            "test_event_id": test_event_id,
            "log_id": log_id,
            "recipient": to_email,
            "template": template_name,
            "mode": "SMTP" if self.settings.SMTP_ENABLED else "SIMULATED",
        }


_global_notification_service = None


def get_notification_service() -> NotificationService:
    """Singleton getter for NotificationService."""
    global _global_notification_service
    if _global_notification_service is None:
        _global_notification_service = NotificationService()
    return _global_notification_service

