import pytest
import sys
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from internal.storage.sqlite import StorageManager
from apps.server import app, get_storage


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        manager = StorageManager(db_path=db_path)
        yield manager, db_path


class TestAPIEndpoints:
    """Tests for API endpoints."""

    def test_root_endpoint(self, temp_db):
        """The ``/`` route serves the dashboard HTML; ``/api`` is the
        JSON discovery endpoint that returns the welcome message."""
        manager, _ = temp_db
        app.dependency_overrides[get_storage] = lambda: manager
        try:
            client = TestClient(app)
            response = client.get("/api")

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "SovND API" in data["message"]
        finally:
            app.dependency_overrides.clear()

    def test_status_endpoint_returns_operational(self, temp_db):
        """Test /api/status returns operational status."""
        manager, _ = temp_db
        app.dependency_overrides[get_storage] = lambda: manager
        try:
            client = TestClient(app)
            response = client.get("/api/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "operational"
            assert data["engine"] == "eBPF-CO-RE"
            assert data["version"] == "1.0.0"
        finally:
            app.dependency_overrides.clear()

    def test_alerts_endpoint_returns_list(self, temp_db):
        """Test /api/alerts returns a list."""
        manager, _ = temp_db
        app.dependency_overrides[get_storage] = lambda: manager
        try:
            client = TestClient(app)
            response = client.get("/api/alerts")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
        finally:
            app.dependency_overrides.clear()

    def test_alerts_endpoint_respects_limit_param(self, temp_db):
        """Test /api/alerts respects limit parameter."""
        manager, _ = temp_db
        for i in range(10):
            manager.save_alert({
                "timestamp": f"2024-01-0{i+1}T00:00:00",
                "pid": 3000 + i,
                "score": 5.0,
                "severity": "info",
                "reasons": [],
                "container_info": None
            })
        
        app.dependency_overrides[get_storage] = lambda: manager
        try:
            client = TestClient(app)
            response = client.get("/api/alerts?limit=5")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 5
        finally:
            app.dependency_overrides.clear()

    def test_alerts_endpoint_default_limit(self, temp_db):
        """Test /api/alerts has default limit of 50."""
        manager, _ = temp_db
        for i in range(100):
            manager.save_alert({
                "timestamp": f"2024-01-{(i%30)+1:02d}T00:00:00",
                "pid": 3000 + i,
                "score": 5.0,
                "severity": "info",
                "reasons": [],
                "container_info": None
            })
        
        app.dependency_overrides[get_storage] = lambda: manager
        try:
            client = TestClient(app)
            response = client.get("/api/alerts")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 50
        finally:
            app.dependency_overrides.clear()

    def test_alerts_endpoint_returns_stored_data(self, temp_db):
        """Test /api/alerts returns actual stored alert data with correct types."""
        manager, _ = temp_db
        manager.save_alert({
            "timestamp": "2024-01-15T10:30:00",
            "pid": 9999,
            "score": 25.5,
            "severity": "critical",
            "reasons": ["unauthorized shell", "shadow access"],
            "container_info": {"id": "test123", "name": "malware"}
        })
        
        app.dependency_overrides[get_storage] = lambda: manager
        try:
            client = TestClient(app)
            response = client.get("/api/alerts?limit=1")
            
            assert response.status_code == 200
            data = response.json()
            assert data[0]["pid"] == 9999
            assert data[0]["score"] == 25.5
            assert data[0]["severity"] == "critical"
            
            assert isinstance(data[0]["reasons"], list), "reasons should be a list"
            assert data[0]["reasons"] == ["unauthorized shell", "shadow access"]
            
            assert isinstance(data[0]["container_info"], dict), "container_info should be a dict"
            assert data[0]["container_info"] == {"id": "test123", "name": "malware"}
        finally:
            app.dependency_overrides.clear()

    def test_alerts_endpoint_returns_empty_list_when_no_alerts(self, temp_db):
        """Test /api/alerts returns empty list when no alerts exist."""
        manager, _ = temp_db
        app.dependency_overrides[get_storage] = lambda: manager
        try:
            client = TestClient(app)
            response = client.get("/api/alerts")
            
            assert response.status_code == 200
            assert response.json() == []
        finally:
            app.dependency_overrides.clear()

    def test_alerts_endpoint_handles_database_error(self, temp_db):
        """Test /api/alerts handles database errors gracefully."""
        mock_instance = MagicMock()
        mock_instance.get_recent_alerts.side_effect = RuntimeError("Database corruption")
        
        app.dependency_overrides[get_storage] = lambda: mock_instance
        try:
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/api/alerts")
            
            assert response.status_code == 500
        finally:
            app.dependency_overrides.clear()


class TestPrometheusMetrics:
    """Tests for Prometheus metrics endpoints."""

    def test_metrics_endpoint_returns_prometheus_format(self, temp_db):
        """Test /metrics returns Prometheus format."""
        manager, _ = temp_db
        app.dependency_overrides[get_storage] = lambda: manager
        try:
            client = TestClient(app)
            response = client.get("/metrics")
            
            assert response.status_code == 200
            content = response.text
            assert "sovnd_syscalls_total" in content
            assert "sovnd_cpu_usage_percent" in content
        finally:
            app.dependency_overrides.clear()

    def test_metrics_endpoint_content_type(self, temp_db):
        """Test /metrics returns correct content type."""
        manager, _ = temp_db
        app.dependency_overrides[get_storage] = lambda: manager
        try:
            client = TestClient(app)
            response = client.get("/metrics")
            
            assert response.status_code == 200
            assert "text/plain" in response.headers["content-type"]
            assert "charset=utf-8" in response.headers["content-type"]
        finally:
            app.dependency_overrides.clear()


class TestAPIDependencyInjection:
    """Tests for FastAPI dependency injection."""

    def test_get_storage_returns_storage_manager(self):
        """Test get_storage dependency returns StorageManager instance."""
        storage = get_storage()
        
        assert hasattr(storage, "save_alert")
        assert hasattr(storage, "get_recent_alerts")
        assert hasattr(storage, "save_profile")


class TestAPIMetadata:
    """Tests for API metadata."""

    def test_app_title(self):
        """Test FastAPI app has correct title."""
        assert app.title == "SovND Security API"

    def test_app_description(self):
        """Test FastAPI app has correct description."""
        assert "API for accessing eBPF-based security monitoring data" in app.description

    def test_app_version(self):
        """Test FastAPI app has correct version."""
        assert app.version == "1.0.0"


class TestAPIIntegration:
    """Integration tests for API with real database."""

    def test_full_workflow_save_and_retrieve_alerts(self):
        """Test complete workflow: save alert then retrieve via API."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            alert_data = {
                "timestamp": "2024-06-15T14:30:00",
                "pid": 4242,
                "score": 42.0,
                "severity": "critical",
                "reasons": ["reverse shell detected"],
                "container_info": {"id": "container-x", "name": "attacker"}
            }
            manager.save_alert(alert_data)
            
            app.dependency_overrides[get_storage] = lambda: manager
            try:
                client = TestClient(app)
                response = client.get("/api/alerts?limit=1")
                
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["pid"] == 4242
                assert data[0]["score"] == 42.0
                
                assert isinstance(data[0]["reasons"], list), "reasons must be parsed as list"
                assert isinstance(data[0]["container_info"], dict), "container_info must be parsed as dict"
            finally:
                app.dependency_overrides.clear()

    def test_status_endpoint_when_db_has_profiles(self):
        """Test /api/status works independently of database content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            manager = StorageManager(db_path=db_path)
            
            manager.save_profile("test_proc", b"\x00\x01\x02", b"\x01\x02\x03")
            
            app.dependency_overrides[get_storage] = lambda: manager
            try:
                client = TestClient(app)
                response = client.get("/api/status")
                
                assert response.status_code == 200
                assert response.json()["status"] == "operational"
            finally:
                app.dependency_overrides.clear()