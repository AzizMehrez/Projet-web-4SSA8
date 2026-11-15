from unittest.mock import MagicMock
import pika
from app.messaging.rabbitmq_consumer import RabbitMQConsumer
from app.schemas.event_schema import PermanentEventError, TemporaryEventError


def test_consumer_on_message_success_acks(test_settings):
    """Consumer calls basic_ack on successful event processing."""
    mock_processor = MagicMock()
    mock_processor.process_event.return_value = (True, "OK")

    consumer = RabbitMQConsumer(
        event_processor=mock_processor,
        settings=test_settings,
    )

    mock_ch = MagicMock()
    mock_method = MagicMock()
    mock_method.delivery_tag = 100
    mock_method.routing_key = "application.created"
    mock_props = MagicMock()
    mock_props.headers = {}

    consumer._on_message(
        ch=mock_ch,
        method=mock_method,
        properties=mock_props,
        body=b'{"eventId": "test"}',
    )

    mock_ch.basic_ack.assert_called_once_with(delivery_tag=100)
    mock_ch.basic_nack.assert_not_called()


def test_consumer_on_message_permanent_error_nacks_to_dlq(test_settings):
    """PermanentEventError must NACK with requeue=False (routes to DLQ)."""
    mock_processor = MagicMock()
    mock_processor.process_event.side_effect = PermanentEventError("Invalid schema")

    consumer = RabbitMQConsumer(
        event_processor=mock_processor,
        settings=test_settings,
    )

    mock_ch = MagicMock()
    mock_method = MagicMock()
    mock_method.delivery_tag = 101
    mock_method.routing_key = "application.created"
    mock_props = MagicMock()
    mock_props.headers = {}

    consumer._on_message(
        ch=mock_ch,
        method=mock_method,
        properties=mock_props,
        body=b'{"invalid": "data"}',
    )

    mock_ch.basic_nack.assert_called_once_with(delivery_tag=101, requeue=False)
    mock_ch.basic_ack.assert_not_called()


def test_consumer_on_message_transient_error_exhausted_retries_routes_to_dlq(test_settings):
    """When retries exceed max_retries, message is NACKed with requeue=False."""
    mock_processor = MagicMock()
    mock_processor.process_event.side_effect = TemporaryEventError("SMTP timeout")

    test_settings.RABBITMQ_MAX_RETRIES = 2
    consumer = RabbitMQConsumer(
        event_processor=mock_processor,
        settings=test_settings,
    )

    mock_ch = MagicMock()
    mock_method = MagicMock()
    mock_method.delivery_tag = 102
    mock_method.routing_key = "interview.scheduled"
    mock_props = MagicMock()
    # Headers show already retried 2 times (equal to max)
    mock_props.headers = {"x-retry-count": 2}

    consumer._on_message(
        ch=mock_ch,
        method=mock_method,
        properties=mock_props,
        body=b'{"eventId": "test"}',
    )

    mock_ch.basic_nack.assert_called_once_with(delivery_tag=102, requeue=False)

