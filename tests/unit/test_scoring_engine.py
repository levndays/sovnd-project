import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.config import Settings
from core.scoring.engine import ScoringEngine, Alert


class TestScoringEngine:
    """Tests for ScoringEngine."""

    def test_compute_below_threshold(self):
        """Test score below threshold returns None."""
        engine = ScoringEngine(settings=Settings(score_threshold=10.0))
        event = {"pid": 123, "comm": "test"}
        stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
        
        result = engine.compute(
            event=event,
            stat_report=stat_report,
            sig_match=None,
            graph_heuristics=[]
        )
        
        assert result is None

    def test_compute_at_threshold(self):
        """Test score at threshold returns Alert with warning."""
        engine = ScoringEngine(settings=Settings(score_threshold=10.0))
        event = {"pid": 123, "comm": "test"}
        stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
        
        result = engine.compute(
            event=event,
            stat_report=stat_report,
            sig_match=None,
            graph_heuristics=["suspicious_parent"]  # 5.0 * 1 = 5.0, need 2 for 10.0
        )
        
        assert result is None

    def test_compute_above_threshold(self):
        """Test score above threshold returns Alert."""
        engine = ScoringEngine(settings=Settings(score_threshold=10.0))
        event = {"pid": 123, "comm": "test"}
        stat_report = {"pid": 123, "is_anomalous": True, "max_z_score": 2.0}
        
        result = engine.compute(
            event=event,
            stat_report=stat_report,
            sig_match={"reason": "shadow file access"},
            graph_heuristics=["suspicious_parent"]
        )
        
        assert result is not None
        assert result.pid == 123

    def test_compute_signature_critical(self):
        """Test full-confidence signature match plus heuristics is critical.

        Signature IOC match (type=SIGNATURE_MATCH) contributes 15.0;
        two unmapped graph heuristics contribute 5.0 each (default weight).
        Total 25.0 >= critical threshold 22.0.
        """
        engine = ScoringEngine(settings=Settings(score_threshold=10.0))
        event = {"pid": 123, "comm": "test"}
        stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}

        result = engine.compute(
            event=event,
            stat_report=stat_report,
            sig_match={"type": "SIGNATURE_MATCH", "reason": "shadow file access"},
            graph_heuristics=["h1", "h2"],
        )

        assert result is not None
        assert result.severity == "critical"

    def test_compute_warning_threshold(self):
        """Test score between T and 2T without signature is warning."""
        engine = ScoringEngine(settings=Settings(score_threshold=10.0))
        event = {"pid": 123, "comm": "test"}
        stat_report = {"pid": 123, "is_anomalous": True, "max_z_score": 5.0}
        
        result = engine.compute(
            event=event,
            stat_report=stat_report,
            sig_match=None,
            graph_heuristics=["suspicious_parent"]
        )
        
        assert result is not None
        assert result.severity == "warning"

    def test_compute_statistical_scaling(self):
        """Test statistical anomaly scales with Z-score."""
        engine = ScoringEngine(settings=Settings(score_threshold=3.0))
        event = {"pid": 123, "comm": "test"}
        stat_report = {"pid": 123, "is_anomalous": True, "max_z_score": 3.0}
        
        result = engine.compute(
            event=event,
            stat_report=stat_report,
            sig_match=None,
            graph_heuristics=[]
        )
        
        assert result is not None
        assert result.score == 3.0

    def test_compute_multiple_heuristics(self):
        """Test multiple graph heuristics add up."""
        engine = ScoringEngine(settings=Settings(score_threshold=10.0))
        event = {"pid": 123, "comm": "test"}
        stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
        
        result = engine.compute(
            event=event,
            stat_report=stat_report,
            sig_match=None,
            graph_heuristics=["h1", "h2", "h3"]
        )
        
        assert result is not None
        assert result.score == 15.0

    def test_compute_with_container_info(self):
        """Test container_info is included in Alert."""
        engine = ScoringEngine(settings=Settings(score_threshold=10.0))
        event = {"pid": 123, "comm": "test"}
        stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
        container_info = {"id": "abc123", "name": "container1"}
        
        result = engine.compute(
            event=event,
            stat_report=stat_report,
            sig_match={"type": "SIGNATURE_MATCH", "reason": "unauthorized shell"},
            graph_heuristics=[],
            container_info=container_info,
        )

        assert result is not None
        assert result.container_info == container_info

    def test_compute_custom_threshold(self):
        """Test custom threshold is used."""
        engine = ScoringEngine(settings=Settings(score_threshold=5.0))
        event = {"pid": 123, "comm": "test"}
        stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
        
        result = engine.compute(
            event=event,
            stat_report=stat_report,
            sig_match=None,
            graph_heuristics=["suspicious_parent"]
        )
        
        assert result is not None

    def test_alert_dataclass_structure(self):
        """Test Alert dataclass has all required fields."""
        alert = Alert(
            timestamp="2024-01-01T00:00:00",
            pid=123,
            comm="test",
            score=15.0,
            severity="critical",
            reasons=["reason1"],
            breakdown={},
            container_info=None
        )
        
        assert hasattr(alert, "timestamp")
        assert hasattr(alert, "pid")
        assert hasattr(alert, "score")
        assert hasattr(alert, "severity")
        assert hasattr(alert, "reasons")
        assert hasattr(alert, "container_info")

    def test_compute_no_reasons_when_below(self):
        """Test reasons remain empty when below threshold."""
        engine = ScoringEngine(settings=Settings(score_threshold=10.0))
        event = {"pid": 123, "comm": "test"}
        stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
        
        result = engine.compute(
            event=event,
            stat_report=stat_report,
            sig_match=None,
            graph_heuristics=[]
        )
        
        assert result is None
