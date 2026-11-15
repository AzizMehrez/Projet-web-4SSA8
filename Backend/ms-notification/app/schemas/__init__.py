from app.schemas.event_schema import BaseEvent, PermanentEventError, TemporaryEventError
from app.schemas.application_schema import ApplicationCreatedEvent, ApplicationStatusChangedEvent
from app.schemas.interview_schema import InterviewScheduledEvent, InterviewCancelledEvent
from app.schemas.job_schema import JobAvailabilityChangedEvent

__all__ = [
    "BaseEvent",
    "PermanentEventError",
    "TemporaryEventError",
    "ApplicationCreatedEvent",
    "ApplicationStatusChangedEvent",
    "InterviewScheduledEvent",
    "InterviewCancelledEvent",
    "JobAvailabilityChangedEvent",
]

