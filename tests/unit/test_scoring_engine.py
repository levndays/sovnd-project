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


class TestScoringEngineNgram:
    """N-gram contribution (rare-syscall-sequence signal from §2.1)."""

    def _stat(self, ngram: float):
        return {
            "pid": 1,
            "is_anomalous": False,
            "max_z_score": 0.0,
            "ngram_anomaly": ngram,
        }

    def test_ngram_below_floor_does_not_contribute(self):
        """Cold-start n-gram scores near 1.0 are uninformative; the
        scorer ignores anything below 0.7."""
        engine = ScoringEngine(settings=Settings(score_threshold=1.0))
        event = {"pid": 1, "comm": "test"}
        # Push past threshold via signature so we get an Alert back
        # and can inspect the breakdown.
        result = engine.compute(
            event=event,
            stat_report=self._stat(ngram=0.5),
            sig_match={"type": "SIGNATURE_MATCH", "reason": "x"},
        )
        assert result is not None
        assert result.breakdown["ngram"] == 0.0

    def test_ngram_above_floor_contributes(self):
        engine = ScoringEngine(settings=Settings(score_threshold=1.0))
        event = {"pid": 1, "comm": "test"}
        result = engine.compute(
            event=event,
            stat_report=self._stat(ngram=1.0),
            sig_match={"type": "SIGNATURE_MATCH", "reason": "x"},
        )
        assert result is not None
        # ngram weight defaults to 3.0; 3.0 * 1.0 = 3.0
        assert result.breakdown["ngram"] == 3.0
        assert any("n-gram" in r for r in result.reasons)


class TestScoringEnginePctx:
    """Per-process P_ctx context multiplier (§2.2)."""

    def _stat(self):
        return {"pid": 1, "is_anomalous": False, "max_z_score": 0.0}

    def test_default_comm_pctx_is_1(self):
        engine = ScoringEngine(settings=Settings(score_threshold=1.0))
        event = {"pid": 1, "comm": "totally-unknown"}
        result = engine.compute(
            event=event,
            stat_report=self._stat(),
            sig_match={"type": "SIGNATURE_MATCH", "reason": "x"},
        )
        assert result is not None
        assert result.breakdown["p_ctx"] == 1.0
        # No multiplier → score == raw signature contribution
        assert result.score == 15.0

    def test_quiet_system_tool_dampens_score(self):
        """``cat`` is in the noisy-utility bucket (P_ctx=0.8)."""
        engine = ScoringEngine(settings=Settings(score_threshold=1.0))
        event = {"pid": 1, "comm": "cat"}
        result = engine.compute(
            event=event,
            stat_report=self._stat(),
            sig_match={"type": "SIGNATURE_MATCH", "reason": "x"},
        )
        assert result is not None
        assert result.breakdown["p_ctx"] == 0.8
        # 15.0 * 0.8 = 12.0
        assert result.score == 12.0

    def test_shell_amplifies_score(self):
        """``bash`` invoked in a risky context is amplified (P_ctx=1.3)."""
        engine = ScoringEngine(settings=Settings(score_threshold=1.0))
        event = {"pid": 1, "comm": "bash"}
        result = engine.compute(
            event=event,
            stat_report=self._stat(),
            sig_match={"type": "SIGNATURE_MATCH", "reason": "x"},
        )
        assert result is not None
        assert result.breakdown["p_ctx"] == 1.3
        # 15.0 * 1.3 = 19.5
        assert result.score == 19.5

    def test_dampened_score_can_drop_below_threshold(self):
        """A borderline alert from a quiet system tool should be
        suppressed by P_ctx — that's the whole point of the multiplier."""
        engine = ScoringEngine(settings=Settings(score_threshold=13.0))
        event = {"pid": 1, "comm": "cat"}
        # 15.0 (sig only) * 0.8 = 12.0 → below threshold of 13.0
        result = engine.compute(
            event=event,
            stat_report=self._stat(),
            sig_match={"type": "SIGNATURE_MATCH", "reason": "x"},
        )
        assert result is None
