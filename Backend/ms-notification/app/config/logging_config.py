import logging
import re
import sys

_SENSITIVE_PATTERNS = [
    re.compile(r'(password[:=]\s*)([^\s&,]+)', re.IGNORECASE),
    re.compile(r'(secret[:=]\s*)([^\s&,]+)', re.IGNORECASE),
    re.compile(r'(amqp://[^:]+:)([^@]+)(@)', re.IGNORECASE),
    re.compile(r'(smtp_password[:=]\s*)([^\s&,]+)', re.IGNORECASE),
]


class SensitiveDataFilter(logging.Filter):
    """Filter that masks passwords and credentials from logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg
            for pattern in _SENSITIVE_PATTERNS:
                msg = pattern.sub(r'\1******\3' if r'\3' in pattern.pattern else r'\1******', msg)
            record.msg = msg
        return True


def setup_logging(debug: bool = False) -> None:
    """Configure structured logging for ms-notification."""
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    formatter = logging.Formatter(log_format, datefmt=date_format)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveDataFilter())

    root_logger.addHandler(console_handler)

    # Reduce verbosity of noisy third-party loggers
    logging.getLogger("pika").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

