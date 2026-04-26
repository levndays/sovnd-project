import pytest
import numpy as np
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path
from collections import deque

SRC_DIR = Path(__file__).parent.parent / "src"


class TestMetricsEngineInit:
    """Tests for MetricsEngine initialization."""

    def test_engine_file_exists(self):
        """Verify MetricsEngine exists."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        assert MetricsEngine is not None

    def test_default_alpha(self):
        """Verify default alpha is 0.3."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        assert engine.alpha == 0.3

    def test_custom_alpha(self):
        """Verify custom alpha is set correctly."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine(alpha=0.5)
        assert engine.alpha == 0.5

    def test_default_n_gram_size(self):
        """Verify default n_gram_size is 3."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        assert engine.n_gram_size == 3

    def test_custom_n_gram_size(self):
        """Verify custom n_gram_size is set correctly."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine(n_gram_size=5)
        assert engine.n_gram_size == 5

    def test_profiles_initially_empty(self):
        """Verify profiles dict is empty on init."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        assert engine.profiles == {}


class TestMetricsEngineUpdateScalar:
    """Tests for update_scalar_metrics method."""

    def test_first_update_creates_profile(self):
        """Verify first update creates a new profile."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        vector = np.array([1.0, 2.0, 3.0])
        engine.update_scalar_metrics(123, vector)
        assert 123 in engine.profiles

    def test_first_update_sets_mu_to_vector(self):
        """Verify first update sets mu to the current vector."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        vector = np.array([1.0, 2.0, 3.0])
        engine.update_scalar_metrics(123, vector)
        np.testing.assert_array_almost_equal(engine.profiles[123]["mu"], vector)

    def test_first_update_sets_sigma_to_ones(self):
        """Verify first update sets sigma to ones."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        vector = np.array([1.0, 2.0, 3.0])
        engine.update_scalar_metrics(123, vector)
        np.testing.assert_array_almost_equal(engine.profiles[123]["sigma"], np.ones(3))

    def test_first_update_creates_history_deque(self):
        """Verify history deque is created."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        vector = np.array([1.0, 2.0, 3.0])
        engine.update_scalar_metrics(123, vector)
        assert isinstance(engine.profiles[123]["history"], deque)

    def test_first_update_creates_ngram_buffer(self):
        """Verify ngram_buffer deque is created."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        vector = np.array([1.0, 2.0, 3.0])
        engine.update_scalar_metrics(123, vector)
        assert isinstance(engine.profiles[123]["ngram_buffer"], deque)

    def test_first_update_creates_ngram_counts(self):
        """Verify ngram_counts dict is created."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        vector = np.array([1.0, 2.0, 3.0])
        engine.update_scalar_metrics(123, vector)
        assert engine.profiles[123]["ngram_counts"] == {}

    def test_ewma_update_formula(self):
        """Verify EWMA update: mu = alpha * current + (1-alpha) * old_mu."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine(alpha=0.3)
        
        old_vector = np.array([10.0, 20.0, 30.0])
        engine.update_scalar_metrics(123, old_vector)
        
        new_vector = np.array([20.0, 40.0, 60.0])
        engine.update_scalar_metrics(123, new_vector)
        
        expected_mu = 0.3 * new_vector + 0.7 * old_vector
        np.testing.assert_array_almost_equal(engine.profiles[123]["mu"], expected_mu)

    def test_ewma_with_zero_alpha(self):
        """Verify EWMA with alpha=0 (no update)."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine(alpha=0.0)
        
        old_vector = np.array([10.0, 20.0, 30.0])
        engine.update_scalar_metrics(123, old_vector)
        
        new_vector = np.array([20.0, 40.0, 60.0])
        engine.update_scalar_metrics(123, new_vector)
        
        np.testing.assert_array_almost_equal(engine.profiles[123]["mu"], old_vector)

    def test_ewma_with_one_alpha(self):
        """Verify EWMA with alpha=1 (full update to current)."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine(alpha=1.0)
        
        old_vector = np.array([10.0, 20.0, 30.0])
        engine.update_scalar_metrics(123, old_vector)
        
        new_vector = np.array([20.0, 40.0, 60.0])
        engine.update_scalar_metrics(123, new_vector)
        
        np.testing.assert_array_almost_equal(engine.profiles[123]["mu"], new_vector)

    def test_multiple_updates_append_to_history(self):
        """Verify multiple updates append to history."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        for i in range(5):
            engine.update_scalar_metrics(123, np.array([float(i)]))
        
        assert len(engine.profiles[123]["history"]) >= 5

    def test_history_maxlen_enforced(self):
        """Verify history respects maxlen."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        for i in range(150):
            engine.update_scalar_metrics(123, np.array([float(i)]))
        
        assert len(engine.profiles[123]["history"]) == 100

    def test_update_with_different_pid(self):
        """Verify updates for different PIDs are separate."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        engine.update_scalar_metrics(100, np.array([1.0]))
        engine.update_scalar_metrics(200, np.array([2.0]))
        
        assert engine.profiles[100]["mu"][0] == 1.0
        assert engine.profiles[200]["mu"][0] == 2.0


