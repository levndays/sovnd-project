import pytest
import time
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).parent.parent.parent


class TestMetricsEngineInit:
    def test_engine_imports(self):
        import sys
        sys.path.insert(0, str(ROOT_DIR))
        from core.metrics.engine import MetricsEngine
        assert MetricsEngine is not None

    def test_default_alpha(self):
        import sys
        sys.path.insert(0, str(ROOT_DIR))
        from core.metrics.engine import MetricsEngine
        assert MetricsEngine().alpha == 0.3

    def test_default_n_gram_size(self):
        import sys
        sys.path.insert(0, str(ROOT_DIR))
        from core.metrics.engine import MetricsEngine
        assert MetricsEngine().n_gram_size == 3

    def test_profiles_empty_on_init(self):
        import sys
        sys.path.insert(0, str(ROOT_DIR))
        from core.metrics.engine import MetricsEngine
        assert MetricsEngine().profiles == {}


class TestMetricsUpdate:
    def make_event(self, pid=100, op_type=1, fd_type=1, fd=10, bytes=0, filename="/tmp/x"):
        return {"pid": pid, "op_type": op_type, "fd_type": fd_type,
                "fd": fd, "bytes": bytes, "filename": filename}

    def test_update_creates_profile(self):
        import sys
        sys.path.insert(0, str(ROOT_DIR))
        from core.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        engine.update(self.make_event(pid=42))
        assert 42 in engine.profiles

    def test_update_tracks_open_close_counts(self):
        import sys
        sys.path.insert(0, str(ROOT_DIR))
        from core.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        engine.update(self.make_event(pid=1, op_type=1))  # OPEN
        engine.update(self.make_event(pid=1, op_type=2))  # CLOSE
        engine.update(self.make_event(pid=1, op_type=1))
        engine.update(self.make_event(pid=1, op_type=1))
        prof = engine.profiles[1]
        assert prof["raw_fd_open"] == 3
        assert prof["raw_fd_close"] == 1

    def test_update_tracks_fd_count_m4(self):
        import sys
        sys.path.insert(0, str(ROOT_DIR))
        from core.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        engine.update(self.make_event(pid=1, op_type=1))  # open
        engine.update(self.make_event(pid=1, op_type=1))  # open
        engine.update(self.make_event(pid=1, op_type=2))  # close
        assert engine.profiles[1]["fd_count"] == 1

    def test_update_tracks_read_write_bytes_m3(self):
        import sys
        sys.path.insert(0, str(ROOT_DIR))
        from core.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        engine.update(self.make_event(pid=1, op_type=3, bytes=1024))  # READ
        engine.update(self.make_event(pid=1, op_type=4, bytes=512))   # WRITE
        assert engine.profiles[1]["raw_read_bytes"] == 1024
        assert engine.profiles[1]["raw_write_bytes"] == 512

    def test_update_tracks_fd_type_distribution_m2(self):
        import sys
        sys.path.insert(0, str(ROOT_DIR))
        from core.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        engine.update(self.make_event(pid=1, op_type=1, fd_type=1))  # file
        engine.update(self.make_event(pid=1, op_type=1, fd_type=1))
        engine.update(self.make_event(pid=1, op_type=1, fd_type=2))  # socket
        assert engine.profiles[1]["raw_fd_type_file"] == 2
        assert engine.profiles[1]["raw_fd_type_socket"] == 1

    def test_multiple_pids_independent(self):
        import sys
        sys.path.insert(0, str(ROOT_DIR))
        from core.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        engine.update(self.make_event(pid=10))
        engine.update(self.make_event(pid=20))
        engine.update(self.make_event(pid=10))
        assert engine.profiles[10]["raw_fd_open"] == 2
        assert engine.profiles[20]["raw_fd_open"] == 1


class TestEWMASnapshot:
    def make_event(self, pid=100, op_type=1, **kw):
        return {"pid": pid, "op_type": op_type, "fd_type": 1, "fd": 10,
                "bytes": 0, "filename": "/tmp/x", **kw}

    def test_snapshot_triggers_after_one_second(self):
        import sys
        sys.path.insert(0, str(ROOT_DIR))
        from core.metrics.engine import MetricsEngine
        engine = MetricsEngine(alpha=1.0)  # alpha=1 → mu = latest vector
        base = time.time()
        with patch("time.time", side_effect=[base, base, base + 1.1]):
            engine.update(self.make_event(pid=1, op_type=1))
            engine.update(self.make_event(pid=1, op_type=1))
            engine.update(self.make_event(pid=1, op_type=1))  # triggers snapshot
        assert len(engine.profiles[1]["window"]) >= 1

    def test_ewma_mu_converges(self):
        import sys
        sys.path.insert(0, str(ROOT_DIR))
        from core.metrics.engine import MetricsEngine
        engine = MetricsEngine(alpha=0.5)
        pid = 99
        base = time.time()
        for i in range(20):
            t = base + i * 1.1
            with patch("time.time", return_value=t):
                engine.update(self.make_event(pid=pid, op_type=1))
        mu = engine.profiles[pid]["mu"]
        assert any(v > 0 for v in mu)

    def test_get_current_vector_returns_list(self):
        import sys
        sys.path.insert(0, str(ROOT_DIR))
        from core.metrics.engine import MetricsEngine
        engine = MetricsEngine()
        engine.update(self.make_event(pid=1))
        vec = engine.get_current_vector(1)
        assert isinstance(vec, list)
        assert len(vec) == 7

    def test_z_scores_returns_list(self):
        import sys
        sys.path.insert(0, str(ROOT_DIR))
        from core.metrics.engine import MetricsEngine
        engine = MetricsEngine(alpha=1.0)
        base = time.time()
        with patch("time.time", side_effect=[base, base + 1.1]):
            engine.update(self.make_event(pid=1, op_type=1))
            engine.update(self.make_event(pid=1, op_type=1))
        z = engine.get_z_scores(1, engine.get_current_vector(1))
        assert isinstance(z, list)
        assert len(z) == 7


class TestNGram:
    def test_ngram_scoring(self):
        import sys
        sys.path.insert(0, str(ROOT_DIR))
        from core.metrics.engine import MetricsEngine, OpType
        engine = MetricsEngine(n_gram_size=3)
        # Build a common trigram
        for _ in range(50):
            engine.update({"pid": 1, "op_type": OpType.OPEN, "fd": 1,
                           "fd_type": 1, "bytes": 0, "filename": "/x"})
            engine.update({"pid": 1, "op_type": OpType.READ, "fd": 1,
                           "fd_type": 1, "bytes": 0, "filename": "/x"})
            engine.update({"pid": 1, "op_type": OpType.CLOSE, "fd": 1,
                           "fd_type": 1, "bytes": 0, "filename": "/x"})
        score = engine.get_ngram_anomaly_score(1)
        assert 0.0 <= score <= 1.0
