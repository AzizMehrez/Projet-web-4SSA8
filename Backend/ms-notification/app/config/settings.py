import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # Application
    APP_NAME: str = "ms-notification"
    APP_ENV: str = "development"
    APP_PORT: int = 8085
    APP_HOST: str = "0.0.0.0"
    DEBUG: bool = False
    ALLOW_TEST_ENDPOINTS: bool = True

    # RabbitMQ
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"
    RABBITMQ_EXCHANGE: str = "jobboard.exchange"
    RABBITMQ_EXCHANGE_TYPE: str = "topic"
    RABBITMQ_DLX_EXCHANGE: str = "jobboard.dlx"
    RABBITMQ_DLQ_NAME: str = "notification.dlq"
    RABBITMQ_CONSUMER_ENABLED: bool = True
    RABBITMQ_PREFETCH_COUNT: int = 10
    RABBITMQ_MAX_RETRIES: int = 3
    RABBITMQ_RETRY_BACKOFF_SECONDS: int = 5

    # Queues & Routing Keys
    QUEUE_APPLICATION_CREATED: str = "notification.application.created"
    ROUTING_KEY_APPLICATION_CREATED: str = "application.created"

    QUEUE_APPLICATION_STATUS_CHANGED: str = "notification.application.status_changed"
    ROUTING_KEY_APPLICATION_STATUS_CHANGED: str = "application.status.changed"

    QUEUE_INTERVIEW_SCHEDULED: str = "notification.interview.scheduled"
    ROUTING_KEY_INTERVIEW_SCHEDULED: str = "interview.scheduled"

    QUEUE_INTERVIEW_CANCELLED: str = "notification.interview.cancelled"
    ROUTING_KEY_INTERVIEW_CANCELLED: str = "interview.cancelled"

    QUEUE_JOB_AVAILABILITY: str = "notification.job.availability_changed"
    ROUTING_KEY_JOB_AVAILABILITY: str = "job.availability.changed"

    # SMTP Configuration
    SMTP_ENABLED: bool = False
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "no-reply@talentconnect.esprit.tn"
    SMTP_FROM_NAME: str = "TalentConnect Notification"
    SMTP_USE_TLS: bool = False
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT: int = 10

    # Local Storage for Idempotency & Audit Logs
    DATABASE_PATH: str = "data/notifications.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in ("production", "prod")

    @property
    def rabbitmq_url(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:******@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{self.RABBITMQ_VHOST}"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()

