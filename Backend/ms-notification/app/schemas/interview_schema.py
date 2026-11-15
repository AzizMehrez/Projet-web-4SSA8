from typing import Optional, Union
from pydantic import EmailStr, Field
from app.schemas.event_schema import BaseEvent


class InterviewScheduledEvent(BaseEvent):
    """
    Event: InterviewScheduled
    Producer: ms-interview
    Official contract: { "eventId", "interviewId", "applicationId", "slot", "meetingUrl", "occurredAt" }
    """
    interviewId: Union[int, str] = Field(..., description="Interview ID")
    applicationId: Union[int, str] = Field(..., description="Associated Application ID")
    slot: str = Field(..., description="Interview slot / date & time")
    meetingUrl: Optional[str] = Field(default=None, description="Virtual meeting link (e.g. Teams, Meet, Zoom)")
    email: Optional[EmailStr] = Field(default=None, description="Candidate email address")
    candidateName: Optional[str] = Field(default=None, description="Optional candidate name")
    jobTitle: Optional[str] = Field(default=None, description="Optional job title")
    notes: Optional[str] = Field(default=None, description="Additional interview instructions")


class InterviewCancelledEvent(BaseEvent):
    """
    Event: InterviewCancelled
    Producer: ms-interview
    Official contract: { "eventId", "interviewId", "applicationId", "reason", "occurredAt" }
    """
    interviewId: Union[int, str] = Field(..., description="Interview ID")
    applicationId: Union[int, str] = Field(..., description="Associated Application ID")
    reason: Optional[str] = Field(default="Annulé par le recruteur", description="Reason for cancellation")
    email: Optional[EmailStr] = Field(default=None, description="Candidate email address")
    candidateName: Optional[str] = Field(default=None, description="Optional candidate name")

