import pytest
import numpy as np
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.detector.statistical import StatisticalDetector
from src.metrics.engine import MetricsEngine


class TestStatisticalDetectorInit:
    """Tests for StatisticalDetector initialization."""

    def test_detector_file_exists(self):
        """Verify StatisticalDetector module exists."""
        assert StatisticalDetector is not None

    def test_default_threshold(self):
        """Verify default threshold is 3.0."""
        engine = MetricsEngine()
        detector = StatisticalDetector(engine)
        assert detector.threshold_z == 3.0

    def test_custom_threshold(self):
        """Verify custom threshold is set."""
        engine = MetricsEngine()
        detector = StatisticalDetector(engine, threshold_z=5.0)
        assert detector.threshold_z == 5.0

    def test_engine_reference_stored(self):
        """Verify engine reference is stored."""
        engine = MetricsEngine()
        detector = StatisticalDetector(engine)
        assert detector.engine is engine


class TestStatisticalDetectorEvaluate:
    """Tests for evaluate method."""

    def test_unknown_pid_returns_non_anomalous(self):
        """Verify unknown PID returns non-anomalous."""
        engine = MetricsEngine()
        detector = StatisticalDetector(engine)
        
        result = detector.evaluate(999, np.array([1.0, 2.0, 3.0]))
        
        assert result["is_anomalous"] is False
        assert result["max_z_score"] == 0.0

    def test_known_pid_z_score_calculation(self):
        """Verify known PID z-score is calculated."""
        engine = MetricsEngine()
        engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
        
        detector = StatisticalDetector(engine, threshold_z=3.0)
        result = detector.evaluate(123, np.array([12.0, 10.0, 8.0]))
        
        assert result["pid"] == 123

    def test_anomaly_detection_threshold(self):
        """Verify anomaly detection above threshold."""
        engine = MetricsEngine()
        engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
        
        detector = StatisticalDetector(engine, threshold_z=3.0)
        result = detector.evaluate(123, np.array([100.0, 10.0, 10.0]))
        
        assert result["is_anomalous"] is True
        assert result["max_z_score"] > 3.0

    def test_no_anomaly_below_threshold(self):
        """Verify no anomaly below threshold."""
        engine = MetricsEngine()
        engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
        
        detector = StatisticalDetector(engine, threshold_z=3.0)
        result = detector.evaluate(123, np.array([12.0, 10.0, 10.0]))
        
        assert result["is_anomalous"] is False

    def test_z_vector_returned(self):
        """Verify z_vector is returned."""
        engine = MetricsEngine()
        engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
        
        detector = StatisticalDetector(engine)
        result = detector.evaluate(123, np.array([20.0, 20.0, 20.0]))
        
        assert "z_vector" in result
        assert isinstance(result["z_vector"], list)

    def test_euclidean_distance_calculated(self):
        """Verify Euclidean distance is calculated."""
        engine = MetricsEngine()
        engine.update_scalar_metrics(123, np.array([0.0, 0.0, 0.0]))
        
        detector = StatisticalDetector(engine)
        result = detector.evaluate(123, np.array([3.0, 4.0, 0.0]))
        
        assert result["euclidean_distance"] == 5.0

    def test_euclidean_distance_zero_for_unknown(self):
        """Verify distance is 0 for unknown PID."""
        engine = MetricsEngine()
        detector = StatisticalDetector(engine)
        
        result = detector.evaluate(999, np.array([1.0, 2.0, 3.0]))
        
        assert result["euclidean_distance"] == 0.0


class TestStatisticalDetectorSeverity:
    """Tests for severity mapping."""

    def test_severity_info_below_threshold(self):
        """Verify severity is info below threshold."""
        engine = MetricsEngine()
        engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
        
        detector = StatisticalDetector(engine, threshold_z=3.0)
        result = detector.evaluate(123, np.array([11.0, 10.0, 10.0]))
        
        assert result["severity"] == "info"

    def test_severity_warning_at_threshold(self):
        """Verify severity is critical at threshold boundary."""
        engine = MetricsEngine()
        engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
        
        detector = StatisticalDetector(engine, threshold_z=3.0)
        result = detector.evaluate(123, np.array([19.0, 10.0, 10.0]))
        
        assert result["severity"] == "warning" or result["severity"] == "critical"

    def test_severity_warning_between_threshold(self):
        """Verify severity is critical above threshold."""
        engine = MetricsEngine()
        engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
        
        detector = StatisticalDetector(engine, threshold_z=3.0)
        result = detector.evaluate(123, np.array([25.0, 10.0, 10.0]))
        
        assert result["severity"] == "critical"

    def test_severity_critical_above_double_threshold(self):
        """Verify severity is critical above 2x threshold."""
        engine = MetricsEngine()
        engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
        
        detector = StatisticalDetector(engine, threshold_z=3.0)
        result = detector.evaluate(123, np.array([100.0, 10.0, 10.0]))
        
        assert result["severity"] == "critical"

    def test_mapped_to_severity_method(self):
        """Verify _map_to_severity method."""
        engine = MetricsEngine()
        detector = StatisticalDetector(engine)
        
        assert detector._map_to_severity(1.0) == "info"
        assert detector._map_to_severity(3.5) == "warning"
        assert detector._map_to_severity(10.0) == "critical"


