from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, EmailStr

from app.config.settings import get_settings
from app.services.notification_service import get_notification_service

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


class TestNotificationRequest(BaseModel):
    """Payload for manual test notification endpoint."""
    to_email: EmailStr
    template_name: str = "application_created.html"
    custom_data: Optional[Dict[str, Any]] = None


@router.get("/ping", summary="Ping endpoint for service discovery and proxy check")
def ping():
    """Simple ping endpoint preserving skeleton compatibility."""
    return {"status": "ok", "service": "notification"}


@router.get("", summary="Get recent notification audit logs")
def list_notifications(limit: int = Query(default=50, ge=1, le=200)):
    """Retrieve audit history of processed notifications."""
    service = get_notification_service()
    logs = service.get_history(limit=limit)
    return {
        "count": len(logs),
        "limit": limit,
        "notifications": logs,
    }


@router.post("/test", summary="Trigger a safe test notification")
def trigger_test_notification(payload: TestNotificationRequest):
    """
    Test email rendering and delivery.
    Disabled in production unless ALLOW_TEST_ENDPOINTS is enabled.
    """
    settings = get_settings()
    if settings.is_production and not settings.ALLOW_TEST_ENDPOINTS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test notification endpoint is disabled in production.",
        )

    service = get_notification_service()
    try:
        result = service.send_test_notification(
            to_email=str(payload.to_email),
            template_name=payload.template_name,
            custom_data=payload.custom_data,
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test notification: {exc}",
        )

