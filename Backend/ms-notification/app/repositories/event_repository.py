import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.config.settings import get_settings

logger = logging.getLogger("ms-notification.repository")


class EventRepository:
    """
    Isolated local storage for processed event IDs (Idempotency)
    and notification audit logs.
    No shared database: fully encapsulated inside ms-notification.
    """

    def __init__(self, db_path: Optional[str] = None):
        settings = get_settings()
        self.db_path = db_path or settings.DATABASE_PATH
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        # Ensure parent directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Table for idempotency: ensures duplicate event IDs are caught
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS processed_events (
                        event_id TEXT PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        processed_at TEXT NOT NULL,
                        status TEXT NOT NULL
                    )
                """)
                # Table for notification delivery audit logs
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notification_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT NOT NULL,
                        channel TEXT NOT NULL,
                        recipient TEXT NOT NULL,
                        subject TEXT NOT NULL,
                        status TEXT NOT NULL,
                        sent_at TEXT NOT NULL,
                        error_message TEXT,
                        template_name TEXT,
                        payload TEXT
                    )
                """)
                # Create indexes for fast lookup
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_processed_events_status ON processed_events(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_notification_logs_event_id ON notification_logs(event_id)")
                conn.commit()
                logger.info(f"Initialized local SQLite storage at: {self.db_path}")

    def is_event_processed(self, event_id: str) -> bool:
        """Check if an eventId was already successfully processed."""
        if not event_id:
            return False
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM processed_events WHERE event_id = ? AND status = 'SUCCESS' LIMIT 1",
                    (str(event_id),)
                )
                return cursor.fetchone() is not None

    def record_event_processed(self, event_id: str, event_type: str, status: str = "SUCCESS") -> bool:
        """
        Record an event as processed in the idempotency table.
        Returns True if inserted, False if already exists (primary key collision).
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        """
                        INSERT INTO processed_events (event_id, event_type, processed_at, status)
                        VALUES (?, ?, ?, ?)
                        """,
                        (str(event_id), event_type, now, status)
                    )
                    conn.commit()
                    return True
                except sqlite3.IntegrityError:
                    # Duplicate entry
                    return False

    def record_notification_log(
        self,
        event_id: str,
        channel: str,
        recipient: str,
        subject: str,
        status: str,
        template_name: Optional[str] = None,
        error_message: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> int:
        """Log an outbound notification attempt."""
        now = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(payload, default=str) if payload else None
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO notification_logs (
                        event_id, channel, recipient, subject, status, sent_at,
                        error_message, template_name, payload
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(event_id), channel, recipient, subject, status, now,
                        error_message, template_name, payload_json
                    )
                )
                conn.commit()
                return cursor.lastrowid

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent notification logs for audit and monitoring."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, event_id, channel, recipient, subject, status,
                           sent_at, error_message, template_name, payload
                    FROM notification_logs
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,)
                )
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    item = dict(row)
                    if item.get("payload"):
                        try:
                            item["payload"] = json.loads(item["payload"])
                        except Exception:
                            pass
                    results.append(item)
                return results

    def get_event_count(self) -> int:
        """Return the total number of processed events."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM processed_events")
                return cursor.fetchone()[0]

    def clear_for_test(self) -> None:
        """Clean all records. Used strictly in automated test fixtures."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM processed_events")
                cursor.execute("DELETE FROM notification_logs")
                conn.commit()


_global_repository: Optional[EventRepository] = None


def get_event_repository() -> EventRepository:
    """Singleton getter for EventRepository."""
    global _global_repository
    if _global_repository is None:
        _global_repository = EventRepository()
    return _global_repository

