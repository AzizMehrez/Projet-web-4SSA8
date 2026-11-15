from datetime import datetime, timezone
from uuid import UUID
from typing import Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


class PermanentEventError(Exception):
    """Unrecoverable error (e.g. malformed payload, missing UUID). Should route to DLQ."""
    pass


class TemporaryEventError(Exception):
    """Temporary recoverable error (e.g. SMTP server timeout). Should trigger retry."""
    pass


class BaseEvent(BaseModel):
    """Base event contract containing unique eventId and timestamp."""
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    eventId: UUID = Field(..., description="Unique UUID for event identification and idempotency")
    occurredAt: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when event occurred"
    )

    @field_validator("eventId", mode="before")
    @classmethod
    def validate_uuid(cls, value: Any) -> UUID:
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid UUID for eventId: {value}") from exc