class TestMetricsEngineUpdateNgram:
    """Tests for update_ngram method."""

    def test_ngram_update_creates_profile_if_missing(self):
        """Verify ngram update creates profile if missing."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine(n_gram_size=3)
        engine.update_ngram(999, 257)
        assert 999 in engine.profiles

    def test_ngram_single_syscall_no_count(self):
        """Verify single syscall doesn't create ngram until buffer full."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine(n_gram_size=3)
        
        engine.update_ngram(123, 257)
        
        assert len(engine.profiles[123]["ngram_counts"]) == 0

    def test_ngram_full_buffer_creates_count(self):
        """Verify full buffer creates ngram count."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine(n_gram_size=3)
        
        engine.update_ngram(123, 257)
        engine.update_ngram(123, 258)
        engine.update_ngram(123, 259)
        
        assert (257, 258, 259) in engine.profiles[123]["ngram_counts"]

    def test_ngram_increments_count(self):
        """Verify repeated ngram increments count."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine(n_gram_size=2)
        
        engine.update_ngram(123, 257)
        engine.update_ngram(123, 258)
        engine.update_ngram(123, 257)
        engine.update_ngram(123, 258)
        
        assert engine.profiles[123]["ngram_counts"][(257, 258)] == 2

    def test_ngram_buffer_slides(self):
        """Verify ngram buffer slides correctly."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine(n_gram_size=2)
        
        engine.update_ngram(123, 1)
        engine.update_ngram(123, 2)
        assert (1, 2) in engine.profiles[123]["ngram_counts"]
        
        engine.update_ngram(123, 3)
        assert (2, 3) in engine.profiles[123]["ngram_counts"]

    def test_ngram_size_one(self):
        """Verify ngram with size 1."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine(n_gram_size=1)
        
        engine.update_ngram(123, 257)
        
        assert (257,) in engine.profiles[123]["ngram_counts"]

    def test_different_pids_have_separate_ngrams(self):
        """Verify different PIDs have separate ngram buffers."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine(n_gram_size=2)
        
        engine.update_ngram(100, 1)
        engine.update_ngram(100, 2)
        
        engine.update_ngram(200, 3)
        engine.update_ngram(200, 4)
        
        assert (1, 2) in engine.profiles[100]["ngram_counts"]
        assert (3, 4) in engine.profiles[200]["ngram_counts"]


class TestMetricsEngineZScores:
    """Tests for get_z_scores method."""

    def test_unknown_pid_returns_zeros(self):
        """Verify unknown PID returns zeros."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        result = engine.get_z_scores(999, np.array([1.0, 2.0, 3.0]))
        
        np.testing.assert_array_almost_equal(result, np.zeros(3))

    def test_z_score_calculation(self):
        """Verify z-score formula: (current - mu) / sigma."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
        
        result = engine.get_z_scores(123, np.array([13.0, 10.0, 7.0]))
        
        np.testing.assert_array_almost_equal(result, np.array([3.0, 0.0, -3.0]))

    def test_zero_sigma_uses_epsilon(self):
        """Verify zero sigma uses 1e-6 epsilon."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
        engine.profiles[123]["sigma"] = np.array([0.0, 0.0, 0.0])
        
        result = engine.get_z_scores(123, np.array([20.0, 20.0, 20.0]))
        
        np.testing.assert_array_almost_equal(result, np.array([10000000.0, 10000000.0, 10000000.0]))

    def test_negative_z_scores(self):
        """Verify negative z-scores are calculated correctly."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        engine.update_scalar_metrics(123, np.array([100.0]))
        
        result = engine.get_z_scores(123, np.array([50.0]))
        
        assert result[0] < 0

    def test_exact_match_z_score_zero(self):
        """Verify exact match to mu gives z-score of 0."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        engine.update_scalar_metrics(123, np.array([50.0]))
        
        result = engine.get_z_scores(123, np.array([50.0]))
        
        np.testing.assert_array_almost_equal(result, np.array([0.0]))


