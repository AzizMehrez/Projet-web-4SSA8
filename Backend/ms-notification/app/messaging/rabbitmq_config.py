from dataclasses import dataclass, field
from typing import Dict, List
from app.config.settings import Settings, get_settings


@dataclass
class QueueDefinition:
    """Represents a RabbitMQ queue and its routing key bindings."""
    name: str
    routing_keys: List[str]
    durable: bool = True
    exclusive: bool = False
    auto_delete: bool = False
    arguments: Dict[str, str] = field(default_factory=dict)


class RabbitMQTopology:
    """Defines exchanges, queues, DLX, and bindings for ms-notification."""

    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()

    @property
    def exchange_name(self) -> str:
        return self.settings.RABBITMQ_EXCHANGE

    @property
    def exchange_type(self) -> str:
        return self.settings.RABBITMQ_EXCHANGE_TYPE

    @property
    def dlx_exchange_name(self) -> str:
        return self.settings.RABBITMQ_DLX_EXCHANGE

    @property
    def dlq_name(self) -> str:
        return self.settings.RABBITMQ_DLQ_NAME

    def get_queues(self) -> List[QueueDefinition]:
        """
        Returns all queues ms-notification listens to.
        Each queue is configured with a dead-letter exchange (DLX).
        """
        dlx_args = {
            "x-dead-letter-exchange": self.dlx_exchange_name,
            "x-dead-letter-routing-key": "notification.dead_letter",
        }

        return [
            QueueDefinition(
                name=self.settings.QUEUE_APPLICATION_CREATED,
                routing_keys=[
                    self.settings.ROUTING_KEY_APPLICATION_CREATED,
                    "ApplicationCreated",
                ],
                arguments=dlx_args,
            ),
            QueueDefinition(
                name=self.settings.QUEUE_APPLICATION_STATUS_CHANGED,
                routing_keys=[
                    self.settings.ROUTING_KEY_APPLICATION_STATUS_CHANGED,
                    "ApplicationStatusChanged",
                ],
                arguments=dlx_args,
            ),
            QueueDefinition(
                name=self.settings.QUEUE_INTERVIEW_SCHEDULED,
                routing_keys=[
                    self.settings.ROUTING_KEY_INTERVIEW_SCHEDULED,
                    "InterviewScheduled",
                ],
                arguments=dlx_args,
            ),
            QueueDefinition(
                name=self.settings.QUEUE_INTERVIEW_CANCELLED,
                routing_keys=[
                    self.settings.ROUTING_KEY_INTERVIEW_CANCELLED,
                    "InterviewCancelled",
                ],
                arguments=dlx_args,
            ),
            QueueDefinition(
                name=self.settings.QUEUE_JOB_AVAILABILITY,
                routing_keys=[
                    self.settings.ROUTING_KEY_JOB_AVAILABILITY,
                    "JobAvailabilityChanged",
                ],
                arguments=dlx_args,
            ),
        ]

