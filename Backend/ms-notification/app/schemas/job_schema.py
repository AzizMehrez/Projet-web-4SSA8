from typing import Optional, Union
from pydantic import Field
from app.schemas.event_schema import BaseEvent


class JobAvailabilityChangedEvent(BaseEvent):
    """
    Event: JobAvailabilityChanged
    Producer: ms-job
    Official contract: { "eventId", "jobId", "available", "occurredAt" }
    
    Note: As per V1 architectural design, this event is catalog/state awareness.
    It does not trigger outbound candidate emails unless specifically subscribed.
    """
    jobId: Union[int, str] = Field(..., description="Job ID")
    available: bool = Field(..., description="Availability status of the job posting")
    jobTitle: Optional[str] = Field(default=None, description="Optional job title")

