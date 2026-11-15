from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class NotificationRecord:
    """Internal model for local notification audit history."""
    id: Optional[int] = None
    event_id: str = ""
    channel: str = "EMAIL"
    recipient: str = ""
    subject: str = ""
    status: str = "SENT"  # SENT, FAILED, SIMULATED
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    template_name: Optional[str] = None
    payload: Optional[Dict[str, Any]] = field(default_factory=dict)

