import os
from fastapi import APIRouter, Response, status
from app.config.settings import get_settings
from app.messaging.rabbitmq_connection import get_connection_manager
from app.repositories.event_repository import get_event_repository

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Basic service liveness check")
def liveness():
    """Liveness probe: returns UP if the process is running."""
    settings = get_settings()
    return {
        "status": "UP",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


@router.get("/health/ready", summary="Readiness probe with dependency check")
def readiness(response: Response):
    """
    Readiness probe: validates local storage and RabbitMQ broker connectivity.
    Returns HTTP 200 if healthy, or 503 if a critical dependency is down.
    """
    settings = get_settings()
    repo = get_event_repository()
    rabbit_mgr = get_connection_manager()

    # Check local SQLite storage
    db_ok = False
    try:
        repo.get_event_count()
        db_ok = True
    except Exception:
        db_ok = False

    # Check RabbitMQ connection
    rabbit_ok = False
    try:
        rabbit_ok = rabbit_mgr.is_connected()
    except Exception:
        rabbit_ok = False

    # If RabbitMQ consumer is explicitly disabled in config, treat RabbitMQ as optional
    overall_up = db_ok and (rabbit_ok or not settings.RABBITMQ_CONSUMER_ENABLED)

    if not overall_up:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "UP" if overall_up else "DEGRADED",
        "service": settings.APP_NAME,
        "dependencies": {
            "database": "UP" if db_ok else "DOWN",
            "rabbitmq": "UP" if rabbit_ok else ("DISABLED" if not settings.RABBITMQ_CONSUMER_ENABLED else "DOWN"),
        },
    }


@router.get("/actuator/health", summary="Spring Actuator compatible health check")
def actuator_health():
    """Endpoint mapped by API Gateway and Eureka for Spring Cloud compatibility."""
    settings = get_settings()
    return {
        "status": "UP",
        "service": settings.APP_NAME,
    }

