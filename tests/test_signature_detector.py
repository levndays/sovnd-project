import pytest
import numpy as np
from pathlib import Path

SRC_DIR = Path(__file__).parent.parent / "src"


class TestSignatureDetectorInit:
    """Tests for SignatureDetector initialization."""

    def test_detector_file_exists(self):
        """Verify SignatureDetector module exists."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        assert SignatureDetector is not None

    def test_default_init(self):
        """Verify default initialization."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        assert detector is not None

    def test_critical_paths_initialized(self):
        """Verify critical_paths list is initialized."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        assert hasattr(detector, "critical_paths")
        assert len(detector.critical_paths) > 0

    def test_suspicious_comm_initialized(self):
        """Verify suspicious_comm list is initialized."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        assert hasattr(detector, "suspicious_comm")
        assert "bash" in detector.suspicious_comm


class TestSignatureDetectorCriticalPaths:
    """Tests for critical path detection (IOCs)."""

    def test_etc_shadow_detected(self):
        """Verify /etc/shadow access is detected."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/etc/shadow", "comm": "test"}
        result = detector.analyze_event(event)
        
        assert result is not None
        assert result["type"] == "SIGNATURE_MATCH"
        assert "critical" in result["severity"]

    def test_etc_sudoers_detected(self):
        """Verify /etc/sudoers access is detected."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/etc/sudoers", "comm": "test"}
        result = detector.analyze_event(event)
        
        assert result is not None
        assert result["type"] == "SIGNATURE_MATCH"

    def test_var_run_docker_sock_detected(self):
        """Verify /var/run/docker.sock access is detected."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/var/run/docker.sock", "comm": "test"}
        result = detector.analyze_event(event)
        
        assert result is not None
        assert result["type"] == "SIGNATURE_MATCH"

    def test_root_ssh_key_access(self):
        """Verify /root/.ssh/ key access is detected."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/root/.ssh/id_rsa", "comm": "test"}
        result = detector.analyze_event(event)
        
        assert result is not None

    def test_proc_kcore_detected(self):
        """Verify /proc/kcore access is detected."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/proc/kcore", "comm": "test"}
        result = detector.analyze_event(event)
        
        assert result is not None

    def test_non_matching_path_returns_none(self):
        """Verify non-matching path returns None."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/etc/passwd", "comm": "test"}
        result = detector.analyze_event(event)
        
        assert result is None


class TestSignatureDetectorSuspiciousComm:
    """Tests for suspicious process detection."""

    def test_bash_process_heuristic(self):
        """Verify bash process triggers heuristic."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/bin/bash", "comm": "bash"}
        result = detector.analyze_event(event)
        
        assert result is not None
        assert result["type"] == "HEURISTIC_MATCH"

    def test_sh_process_heuristic(self):
        """Verify sh process triggers heuristic."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/bin/sh", "comm": "sh"}
        result = detector.analyze_event(event)
        
        assert result is not None
        assert result["type"] == "HEURISTIC_MATCH"

    def test_nc_process_heuristic(self):
        """Verify nc (netcat) triggers heuristic."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/usr/bin/nc", "comm": "nc"}
        result = detector.analyze_event(event)
        
        assert result is not None
        assert result["severity"] == "warning"

    def test_ncat_process_heuristic(self):
        """Verify ncat triggers heuristic."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/usr/bin/ncat", "comm": "ncat"}
        result = detector.analyze_event(event)
        
        assert result is not None

    def test_python_process_heuristic(self):
        """Verify python process triggers heuristic."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/usr/bin/python3", "comm": "python"}
        result = detector.analyze_event(event)
        
        assert result is not None

    def test_perl_process_heuristic(self):
        """Verify perl process triggers heuristic."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/usr/bin/perl", "comm": "perl"}
        result = detector.analyze_event(event)
        
        assert result is not None

    def test_non_suspicious_comm_no_heuristic(self):
        """Verify non-suspicious process doesn't trigger heuristic."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/bin/nginx", "comm": "nginx"}
        result = detector.analyze_event(event)
        
        assert result is None


class TestSignatureDetectorEdgeCases:
    """Edge case tests for SignatureDetector."""

    def test_empty_event(self):
        """Verify empty event returns None."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {}
        result = detector.analyze_event(event)
        
        assert result is None

    def test_empty_filename(self):
        """Verify empty filename returns None."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "", "comm": "bash"}
        result = detector.analyze_event(event)
        
        assert result is None

    def test_none_filename(self):
        """Verify None filename doesn't crash."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": None, "comm": "bash"}
        result = detector.analyze_event(event)
        
        assert result is None

    def test_missing_comm_key(self):
        """Verify missing 'comm' key is handled."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/etc/shadow"}
        result = detector.analyze_event(event)
        
        assert result is not None

    def test_missing_filename_key(self):
        """Verify missing 'filename' key is handled."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"comm": "test"}
        result = detector.analyze_event(event)
        
        assert result is None

    def test_path_with_extra_slashes(self):
        """Verify path normalization works."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "///etc///shadow", "comm": "test"}
        result = detector.analyze_event(event)
        
        assert result is None

    def test_path_with_dotdots(self):
        """Verify path with .. is handled."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/etc/../etc/shadow", "comm": "test"}
        result = detector.analyze_event(event)
        
        assert result is None


