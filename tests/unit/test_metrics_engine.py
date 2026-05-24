import pytest
import time
from unittest.mock import patch
from core.config import Settings
from core.metrics.engine import MetricsEngine, OpType


class TestMetricsEngineInit:
    def test_default_alpha(self):
        assert MetricsEngine().alpha == 0.3

    def test_default_n_gram_size(self):
        assert MetricsEngine().n_gram_size == 3

    def test_profiles_empty_on_init(self):
        assert MetricsEngine().profiles == {}


class TestMetricsUpdate:
    @staticmethod
    def make_event(pid=100, op_type=1, fd_type=1, fd=10, bytes=0, filename="/tmp/x"):
        return {"pid": pid, "op_type": op_type, "fd_type": fd_type,
                "fd": fd, "bytes": bytes, "filename": filename}

    def test_update_creates_profile(self):
        engine = MetricsEngine()
        engine.update(self.make_event(pid=42))
        assert 42 in engine.profiles

    def test_update_tracks_open_close_counts(self):
        engine = MetricsEngine()
        engine.update(self.make_event(pid=1, op_type=1))  # OPEN
        engine.update(self.make_event(pid=1, op_type=2))  # CLOSE
        engine.update(self.make_event(pid=1, op_type=1))
        engine.update(self.make_event(pid=1, op_type=1))
        prof = engine.profiles[1]
        assert prof.raw_open == 3
        assert prof.raw_close == 1

    def test_update_tracks_fd_count_m4(self):
        engine = MetricsEngine()
        engine.update(self.make_event(pid=1, op_type=1))  # open
        engine.update(self.make_event(pid=1, op_type=1))  # open
        engine.update(self.make_event(pid=1, op_type=2))  # close
        assert engine.profiles[1].fd_cnt == 1

    def test_update_tracks_read_write_bytes_m3(self):
        engine = MetricsEngine()
        engine.update(self.make_event(pid=1, op_type=3, bytes=1024))  # READ
        engine.update(self.make_event(pid=1, op_type=4, bytes=512))   # WRITE
        assert engine.profiles[1].raw_rbytes == 1024
        assert engine.profiles[1].raw_wbytes == 512

    def test_update_tracks_fd_type_distribution_m2(self):
        engine = MetricsEngine()
        engine.update(self.make_event(pid=1, op_type=1, fd_type=1))  # file
        engine.update(self.make_event(pid=1, op_type=1, fd_type=1))
        engine.update(self.make_event(pid=1, op_type=1, fd_type=2))  # socket
        assert engine.profiles[1].raw_ft_file == 2
        assert engine.profiles[1].raw_ft_socket == 1

    def test_multiple_pids_independent(self):
        engine = MetricsEngine()
        engine.update(self.make_event(pid=10))
        engine.update(self.make_event(pid=20))
        engine.update(self.make_event(pid=10))
        assert engine.profiles[10].raw_open == 2
        assert engine.profiles[20].raw_open == 1


class TestEWMASnapshot:
    @staticmethod
    def make_event(pid=100, op_type=1, **kw):
        return {"pid": pid, "op_type": op_type, "fd_type": 1, "fd": 10,
                "bytes": 0, "filename": "/tmp/x", **kw}

    def test_snapshot_triggers_after_one_second(self):
        engine = MetricsEngine(settings=Settings(ewma_alpha=1.0))
        base = time.time()
        with patch("time.time", side_effect=[base, base, base + 1.1]):
            engine.update(self.make_event(pid=1, op_type=1))
            engine.update(self.make_event(pid=1, op_type=1))
            engine.update(self.make_event(pid=1, op_type=1))
        assert len(engine.profiles[1].window) >= 1

    def test_ewma_mu_converges(self):
        engine = MetricsEngine(settings=Settings(ewma_alpha=0.5))
        pid = 99
        base = time.time()
        for i in range(20):
            t = base + i * 1.1
            with patch("time.time", return_value=t):
                engine.update(self.make_event(pid=pid, op_type=1))
        mu = engine.profiles[pid].mu
        assert any(v > 0 for v in mu)

    def test_get_current_vector_returns_list(self):
        engine = MetricsEngine()
        engine.update(self.make_event(pid=1))
        vec = engine.get_current_vector(1)
        assert isinstance(vec, list)
        assert len(vec) == 7

    def test_z_scores_returns_list(self):
        engine = MetricsEngine(settings=Settings(ewma_alpha=1.0))
        base = time.time()
        with patch("time.time", side_effect=[base, base + 1.1]):
            engine.update(self.make_event(pid=1, op_type=1))
            engine.update(self.make_event(pid=1, op_type=1))
        z = engine.get_z_scores(1, engine.get_current_vector(1))
        assert isinstance(z, list)
        assert len(z) == 7


class TestNGram:
    def test_ngram_scoring(self):
        engine = MetricsEngine(settings=Settings(n_gram_size=3))
        for _ in range(50):
            engine.update({"pid": 1, "op_type": OpType.OPEN, "fd": 1,
                           "fd_type": 1, "bytes": 0, "filename": "/x"})
            engine.update({"pid": 1, "op_type": OpType.READ, "fd": 1,
                           "fd_type": 1, "bytes": 0, "filename": "/x"})
            engine.update({"pid": 1, "op_type": OpType.CLOSE, "fd": 1,
                           "fd_type": 1, "bytes": 0, "filename": "/x"})
        score = engine.get_ngram_anomaly_score(1)
        assert 0.0 <= score <= 1.0
