import logging
import threading
import time
from typing import Optional

import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError

from app.config.settings import Settings, get_settings
from app.messaging.rabbitmq_config import RabbitMQTopology
from app.messaging.rabbitmq_connection import RabbitMQConnectionManager, get_connection_manager
from app.schemas.event_schema import PermanentEventError, TemporaryEventError
from app.services.event_processor import EventProcessor, get_event_processor

logger = logging.getLogger("ms-notification.rabbitmq.consumer")


class RabbitMQConsumer:
    """
    Robust background AMQP consumer.
    Features:
    - Automatic reconnection loop with backoff.
    - QoS prefetch.
    - Manual ACK / NACK.
    - Dead Letter Queue routing on permanent errors and retry exhaustion.
    - Non-blocking daemon thread.
    """

    def __init__(
        self,
        connection_manager: Optional[RabbitMQConnectionManager] = None,
        event_processor: Optional[EventProcessor] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.connection_manager = connection_manager or get_connection_manager()
        self.event_processor = event_processor or get_event_processor()
        self.topology = RabbitMQTopology(self.settings)

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_active = False

    def is_running(self) -> bool:
        """Return True if background consumer thread is active."""
        return self._is_active and self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start the consumer loop in a background daemon thread."""
        if self.is_running():
            logger.warning("RabbitMQ consumer is already running.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_consumer_loop,
            name="RabbitMQConsumerThread",
            daemon=True
        )
        self._thread.start()
        logger.info("RabbitMQ consumer background thread started.")

    def stop(self) -> None:
        """Signal the consumer thread to stop gracefully and close connections."""
        logger.info("Stopping RabbitMQ consumer...")
        self._stop_event.set()
        self._is_active = False
        self.connection_manager.close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        logger.info("RabbitMQ consumer stopped.")

    def _run_consumer_loop(self) -> None:
        """Outer loop handling automatic reconnect with backoff."""
        backoff = 2
        max_backoff = 30

        while not self._stop_event.is_set():
            try:
                self._is_active = True
                self._consume()
                backoff = 2  # Reset on clean run
            except (AMQPConnectionError, AMQPChannelError, OSError) as exc:
                if self._stop_event.is_set():
                    break
                logger.warning(
                    f"RabbitMQ connection lost or unavailable: {exc}. "
                    f"Retrying in {backoff} seconds..."
                )
                self._is_active = False
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
            except Exception as exc:
                if self._stop_event.is_set():
                    break
                logger.exception(f"Unexpected error in RabbitMQ consumer: {exc}. Retrying in {backoff}s...")
                self._is_active = False
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

        self._is_active = False

    def _consume(self) -> None:
        """Set up channel, QoS, consumer tags, and start consuming."""
        conn = self.connection_manager.connect()
        channel = conn.channel()
        self.connection_manager.declare_topology(channel)

        channel.basic_qos(prefetch_count=self.settings.RABBITMQ_PREFETCH_COUNT)

        for q_def in self.topology.get_queues():
            channel.basic_consume(
                queue=q_def.name,
                on_message_callback=self._on_message,
                auto_ack=False,
            )
            logger.info(f"Registered consumer for queue: {q_def.name}")

        logger.info("RabbitMQ consumer is now waiting for messages...")
        while not self._stop_event.is_set() and channel.is_open:
            conn.process_data_events(time_limit=1.0)

        if channel.is_open:
            channel.close()

    def _on_message(
        self,
        ch: pika.adapters.blocking_connection.BlockingChannel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes,
    ) -> None:
        """Callback for incoming messages."""
        delivery_tag = method.delivery_tag
        routing_key = method.routing_key
        headers = properties.headers or {}

        # Determine current retry count
        retry_count = headers.get("x-retry-count", 0)

        try:
            self.event_processor.process_event(
                raw_body=body,
                routing_key=routing_key,
                headers=headers,
            )
            # Acknowledge message upon successful processing or idempotent deduplication
            ch.basic_ack(delivery_tag=delivery_tag)
            logger.debug(f"ACK message {delivery_tag} on {routing_key}")

        except PermanentEventError as exc:
            # Permanent failure: route directly to Dead Letter Queue (DLQ)
            logger.error(
                f"[PERMANENT ERROR] Rejecting message {delivery_tag} ({routing_key}) "
                f"to DLQ: {exc}"
            )
            ch.basic_nack(delivery_tag=delivery_tag, requeue=False)

        except TemporaryEventError as exc:
            # Transient failure: retry with backoff up to MAX_RETRIES
            if retry_count < self.settings.RABBITMQ_MAX_RETRIES:
                new_retry = retry_count + 1
                logger.warning(
                    f"[TEMPORARY ERROR] Message {delivery_tag} ({routing_key}) failed: {exc}. "
                    f"Retry {new_retry}/{self.settings.RABBITMQ_MAX_RETRIES} in "
                    f"{self.settings.RABBITMQ_RETRY_BACKOFF_SECONDS}s..."
                )
                time.sleep(self.settings.RABBITMQ_RETRY_BACKOFF_SECONDS)
                # Re-publish with incremented retry header and ACK current delivery
                new_headers = dict(headers)
                new_headers["x-retry-count"] = new_retry
                new_properties = pika.BasicProperties(
                    headers=new_headers,
                    delivery_mode=2,  # Persistent
                    content_type=properties.content_type,
                )
                ch.basic_publish(
                    exchange=method.exchange,
                    routing_key=routing_key,
                    body=body,
                    properties=new_properties,
                )
                ch.basic_ack(delivery_tag=delivery_tag)
            else:
                # Max retries exhausted: route to DLQ
                logger.error(
                    f"[RETRY EXHAUSTED] Message {delivery_tag} ({routing_key}) exceeded "
                    f"{self.settings.RABBITMQ_MAX_RETRIES} retries. Routing to DLQ."
                )
                ch.basic_nack(delivery_tag=delivery_tag, requeue=False)

        except Exception as exc:
            logger.exception(f"Unexpected fatal error handling message {delivery_tag}: {exc}")
            ch.basic_nack(delivery_tag=delivery_tag, requeue=False)


_global_consumer: Optional[RabbitMQConsumer] = None


def get_rabbitmq_consumer() -> RabbitMQConsumer:
    """Singleton getter for RabbitMQConsumer."""
    global _global_consumer
    if _global_consumer is None:
        _global_consumer = RabbitMQConsumer()
    return _global_consumer

