import logging
from typing import Optional
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError
from app.config.settings import Settings, get_settings
from app.messaging.rabbitmq_config import RabbitMQTopology

logger = logging.getLogger("ms-notification.rabbitmq.connection")


class RabbitMQConnectionManager:
    """Manages connection, channel creation, and topology declaration."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.topology = RabbitMQTopology(self.settings)
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None

    def get_connection_parameters(self) -> pika.ConnectionParameters:
        """Build pika ConnectionParameters."""
        credentials = pika.PlainCredentials(
            username=self.settings.RABBITMQ_USER,
            password=self.settings.RABBITMQ_PASSWORD
        )
        return pika.ConnectionParameters(
            host=self.settings.RABBITMQ_HOST,
            port=self.settings.RABBITMQ_PORT,
            virtual_host=self.settings.RABBITMQ_VHOST,
            credentials=credentials,
            heartbeat=30,
            blocked_connection_timeout=30,
            connection_attempts=3,
            retry_delay=2,
        )

    def connect(self) -> pika.BlockingConnection:
        """Establish a blocking connection to RabbitMQ."""
        if self._connection and self._connection.is_open:
            return self._connection

        params = self.get_connection_parameters()
        logger.info(
            f"Connecting to RabbitMQ at {self.settings.RABBITMQ_HOST}:{self.settings.RABBITMQ_PORT} "
            f"(vhost: {self.settings.RABBITMQ_VHOST}, user: {self.settings.RABBITMQ_USER})..."
        )
        self._connection = pika.BlockingConnection(params)
        logger.info("Successfully connected to RabbitMQ.")
        return self._connection

    def get_channel(self) -> pika.adapters.blocking_connection.BlockingChannel:
        """Get or create an active AMQP channel."""
        if self._channel and self._channel.is_open:
            return self._channel

        conn = self.connect()
        self._channel = conn.channel()
        self.declare_topology(self._channel)
        return self._channel

    def declare_topology(self, channel: pika.adapters.blocking_connection.BlockingChannel) -> None:
        """
        Idempotently declare exchanges, dead-letter exchanges, DLQ, queues, and bindings.
        """
        # 1. Main topic exchange
        channel.exchange_declare(
            exchange=self.topology.exchange_name,
            exchange_type=self.topology.exchange_type,
            durable=True
        )

        # 2. Dead Letter Exchange (DLX) & DLQ
        channel.exchange_declare(
            exchange=self.topology.dlx_exchange_name,
            exchange_type="direct",
            durable=True
        )
        channel.queue_declare(
            queue=self.topology.dlq_name,
            durable=True
        )
        channel.queue_bind(
            queue=self.topology.dlq_name,
            exchange=self.topology.dlx_exchange_name,
            routing_key="notification.dead_letter"
        )

        # 3. Microservice queues and bindings
        for q_def in self.topology.get_queues():
            channel.queue_declare(
                queue=q_def.name,
                durable=q_def.durable,
                exclusive=q_def.exclusive,
                auto_delete=q_def.auto_delete,
                arguments=q_def.arguments
            )
            for rk in q_def.routing_keys:
                channel.queue_bind(
                    queue=q_def.name,
                    exchange=self.topology.exchange_name,
                    routing_key=rk
                )

        logger.info("RabbitMQ exchanges, queues, DLQ, and bindings successfully declared.")

    def is_connected(self) -> bool:
        """Health check probe for RabbitMQ."""
        try:
            if self._connection and self._connection.is_open:
                return True
            # Quick probe
            params = self.get_connection_parameters()
            params.connection_attempts = 1
            params.retry_delay = 1
            conn = pika.BlockingConnection(params)
            conn.close()
            return True
        except Exception as exc:
            logger.debug(f"RabbitMQ health probe failed: {exc}")
            return False

    def close(self) -> None:
        """Cleanly close channel and connection."""
        try:
            if self._channel and self._channel.is_open:
                self._channel.close()
        except Exception:
            pass
        try:
            if self._connection and self._connection.is_open:
                self._connection.close()
        except Exception:
            pass
        self._channel = None
        self._connection = None
        logger.info("RabbitMQ connection closed.")


_global_connection_manager = None


def get_connection_manager() -> RabbitMQConnectionManager:
    """Singleton getter for RabbitMQConnectionManager."""
    global _global_connection_manager
    if _global_connection_manager is None:
        _global_connection_manager = RabbitMQConnectionManager()
    return _global_connection_manager

