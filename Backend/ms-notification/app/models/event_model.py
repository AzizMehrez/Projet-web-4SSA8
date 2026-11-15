from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ProcessedEventRecord:
    """Internal model for an event tracked in the idempotency store."""
    event_id: str
    event_type: str
    processed_at: datetime
    status: str = "SUCCESS"  # SUCCESS, FAILED, RETRIED
    error_message: Optional[str] = None

