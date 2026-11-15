import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config.settings import Settings, get_settings
from app.schemas.event_schema import TemporaryEventError, PermanentEventError

logger = logging.getLogger("ms-notification.email")


class EmailService:
    """
    Service responsible for constructing and delivering emails via SMTP.
    Supports TLS, SSL, timeouts, and safe test/simulation mode.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send an HTML email with optional plain-text fallback.
        Raises TemporaryEventError on transient SMTP connection issues.
        Raises PermanentEventError on invalid addresses or authentication rejects.
        """
        if not to_email or "@" not in to_email:
            raise PermanentEventError(f"Invalid recipient email address: '{to_email}'")

        # Build MIME message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.settings.SMTP_FROM_NAME} <{self.settings.SMTP_FROM_EMAIL}>"
        message["To"] = to_email

        if text_body:
            message.attach(MIMEText(text_body, "plain", "utf-8"))
        message.attach(MIMEText(html_body, "html", "utf-8"))

        # Simulation mode for testing / development without a live SMTP server
        if not self.settings.SMTP_ENABLED:
            logger.info(
                f"[SIMULATED EMAIL] To: {to_email} | Subject: '{subject}' | "
                f"From: {self.settings.SMTP_FROM_EMAIL} (SMTP_ENABLED=False)"
            )
            return True

        # Real SMTP Delivery
        try:
            logger.info(
                f"Connecting to SMTP server at {self.settings.SMTP_HOST}:{self.settings.SMTP_PORT} "
                f"(TLS={self.settings.SMTP_USE_TLS}, SSL={self.settings.SMTP_USE_SSL})..."
            )
            client_cls = smtplib.SMTP_SSL if self.settings.SMTP_USE_SSL else smtplib.SMTP

            with client_cls(
                host=self.settings.SMTP_HOST,
                port=self.settings.SMTP_PORT,
                timeout=self.settings.SMTP_TIMEOUT
            ) as server:
                server.ehlo()
                if self.settings.SMTP_USE_TLS and not self.settings.SMTP_USE_SSL:
                    server.starttls()
                    server.ehlo()

                if self.settings.SMTP_USER and self.settings.SMTP_PASSWORD:
                    server.login(self.settings.SMTP_USER, self.settings.SMTP_PASSWORD)

                server.send_message(message)
                logger.info(f"Email successfully delivered to {to_email} with subject: '{subject}'")
                return True

        except smtplib.SMTPAuthenticationError as exc:
            logger.error(f"Permanent SMTP authentication error for user {self.settings.SMTP_USER}: {exc}")
            raise PermanentEventError(f"SMTP authentication failed: {exc}") from exc

        except smtplib.SMTPRecipientsRefused as exc:
            logger.error(f"Permanent SMTP recipient refused for {to_email}: {exc}")
            raise PermanentEventError(f"Recipient refused: {exc}") from exc

        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError, OSError) as exc:
            logger.warning(f"Temporary SMTP connection failure to {self.settings.SMTP_HOST}:{self.settings.SMTP_PORT} : {exc}")
            raise TemporaryEventError(f"Transient SMTP error: {exc}") from exc

        except smtplib.SMTPException as exc:
            logger.error(f"Generic SMTP error during send to {to_email}: {exc}")
            raise TemporaryEventError(f"SMTP exception: {exc}") from exc


_global_email_service = None


def get_email_service() -> EmailService:
    """Singleton getter for EmailService."""
    global _global_email_service
    if _global_email_service is None:
        _global_email_service = EmailService()
    return _global_email_service