class TestMetricsEngineNgramAnomalyScore:
    """Tests for get_ngram_anomaly_score method."""

    def test_unknown_pid_returns_one(self):
        """Verify unknown PID returns 1.0 (max anomaly)."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        result = engine.get_ngram_anomaly_score(999, (1, 2, 3))
        
        assert result == 1.0

    def test_zero_total_returns_one(self):
        """Verify zero total ngram count returns 1.0."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        engine.update_scalar_metrics(123, np.array([1.0]))
        
        result = engine.get_ngram_anomaly_score(123, (1, 2, 3))
        
        assert result == 1.0

    def test_rare_sequence_high_score(self):
        """Verify rare sequence returns high anomaly score."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine(n_gram_size=2)
        
        for _ in range(100):
            engine.update_ngram(123, 1)
            engine.update_ngram(123, 2)
        
        engine.update_ngram(123, 3)
        engine.update_ngram(123, 4)
        
        result = engine.get_ngram_anomaly_score(123, (3, 4))
        
        assert result >= 0.9

    def test_common_sequence_high_rare_score(self):
        """Verify common sequences have lower anomaly score than rare ones."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine(n_gram_size=2)
        
        for _ in range(100):
            engine.update_ngram(123, 1)
            engine.update_ngram(123, 2)
        
        # (1,2) is seen many times, (3,4) is seen only once
        result_common = engine.get_ngram_anomaly_score(123, (1, 2))
        result_rare = engine.get_ngram_anomaly_score(123, (3, 4))
        
        assert result_common < result_rare

    def test_perfect_match_returns_zero(self):
        """Verify sequence with 100% frequency returns 0."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        engine.update_scalar_metrics(123, np.array([1.0]))
        # Only one unique ngram with 100% frequency
        engine.profiles[123]["ngram_counts"][(1, 2, 3)] = 1
        
        result = engine.get_ngram_anomaly_score(123, (1, 2, 3))
        
        assert result == 0.0


class TestMetricsEngineEdgeCases:
    """Edge case tests for MetricsEngine."""

    def test_empty_vector(self):
        """Verify empty vector handling."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        engine.update_scalar_metrics(123, np.array([]))
        
        assert 123 in engine.profiles
        assert len(engine.profiles[123]["mu"]) == 0

    def test_single_element_vector(self):
        """Verify single element vector."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        engine.update_scalar_metrics(123, np.array([42.0]))
        
        assert engine.profiles[123]["mu"][0] == 42.0

    def test_large_vector(self):
        """Verify large vector dimension."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        large_vector = np.random.rand(1000)
        engine.update_scalar_metrics(123, large_vector)
        
        assert len(engine.profiles[123]["mu"]) == 1000

    def test_negative_values(self):
        """Verify negative values are handled."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        engine.update_scalar_metrics(123, np.array([-10.0, -20.0]))
        
        assert engine.profiles[123]["mu"][0] == -10.0

    def test_mixed_positive_negative(self):
        """Verify mixed positive/negative values."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        engine.update_scalar_metrics(123, np.array([-5.0, 0.0, 5.0]))
        
        np.testing.assert_array_almost_equal(
            engine.profiles[123]["mu"], 
            np.array([-5.0, 0.0, 5.0])
        )

    def test_float32_array(self):
        """Verify float32 array is converted to float."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        vector = np.array([1.0, 2.0], dtype=np.float32)
        engine.update_scalar_metrics(123, vector)
        
        assert engine.profiles[123]["mu"].dtype == np.float64

    def test_integer_array(self):
        """Verify integer array is converted to float."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        vector = np.array([1, 2, 3], dtype=np.int32)
        engine.update_scalar_metrics(123, vector)
        
        assert engine.profiles[123]["mu"].dtype == np.float64


class TestMetricsEngineIntegration:
    """Integration tests for MetricsEngine."""

    def test_full_workflow(self):
        """Verify full detection workflow."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine(alpha=0.3, n_gram_size=2)
        
        for i in range(20):
            vector = np.array([float(i), float(i*2), float(i*3)])
            engine.update_scalar_metrics(123, vector)
            engine.update_ngram(123, 257 + i)
        
        test_vector = np.array([25.0, 50.0, 75.0])
        z_scores = engine.get_z_scores(123, test_vector)
        
        assert z_scores.shape == (3,)
        
        anomaly = engine.get_ngram_anomaly_score(123, (275, 276))
        assert 0.0 <= anomaly <= 1.0

    def test_multiple_processes(self):
        """Verify multiple processes tracking."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from src.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        
        for pid in [100, 200, 300]:
            for _ in range(10):
                engine.update_scalar_metrics(pid, np.array([float(pid)]))
        
        for pid in [100, 200, 300]:
            assert pid in engine.profiles
            z = engine.get_z_scores(pid, np.array([float(pid)]))
            np.testing.assert_array_almost_equal(z, np.array([0.0]))