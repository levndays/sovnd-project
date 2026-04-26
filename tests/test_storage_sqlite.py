import pytest
import sys
import sqlite3
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from storage.sqlite import StorageManager


class TestStorageManagerSchema:
    """Tests for database schema initialization."""

    def test_init_creates_profiles_table(self):
        """Verify profiles table is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='profiles'"
            )
            result = cursor.fetchone()
            conn.close()
            
            assert result is not None, "profiles table should exist"

    def test_init_creates_alerts_table(self):
        """Verify alerts table is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='alerts'"
            )
            result = cursor.fetchone()
            conn.close()
            
            assert result is not None, "alerts table should exist"

    def test_init_creates_profiles_with_correct_columns(self):
        """Verify profiles table has required columns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("PRAGMA table_info(profiles)")
            columns = {row[1] for row in cursor.fetchall()}
            conn.close()
            
            required = {"id", "identifier", "mu", "sigma", "last_updated"}
            assert required.issubset(columns), f"Missing columns: {required - columns}"

    def test_init_creates_alerts_with_correct_columns(self):
        """Verify alerts table has required columns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("PRAGMA table_info(alerts)")
            columns = {row[1] for row in cursor.fetchall()}
            conn.close()
            
            required = {"id", "timestamp", "pid", "score", "severity", "reasons", "container_info"}
            assert required.issubset(columns), f"Missing columns: {required - columns}"

    def test_profile_identifier_unique_constraint(self):
        """Verify identifier column has UNIQUE constraint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='profiles'"
            )
            schema = cursor.fetchone()[0]
            conn.close()
            
            assert "UNIQUE" in schema.upper(), "profiles.identifier must have UNIQUE constraint"


class TestStorageManagerAlerts:
    """Tests for alert storage operations."""

    def test_save_alert_inserts_record(self):
        """Verify save_alert inserts a record into the database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            alert_data = {
                "timestamp": "2024-01-01T00:00:00",
                "pid": 1234,
                "score": 15.5,
                "severity": "critical",
                "reasons": ["unauthorized access"],
                "container_info": {"id": "abc123"}
            }
            manager.save_alert(alert_data)
            
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT * FROM alerts WHERE pid = ?", (1234,))
            row = cursor.fetchone()
            conn.close()
            
            assert row is not None, "Alert should be saved"
            assert row[2] == 1234
            assert row[3] == 15.5
            assert row[4] == "critical"

    def test_save_alert_serializes_reasons_as_json(self):
        """Verify reasons are stored as JSON string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            alert_data = {
                "timestamp": "2024-01-01T00:00:00",
                "pid": 1234,
                "score": 10.0,
                "severity": "warning",
                "reasons": ["reason1", "reason2"],
                "container_info": None
            }
            manager.save_alert(alert_data)
            
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT reasons FROM alerts WHERE pid = ?", (1234,))
            row = cursor.fetchone()
            conn.close()
            
            parsed = json.loads(row[0])
            assert parsed == ["reason1", "reason2"]

    def test_save_alert_serializes_container_info_as_json(self):
        """Verify container_info is stored as JSON string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            alert_data = {
                "timestamp": "2024-01-01T00:00:00",
                "pid": 1234,
                "score": 10.0,
                "severity": "warning",
                "reasons": [],
                "container_info": {"id": "def456", "name": "testcontainer"}
            }
            manager.save_alert(alert_data)
            
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT container_info FROM alerts WHERE pid = ?", (1234,))
            row = cursor.fetchone()
            conn.close()
            
            parsed = json.loads(row[0])
            assert parsed == {"id": "def456", "name": "testcontainer"}

    def test_save_alert_handles_none_container_info(self):
        """Verify None container_info is handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            alert_data = {
                "timestamp": "2024-01-01T00:00:00",
                "pid": 1234,
                "score": 10.0,
                "severity": "warning",
                "reasons": [],
                "container_info": None
            }
            manager.save_alert(alert_data)
            
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT container_info FROM alerts WHERE pid = ?", (1234,))
            row = cursor.fetchone()
            conn.close()
            
            assert row[0] == "null"

    def test_get_recent_alerts_returns_ordered_by_timestamp(self):
        """Verify alerts are returned in descending timestamp order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            manager.save_alert({
                "timestamp": "2024-01-01T00:00:00",
                "pid": 1001,
                "score": 5.0,
                "severity": "info",
                "reasons": [],
                "container_info": None
            })
            manager.save_alert({
                "timestamp": "2024-01-02T00:00:00",
                "pid": 1002,
                "score": 10.0,
                "severity": "warning",
                "reasons": [],
                "container_info": None
            })
            
            alerts = manager.get_recent_alerts(limit=10)
            
            assert alerts[0]["pid"] == 1002, "Most recent alert should be first"
            assert alerts[1]["pid"] == 1001

    def test_get_recent_alerts_respects_limit(self):
        """Verify limit parameter is respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            for i in range(10):
                manager.save_alert({
                    "timestamp": f"2024-01-0{i+1}T00:00:00",
                    "pid": 1000 + i,
                    "score": 5.0,
                    "severity": "info",
                    "reasons": [],
                    "container_info": None
                })
            
            alerts = manager.get_recent_alerts(limit=3)
            
            assert len(alerts) == 3, "Should return only 3 alerts"

    def test_get_recent_alerts_returns_empty_list_when_no_alerts(self):
        """Verify empty list is returned when no alerts exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            alerts = manager.get_recent_alerts(limit=10)
            
            assert alerts == []

    def test_get_recent_alerts_parses_json_reasons(self):
        """Verify reasons are returned as JSON string (NOT auto-parsed)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            manager.save_alert({
                "timestamp": "2024-01-01T00:00:00",
                "pid": 1234,
                "score": 10.0,
                "severity": "warning",
                "reasons": ["reason1", "reason2"],
                "container_info": None
            })
            
            alerts = manager.get_recent_alerts(limit=1)
            
            assert alerts[0]["reasons"] == '["reason1", "reason2"]'

    def test_get_recent_alerts_parses_json_container_info(self):
        """Verify container_info is returned as JSON string (NOT auto-parsed)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            manager.save_alert({
                "timestamp": "2024-01-01T00:00:00",
                "pid": 1234,
                "score": 10.0,
                "severity": "warning",
                "reasons": [],
                "container_info": {"id": "abc", "name": "test"}
            })
            
            alerts = manager.get_recent_alerts(limit=1)
            
            assert alerts[0]["container_info"] == '{"id": "abc", "name": "test"}'


