import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from app.config.settings import Settings, get_settings
from app.repositories.event_repository import EventRepository
from app.services.email_service import EmailService
from app.services.event_processor import EventProcessor
from app.services.template_service import TemplateService
from app.services.notification_service import NotificationService


@pytest.fixture
def temp_db_path():
    """Create a temporary SQLite database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


@pytest.fixture
def test_settings(temp_db_path):
    """Provides test-specific settings."""
    return Settings(
        APP_NAME="ms-notification-test",
        APP_ENV="test",
        DATABASE_PATH=temp_db_path,
        SMTP_ENABLED=False,
        RABBITMQ_CONSUMER_ENABLED=False,
        ALLOW_TEST_ENDPOINTS=True,
    )


@pytest.fixture
def test_repo(temp_db_path):
    """Isolated EventRepository instance using temp database."""
    return EventRepository(db_path=temp_db_path)


@pytest.fixture
def template_service():
    """TemplateService instance."""
    return TemplateService()


@pytest.fixture
def email_service(test_settings):
    """EmailService in simulation mode."""
    return EmailService(settings=test_settings)


@pytest.fixture
def event_processor(test_repo, email_service, template_service, test_settings):
    """EventProcessor with injected test dependencies."""
    return EventProcessor(
        repository=test_repo,
        email_service=email_service,
        template_service=template_service,
        settings=test_settings,
    )


@pytest.fixture
def client(test_settings, test_repo):
    """FastAPI TestClient with overridden dependencies."""
    from app.main import app
    from app.repositories import event_repository

    # Override repository singleton during test
    event_repository._global_repository = test_repo

    with TestClient(app) as test_client:
        yield test_client