class TestStatisticalDetectorReturnValues:
    """Tests for return value structure."""

    def test_return_has_pid(self):
        """Verify return has pid field."""
        engine = MetricsEngine()
        detector = StatisticalDetector(engine)
        
        result = detector.evaluate(123, np.array([1.0]))
        
        assert "pid" in result

    def test_return_has_is_anomalous(self):
        """Verify return has is_anomalous field."""
        engine = MetricsEngine()
        detector = StatisticalDetector(engine)
        
        result = detector.evaluate(123, np.array([1.0]))
        
        assert "is_anomalous" in result
        assert isinstance(result["is_anomalous"], bool)

    def test_return_has_max_z_score(self):
        """Verify return has max_z_score field."""
        engine = MetricsEngine()
        detector = StatisticalDetector(engine)
        
        result = detector.evaluate(123, np.array([1.0]))
        
        assert "max_z_score" in result

    def test_return_has_severity(self):
        """Verify return has severity field."""
        engine = MetricsEngine()
        detector = StatisticalDetector(engine)
        
        result = detector.evaluate(123, np.array([1.0]))
        
        assert "severity" in result


class TestStatisticalDetectorEdgeCases:
    """Edge case tests."""

    def test_empty_vector(self):
        """Verify empty vector handled."""
        engine = MetricsEngine()
        detector = StatisticalDetector(engine)
        
        result = detector.evaluate(123, np.array([]))
        
        assert result["pid"] == 123

    def test_single_element_vector(self):
        """Verify single element vector."""
        engine = MetricsEngine()
        engine.update_scalar_metrics(123, np.array([50.0]))
        
        detector = StatisticalDetector(engine)
        result = detector.evaluate(123, np.array([60.0]))
        
        assert result["max_z_score"] > 0

    def test_large_vector(self):
        """Verify large vector handled."""
        engine = MetricsEngine()
        large_vector = np.random.rand(1000)
        detector = StatisticalDetector(engine)
        
        result = detector.evaluate(123, large_vector)
        
        assert "z_vector" in result
        assert len(result["z_vector"]) == 1000

    def test_negative_values(self):
        """Verify negative values handled."""
        engine = MetricsEngine()
        engine.update_scalar_metrics(123, np.array([-10.0, -20.0]))
        
        detector = StatisticalDetector(engine)
        result = detector.evaluate(123, np.array([-5.0, -30.0]))
        
        assert result["max_z_score"] > 0

    def test_zero_threshold(self):
        """Verify zero threshold handled."""
        engine = MetricsEngine()
        engine.update_scalar_metrics(123, np.array([10.0]))
        
        detector = StatisticalDetector(engine, threshold_z=0.0)
        result = detector.evaluate(123, np.array([10.0]))
        
        assert "severity" in result

    def test_negative_threshold(self):
        """Verify negative threshold handled."""
        engine = MetricsEngine()
        engine.update_scalar_metrics(123, np.array([10.0]))
        
        detector = StatisticalDetector(engine, threshold_z=-1.0)
        result = detector.evaluate(123, np.array([10.0]))
        
        assert "severity" in result


class TestStatisticalDetectorIntegration:
    """Integration tests with MetricsEngine."""

    def test_full_workflow(self):
        """Verify full detection workflow."""
        engine = MetricsEngine(alpha=0.3)
        
        for i in range(50):
            vector = np.array([
                float(i) + np.random.randn(),
                float(i * 2) + np.random.randn(),
                float(i * 3) + np.random.randn()
            ])
            engine.update_scalar_metrics(123, vector)
        
        detector = StatisticalDetector(engine, threshold_z=3.0)
        
        normal = np.array([25.0, 50.0, 75.0])
        result_normal = detector.evaluate(123, normal)
        
        assert "is_anomalous" in result_normal
        assert "euclidean_distance" in result_normal

        anomalous = np.array([1000.0, 1000.0, 1000.0])
        result_anom = detector.evaluate(123, anomalous)
        
        assert result_anom["is_anomalous"] is True

    def test_multiple_pids(self):
        """Verify multiple PIDs tracked separately."""
        engine = MetricsEngine()
        
        for pid in [100, 200, 300]:
            for _ in range(20):
                engine.update_scalar_metrics(pid, np.array([float(pid)]))
        
        detector = StatisticalDetector(engine)
        
        for pid in [100, 200, 300]:
            result = detector.evaluate(pid, np.array([float(pid)]))
            assert result["is_anomalous"] is False

    def test_ewma_integration(self):
        """Verify EWMA updates work with detector."""
        engine = MetricsEngine(alpha=0.3)
        
        engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
        
        for _ in range(10):
            engine.update_scalar_metrics(123, np.array([20.0, 20.0, 20.0]))
        
        detector = StatisticalDetector(engine)
        result = detector.evaluate(123, np.array([25.0, 25.0, 25.0]))
        
        assert "z_vector" in result


class TestStatisticalDetectorNgramIntegration:
    """Integration with n-gram functionality."""

    def test_ngram_with_statistical(self):
        """Verify ngram integration works."""
        engine = MetricsEngine(n_gram_size=3)
        
        for i in range(100):
            engine.update_ngram(123, i)
            engine.update_ngram(123, i + 1)
            engine.update_ngram(123, i + 2)
        
        detector = StatisticalDetector(engine)
        
        anomaly_score = engine.get_ngram_anomaly_score(123, (999, 1000, 1001))
        assert anomaly_score > 0.5