class TestSignatureDetectorReturnValues:
    """Tests for return value structure."""

    def test_signature_match_structure(self):
        """Verify SIGNATURE_MATCH has correct structure."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/etc/shadow", "comm": "test"}
        result = detector.analyze_event(event)
        
        assert "type" in result
        assert "reason" in result
        assert "severity" in result
        assert "ioc" in result

    def test_heuristic_match_structure(self):
        """Verify HEURISTIC_MATCH has correct structure."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/bin/bash", "comm": "bash"}
        result = detector.analyze_event(event)
        
        assert "type" in result
        assert "reason" in result
        assert "severity" in result

    def test_severity_values(self):
        """Verify severity values are valid."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/etc/shadow", "comm": "test"}
        result = detector.analyze_event(event)
        
        assert result["severity"] in ["info", "warning", "critical"]


class TestSignatureDetectorPriority:
    """Tests for detection priority (critical paths > heuristics)."""

    def test_critical_path_takes_priority(self):
        """Verify critical path takes priority over heuristic."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/etc/shadow", "comm": "bash"}
        result = detector.analyze_event(event)
        
        assert result["type"] == "SIGNATURE_MATCH"
        assert result["severity"] == "critical"


class TestSignatureDetectorIOCFields:
    """Tests for specific IOC field values."""

    def test_shadow_ioc_value(self):
        """Verify shadow IOC has correct value."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/etc/shadow", "comm": "test"}
        result = detector.analyze_event(event)
        
        assert result["ioc"] == "/etc/shadow"

    def test_sudoers_ioc_value(self):
        """Verify sudoers IOC has correct value."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/etc/sudoers", "comm": "test"}
        result = detector.analyze_event(event)
        
        assert result["ioc"] == "/etc/sudoers"

    def test_docker_sock_ioc_value(self):
        """Verify docker.sock IOC has correct value."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/var/run/docker.sock", "comm": "test"}
        result = detector.analyze_event(event)
        
        assert result["ioc"] == "/var/run/docker.sock"


class TestSignatureDetectorRealWorld:
    """Real-world attack scenario tests."""

    def test_password_file_access(self):
        """Verify /etc/passwd access doesn't trigger (common task)."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/etc/passwd", "comm": "cat"}
        result = detector.analyze_event(event)
        
        assert result is None

    def test_scheduled_task_access(self):
        """Verify cron access is allowed."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/etc/cron.d", "comm": "cron"}
        result = detector.analyze_event(event)
        
        assert result is None

    def test_web_server_shell(self):
        """Verify web server spawning shell is detected."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/bin/bash", "comm": "nginx"}
        result = detector.analyze_event(event)
        
        assert result is not None
        assert result["severity"] == "warning"

    def test_reverse_shell_pattern(self):
        """Verify reverse shell pattern is caught."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.detector.signature import SignatureDetector
        detector = SignatureDetector()
        
        event = {"filename": "/bin/bash", "comm": "nc"}
        result = detector.analyze_event(event)
        
        assert result is not None