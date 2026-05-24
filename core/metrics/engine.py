import time
import logging
from typing import Dict, List, Tuple, Any, Optional
from collections import deque
from enum import IntEnum

logger = logging.getLogger(__name__)

class OpType(IntEnum):
    OPEN  = 1
    CLOSE = 2
    READ  = 3
    WRITE = 4

class FdType(IntEnum):
    FILE   = 1
    SOCKET = 2
    PIPE   = 3
    ANON   = 4
    UNKNOWN = 0

class MetricsEngine:
    """
    Computes the M(t) behavioural profile per §2.1.

    M(t) = (m1, m2_type_file, m2_type_socket, m2_type_pipe,
            m3_read_bps, m3_write_bps, m4_fd_count,
            m5_ngram_score)

    Uses EWMA (alpha=0.3) for adaptive baseline of scalar metrics
    and n-gram trees for syscall-op sequence anomaly detection.
    """

    OP_TYPES = {OpType.OPEN, OpType.CLOSE, OpType.READ, OpType.WRITE}
    N_FEATURES = 7      # dimensions in the profile vector
    N_HISTORY = 100      # sliding window for per-PID history

    def __init__(self, alpha: float = 0.3, n_gram_size: int = 3):
        self.alpha = alpha
        self.n_gram_size = n_gram_size

        # Per-PID state:  { pid: { "mu": [...], "sigma": [...],
        #   "window": deque of metric_snapshots,
        #   "ngram_buf": deque of op_type ints,
        #   "ngram_counts": { (1,2,3): count } } }
        self.profiles: Dict[int, Dict] = {}

    # ── public API ──────────────────────────────────────────────

    def update(self, event: Dict[str, Any]):
        """
        Process an eBPF event. Updates per-PID counters and,
        once per second, computes a metric snapshot and updates
        the EWMA baseline.
        """
        pid = event.get("pid")
        if pid is None:
            return

        op_type = event.get("op_type", 0)
        fd_type = event.get("fd_type", 0)

        self._ensure_profile(pid)
        prof = self.profiles[pid]

        # bump raw counters
        prof["raw_op_count"] += 1
        if op_type == OpType.OPEN:
            prof["raw_fd_open"] += 1
        elif op_type == OpType.CLOSE:
            prof["raw_fd_close"] += 1
        elif op_type == OpType.READ:
            prof["raw_read_bytes"] += event.get("bytes", 0)
        elif op_type == OpType.WRITE:
            prof["raw_write_bytes"] += event.get("bytes", 0)

        # track FD type distribution
        if fd_type == FdType.FILE:
            prof["raw_fd_type_file"] += 1
        elif fd_type == FdType.SOCKET:
            prof["raw_fd_type_socket"] += 1
        elif fd_type == FdType.PIPE:
            prof["raw_fd_type_pipe"] += 1

        # track FD count: open +1, close -1
        if op_type == OpType.OPEN:
            prof["fd_count"] += 1
        elif op_type == OpType.CLOSE and prof["fd_count"] > 0:
            prof["fd_count"] -= 1

        # n-gram buffer
        self._update_ngram(pid, op_type)

        # snapshot metrics every 1 second
        now = time.time()
        if now - prof["last_snapshot_ts"] >= 1.0:
            self._snapshot_and_update_ewma(pid, now)

    def get_current_vector(self, pid: int) -> List[float]:
        """
        Return the current metric vector for Z-score comparison.
        Uses the most recent snapshot.
        """
        if pid not in self.profiles:
            return [0.0] * self.N_FEATURES
        prof = self.profiles[pid]
        if prof["window"]:
            return list(prof["window"][-1])
        return list(prof.get("mu", [0.0] * self.N_FEATURES))

    def get_z_scores(self, pid: int, current_vector: List[float]) -> List[float]:
        if pid not in self.profiles:
            return [0.0] * len(current_vector)
        prof = self.profiles[pid]
        mu = prof.get("mu", [0.0] * len(current_vector))
        sigma = prof.get("sigma", [1.0] * len(current_vector))
        z_scores = []
        for i, (c, m, s) in enumerate(zip(current_vector, mu, sigma)):
            denom = s if s > 1e-9 else 1e-9
            z_scores.append((c - m) / denom)
        return z_scores

    def get_ngram_anomaly_score(self, pid: int) -> float:
        """
        Returns 1.0 – frequency of the most recent n-gram.
        Rare sequences → high score.
        """
        if pid not in self.profiles:
            return 1.0
        prof = self.profiles[pid]
        buf = prof["ngram_buf"]
        if len(buf) < self.n_gram_size:
            return 0.0
        ngram = tuple(buf)
        counts = prof["ngram_counts"]
        total = sum(counts.values())
        if total == 0:
            return 1.0
        freq = counts.get(ngram, 0) / total
        return 1.0 - freq

    # ── internals ───────────────────────────────────────────────

    def _ensure_profile(self, pid: int):
        if pid in self.profiles:
            return
        self.profiles[pid] = {
            "mu":              [0.0] * self.N_FEATURES,
            "sigma":           [1.0] * self.N_FEATURES,
            "window":          deque(maxlen=self.N_HISTORY),
            "ngram_buf":       deque(maxlen=self.n_gram_size),
            "ngram_counts":    {},
            "raw_op_count":    0,
            "raw_fd_open":     0,
            "raw_fd_close":    0,
            "raw_read_bytes":  0,
            "raw_write_bytes": 0,
            "raw_fd_type_file":  0,
            "raw_fd_type_socket":0,
            "raw_fd_type_pipe":  0,
            "fd_count":         0,
            "last_snapshot_ts": time.time(),
        }

    def _snapshot_and_update_ewma(self, pid: int, now: float):
        prof = self.profiles[pid]

        # build metric vector from accumulated raw counters
        # m1 = open + close churn rate
        m1 = prof["raw_fd_open"] + prof["raw_fd_close"]

        # m2 = FD type distribution (normalised)
        total_types = max(prof["raw_fd_type_file"] + prof["raw_fd_type_socket"] + prof["raw_fd_type_pipe"], 1)
        m2_file   = prof["raw_fd_type_file"]   / total_types
        m2_socket = prof["raw_fd_type_socket"]  / total_types
        m2_pipe   = prof["raw_fd_type_pipe"]    / total_types

        # m3 = I/O intensity (bytes/sec)
        m3_read  = prof["raw_read_bytes"]
        m3_write = prof["raw_write_bytes"]

        # m4 = concurrent FD count (snapshot)
        m4 = prof["fd_count"]

        vec = [float(m1), m2_file, m2_socket, m2_pipe,
               float(m3_read), float(m3_write), float(m4)]

        prof["window"].append(vec)

        # EWMA update for mu and sigma
        old_mu = prof["mu"]
        new_mu = [self.alpha * v + (1.0 - self.alpha) * old for v, old in zip(vec, old_mu)]
        prof["mu"] = new_mu

        for i in range(self.N_FEATURES):
            delta = vec[i] - old_mu[i]
            old_s = prof["sigma"][i]
            prof["sigma"][i] = ((1.0 - self.alpha) * (old_s ** 2 + self.alpha * delta ** 2)) ** 0.5
            if prof["sigma"][i] < 0.01:
                prof["sigma"][i] = 0.01

        # reset raw counters for next second
        prof["raw_op_count"]    = 0
        prof["raw_fd_open"]     = 0
        prof["raw_fd_close"]    = 0
        prof["raw_read_bytes"]  = 0
        prof["raw_write_bytes"] = 0
        prof["raw_fd_type_file"]   = 0
        prof["raw_fd_type_socket"] = 0
        prof["raw_fd_type_pipe"]   = 0
        prof["last_snapshot_ts"] = now

    def _update_ngram(self, pid: int, op_type: int):
        prof = self.profiles[pid]
        buf = prof["ngram_buf"]
        buf.append(op_type)
        if len(buf) == self.n_gram_size:
            ngram = tuple(buf)
            prof["ngram_counts"][ngram] = prof["ngram_counts"].get(ngram, 0) + 1
