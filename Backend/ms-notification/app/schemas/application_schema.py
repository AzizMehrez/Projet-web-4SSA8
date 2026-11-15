from typing import Optional, Union
from pydantic import EmailStr, Field
from app.schemas.event_schema import BaseEvent


class ApplicationCreatedEvent(BaseEvent):
    """
    Event: ApplicationCreated
    Producer: ms-application
    Official contract: { "eventId", "applicationId", "candidateId", "jobId", "email", "occurredAt" }
    """
    applicationId: Union[int, str] = Field(..., description="Application ID")
    candidateId: Union[int, str] = Field(..., description="Candidate ID")
    jobId: Union[int, str] = Field(..., description="Job ID")
    email: EmailStr = Field(..., description="Candidate email address")
    candidateName: Optional[str] = Field(default=None, description="Optional candidate full name")
    jobTitle: Optional[str] = Field(default=None, description="Optional job title")


class ApplicationStatusChangedEvent(BaseEvent):
    """
    Event: ApplicationStatusChanged
    Producer: ms-application
    Official contract: { "eventId", "applicationId", "fromStatus", "toStatus", "occurredAt" }
    """
    applicationId: Union[int, str] = Field(..., description="Application ID")
    fromStatus: str = Field(..., description="Previous application status")
    toStatus: str = Field(..., description="New application status")
    email: Optional[EmailStr] = Field(default=None, description="Candidate email address if known")
    candidateName: Optional[str] = Field(default=None, description="Optional candidate name")
    jobTitle: Optional[str] = Field(default=None, description="Optional job title")

