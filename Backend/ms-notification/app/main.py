from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.config.logging_config import setup_logging
from app.config.settings import get_settings
from app.controllers.health_controller import router as health_router
from app.controllers.notification_controller import router as notification_router
from app.messaging.rabbitmq_consumer import get_rabbitmq_consumer
from app.repositories.event_repository import get_event_repository

settings = get_settings()
setup_logging(debug=settings.DEBUG)
logger = logging.getLogger("ms-notification.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan manager:
    Initializes repository and starts background RabbitMQ consumer on startup;
    gracefully stops worker and closes connections on shutdown.
    """
    logger.info(f"Starting {settings.APP_NAME} in '{settings.APP_ENV}' mode on port {settings.APP_PORT}...")

    # Initialize local SQLite storage
    repo = get_event_repository()
    logger.info(f"Local event store initialized with {repo.get_event_count()} tracked events.")

    # Start RabbitMQ consumer thread if enabled
    consumer = None
    if settings.RABBITMQ_CONSUMER_ENABLED:
        try:
            consumer = get_rabbitmq_consumer()
            consumer.start()
            logger.info("RabbitMQ consumer initialized and running.")
        except Exception as exc:
            logger.error(f"Failed to start RabbitMQ consumer on startup: {exc}. Will retry in background.")
    else:
        logger.info("RabbitMQ consumer is disabled by configuration (RABBITMQ_CONSUMER_ENABLED=false).")

    yield

    # Graceful shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")
    if consumer and consumer.is_running():
        consumer.stop()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="ms-notification",
    description=(
        "TalentConnect Notification Microservice (AWD ESPRIT 2026-2027)\n\n"
        "Asynchronous event-driven notification service using Python FastAPI, RabbitMQ, and SMTP.\n"
        "Responsible: Dhia Jbali (Port 8085)"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Register routers
app.include_router(health_router)
app.include_router(notification_router)


@app.get("/", include_in_schema=False)
def root():
    """Redirect root path to interactive documentation."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )
