import sqlite3
import json
import logging
import os
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class StorageManager:
    """
    Handles persistence for security profiles and alerts (Section 3.2).
    Uses a thread-safe connection pattern and context managers.
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.environ.get("DB_PATH", "data/sovnd.db")
        self._lock = threading.Lock()
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initializes the database schema."""
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else "data", exist_ok=True)
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT UNIQUE, -- e.g., process name or container image
                    mu BLOB,
                    sigma BLOB,
                    last_updated TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    pid INTEGER,
                    comm TEXT,
                    score REAL,
                    severity TEXT,
                    reasons TEXT,       -- JSON string
                    breakdown TEXT,     -- JSON string
                    container_info TEXT -- JSON string
                )
            """)
            conn.commit()
        try:
            os.chmod(self.db_path, 0o644)
        except PermissionError:
            pass
        logger.info("Database initialized at %s", self.db_path)

    def save_alert(self, alert_data: Dict[str, Any]):
        """Persists a generated alert."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO alerts (timestamp, pid, comm, score, severity, reasons, breakdown, container_info) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        alert_data.get("timestamp"),
                        alert_data.get("pid"),
                        alert_data.get("comm", "unknown"),
                        alert_data.get("score"),
                        alert_data.get("severity"),
                        json.dumps(alert_data.get("reasons")),
                        json.dumps(alert_data.get("breakdown", {})),
                        json.dumps(alert_data.get("container_info"))
                    )
                )
                conn.commit()
        try:
            os.chmod(self.db_path, 0o644)
        except PermissionError:
            pass

    def get_recent_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves most recent security alerts."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            rows = cursor.fetchall()
            alerts = []
            for row in rows:
                alert = dict(row)
                alert["reasons"] = json.loads(alert["reasons"]) if alert["reasons"] else []
                alert["breakdown"] = json.loads(alert["breakdown"]) if alert["breakdown"] else {}
                alert["container_info"] = json.loads(alert["container_info"]) if alert["container_info"] else None
                alerts.append(alert)
            return alerts

    def save_profile(self, identifier: str, mu: bytes, sigma: bytes):
        """Saves or updates a behavioral profile."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO profiles (identifier, mu, sigma, last_updated)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(identifier) DO UPDATE SET
                        mu=excluded.mu,
                        sigma=excluded.sigma,
                        last_updated=excluded.last_updated
                """, (identifier, mu, sigma, datetime.now().isoformat()))
                conn.commit()

    def get_profile(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Retrieves a behavioral profile by identifier."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM profiles WHERE identifier = ?", (identifier,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def clear_alerts(self):
        """Clears all alerts from the database."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM alerts")
                conn.commit()
        try:
            os.chmod(self.db_path, 0o644)
        except PermissionError:
            pass
        logger.info("All alerts cleared")
