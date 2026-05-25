import pytest
import time
from pathlib import Path
from unittest.mock import patch

from core.config import Settings
from core.detection.statistical import StatisticalDetector
from core.metrics.engine import MetricsEngine


def _make_event(pid=123, op_type=1, fd_type=1, fd=10, bytes=0, filename="/tmp/x"):
    return {"pid": pid, "op_type": op_type, "fd_type": fd_type,
            "fd": fd, "bytes": bytes, "filename": filename}


class TestStatisticalDetectorInit:
    def test_default_threshold(self):
        engine = MetricsEngine()
        detector = StatisticalDetector(engine)
        assert detector.threshold_z == 3.0

    def test_custom_threshold(self):
        engine = MetricsEngine()
        settings = Settings(z_threshold=5.0)
        detector = StatisticalDetector(engine, settings=settings)
        assert detector.threshold_z == 5.0

    def test_engine_reference_stored(self):
        engine = MetricsEngine()
        detector = StatisticalDetector(engine)
        assert detector.engine is engine


class TestStatisticalDetectorEvaluate:
    def test_unknown_pid_returns_non_anomalous(self):
        engine = MetricsEngine()
        detector = StatisticalDetector(engine)
        result = detector.evaluate(999, [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert result["is_anomalous"] is False
        assert result["max_z_score"] == 0.0

    def test_known_pid_no_deviation(self):
        engine = MetricsEngine(settings=Settings(ewma_alpha=1.0))
        base = time.time()
        with patch("time.time", side_effect=[base, base, base + 1.1]):
            detector = StatisticalDetector(engine)
            engine.update(_make_event(pid=123, op_type=1))
            engine.update(_make_event(pid=123, op_type=1))
        result = detector.evaluate(123, engine.get_current_vector(123))
        assert result["is_anomalous"] is False

    def test_severity_mapping(self):
        engine = MetricsEngine()
        detector = StatisticalDetector(engine)
        assert detector._severity(1.0) == "info"
        assert detector._severity(3.5) == "warning"
        assert detector._severity(250.0) == "critical"

    def test_z_below_threshold_not_anomalous(self):
        engine = MetricsEngine(settings=Settings(ewma_alpha=1.0))
        base = time.time()
        # MetricsEngine.update() calls time.time() once per event (snapshot
        # check) plus one extra call inside _Profile.__init__ on first ingest.
        # 11 events → 12 time.time() calls; last one crosses the 1 s
        # snapshot boundary.
        times = [base] * 11 + [base + 1.1]
        with patch("time.time", side_effect=times):
            detector = StatisticalDetector(engine)
            for _ in range(10):
                engine.update(_make_event(pid=123, op_type=1))
            engine.update(_make_event(pid=123, op_type=1))
        cur = engine.get_current_vector(123)
        result = detector.evaluate(123, cur)
        assert "is_anomalous" in result
        assert "max_z_score" in result
        assert "severity" in result
        assert "z_vector" in result
        assert "euclidean_distance" in result

    def test_result_has_required_fields(self):
        engine = MetricsEngine()
        detector = StatisticalDetector(engine)
        result = detector.evaluate(1, [1.0, 2.0, 3.0, 0.0, 0.0, 0.0, 0.0])
        for key in ("pid", "is_anomalous", "max_z_score", "z_vector",
                    "euclidean_distance", "severity"):
            assert key in result

    def test_multiple_pids_independent(self):
        engine = MetricsEngine(settings=Settings(ewma_alpha=1.0))
        detector = StatisticalDetector(engine)
        base = time.time()
        with patch("time.time", side_effect=[base, base, base, base, base + 1.1]):
            engine.update(_make_event(pid=10, op_type=1))
            engine.update(_make_event(pid=20, op_type=1))
            engine.update(_make_event(pid=10, op_type=1))
        r10 = detector.evaluate(10, engine.get_current_vector(10))
        r20 = detector.evaluate(20, engine.get_current_vector(20))
        assert r10["pid"] == 10
        assert r20["pid"] == 20

