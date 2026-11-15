import smtplib
from unittest.mock import MagicMock, patch
import pytest

from app.config.settings import Settings
from app.schemas.event_schema import PermanentEventError, TemporaryEventError
from app.services.email_service import EmailService
from app.services.template_service import TemplateService


def test_template_rendering_all_templates():
    """Verify all 4 HTML templates render valid HTML without Jinja errors."""
    ts = TemplateService()

    # 1. application_created
    html1 = ts.render("application_created.html", {
        "applicationId": 123,
        "candidateId": 456,
        "jobId": 789,
        "candidateName": "Ali Ben Ali",
        "jobTitle": "Lead Python Developer",
        "occurredAt": "15/11/2026 à 10:00",
    })
    assert "Ali Ben Ali" in html1
    assert "Confirmation de votre candidature #123" in html1
    assert "Lead Python Developer" in html1

    # 2. application_status_changed
    html2 = ts.render("application_status_changed.html", {
        "applicationId": 123,
        "candidateName": "Ali",
        "fromStatus": "SUBMITTED",
        "toStatus": "ACCEPTED",
        "occurredAt": "15/11/2026 à 11:00",
    })
    assert "SUBMITTED" in html2
    assert "ACCEPTED" in html2

    # 3. interview_scheduled
    html3 = ts.render("interview_scheduled.html", {
        "interviewId": 999,
        "applicationId": 123,
        "slot": "25 Novembre 2026 à 15:00",
        "meetingUrl": "https://meet.google.com/test",
        "candidateName": "Ali",
        "occurredAt": "15/11/2026 à 12:00",
    })
    assert "999" in html3
    assert "https://meet.google.com/test" in html3

    # 4. interview_cancelled
    html4 = ts.render("interview_cancelled.html", {
        "interviewId": 999,
        "applicationId": 123,
        "reason": "Poste pourvu en interne",
        "candidateName": "Ali",
        "occurredAt": "15/11/2026 à 13:00",
    })
    assert "Poste pourvu en interne" in html4


def test_html_to_plain_text():
    """Verify HTML stripping generates readable plain text."""
    ts = TemplateService()
    html = "<h1>Title</h1><p>First line.<br>Second line.</p>"
    plain = ts.html_to_plain_text(html)
    assert "Title" in plain
    assert "First line." in plain
    assert "Second line." in plain
    assert "<" not in plain


def test_email_simulation_mode():
    """EmailService in simulation mode (SMTP_ENABLED=False) logs and returns True."""
    settings = Settings(SMTP_ENABLED=False)
    service = EmailService(settings=settings)
    result = service.send_email(
        to_email="test@talentconnect.tn",
        subject="Test Subject",
        html_body="<p>Test Body</p>",
    )
    assert result is True


def test_email_invalid_recipient_raises_permanent_error():
    """Missing or invalid recipient address must raise PermanentEventError."""
    service = EmailService()
    with pytest.raises(PermanentEventError):
        service.send_email(to_email="", subject="Subj", html_body="<p>Body</p>")
    with pytest.raises(PermanentEventError):
        service.send_email(to_email="invalid_address_at_none", subject="Subj", html_body="<p>Body</p>")


@patch("smtplib.SMTP")
def test_email_real_smtp_success(mock_smtp_cls):
    """Test successful email transmission over live SMTP."""
    mock_server = MagicMock()
    mock_smtp_cls.return_value.__enter__.return_value = mock_server

    settings = Settings(
        SMTP_ENABLED=True,
        SMTP_HOST="smtp.example.com",
        SMTP_PORT=587,
        SMTP_USER="user@example.com",
        SMTP_PASSWORD="secretpassword",
        SMTP_USE_TLS=True,
    )
    service = EmailService(settings=settings)
    result = service.send_email(
        to_email="valid.candidate@esprit.tn",
        subject="Test Live Subject",
        html_body="<p>Hello live</p>",
    )
    assert result is True
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("user@example.com", "secretpassword")
    mock_server.send_message.assert_called_once()


@patch("smtplib.SMTP")
def test_email_smtp_auth_error_raises_permanent_error(mock_smtp_cls):
    """SMTP authentication error is permanent (should route to DLQ)."""
    mock_server = MagicMock()
    mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")
    mock_smtp_cls.return_value.__enter__.return_value = mock_server

    settings = Settings(
        SMTP_ENABLED=True,
        SMTP_HOST="smtp.example.com",
        SMTP_USER="wrong_user",
        SMTP_PASSWORD="bad_password",
    )
    service = EmailService(settings=settings)
    with pytest.raises(PermanentEventError):
        service.send_email(
            to_email="candidate@esprit.tn",
            subject="Subj",
            html_body="<p>Body</p>",
        )


@patch("smtplib.SMTP")
def test_email_smtp_timeout_raises_temporary_error(mock_smtp_cls):
    """SMTP connection timeout is transient and must raise TemporaryEventError for retry."""
    mock_smtp_cls.side_effect = TimeoutError("Connection timed out")

    settings = Settings(SMTP_ENABLED=True, SMTP_HOST="smtp.example.com")
    service = EmailService(settings=settings)
    with pytest.raises(TemporaryEventError):
        service.send_email(
            to_email="candidate@esprit.tn",
            subject="Subj",
            html_body="<p>Body</p>",
        )