class TestStorageManagerProfiles:
    """Tests for profile storage operations."""

    def test_save_profile_inserts_record(self):
        """Verify save_profile inserts a record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            manager.save_profile("bash", b"mu_data", b"sigma_data")
            
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT * FROM profiles WHERE identifier = ?", ("bash",))
            row = cursor.fetchone()
            conn.close()
            
            assert row is not None, "Profile should be saved"
            assert row[1] == "bash"

    def test_save_profile_updates_existing(self):
        """Verify save_profile updates existing record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            manager.save_profile("bash", b"mu_v1", b"sigma_v1")
            manager.save_profile("bash", b"mu_v2", b"sigma_v2")
            
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT mu, sigma FROM profiles WHERE identifier = ?", ("bash",))
            row = cursor.fetchone()
            conn.close()
            
            assert row[0] == b"mu_v2", "mu should be updated"
            assert row[1] == b"sigma_v2", "sigma should be updated"

    def test_get_profile_returns_dict(self):
        """Verify get_profile returns dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            manager.save_profile("bash", b"mu_data", b"sigma_data")
            profile = manager.get_profile("bash")
            
            assert isinstance(profile, dict)
            assert profile["identifier"] == "bash"
            assert profile["mu"] == b"mu_data"

    def test_get_profile_returns_none_for_missing(self):
        """Verify get_profile returns None for non-existent profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            profile = manager.get_profile("nonexistent")
            
            assert profile is None


class TestStorageManagerConcurrency:
    """Tests for thread safety."""

    def test_lock_is_thread_lock(self):
        """Verify lock is a threading.Lock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            import threading
            assert isinstance(manager._lock, type(threading.Lock()))

    def test_concurrent_saves_do_not_corrupt(self):
        """Verify concurrent writes don't corrupt database."""
        import threading
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            def save_alert(i):
                manager.save_alert({
                    "timestamp": f"2024-01-0{i%9+1}T00:00:00",
                    "pid": 2000 + i,
                    "score": 5.0,
                    "severity": "info",
                    "reasons": [],
                    "container_info": None
                })
            
            threads = [threading.Thread(target=save_alert, args=(i,)) for i in range(20)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM alerts")
            count = cursor.fetchone()[0]
            conn.close()
            
            assert count == 20, "All 20 alerts should be saved"