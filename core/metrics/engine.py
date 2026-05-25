"""EWMA-based behavioural metrics engine (§2.1).

Maintains per-PID ``M(t) = (m₁, …, m₇)`` profiles:
    m₁      — fd churn rate (open + close events / sec)
    m₂_file — fraction of operations on regular files
    m₂_sock — fraction of operations on sockets
    m₂_pipe — fraction of operations on pipes
    m₃_read — bytes read / sec
    m₃_wrt  — bytes written / sec
    m₄      — concurrent open-FD count (snapshot)

N-gram anomaly scoring (§2.1 n-gram-tree) tracks rare
syscall-operation sequences.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from enum import IntEnum
from typing import Any

from core.config import Settings, get_settings

logger = logging.getLogger(__name__)


# ── domain enums ─────────────────────────────────────────────

class OpType(IntEnum):
    OPEN  = 1
    CLOSE = 2
    READ  = 3
    WRITE = 4


class FdType(IntEnum):
    FILE    = 1
    SOCKET  = 2
    PIPE    = 3
    ANON    = 4
    UNKNOWN = 0


# ── per-PID profile state ────────────────────────────────────

class _Profile:
    __slots__ = (
        "mu", "sigma", "window",
        "ngram_buf", "ngram_counts",
        "raw_op", "raw_open", "raw_close",
        "raw_rbytes", "raw_wbytes",
        "raw_ft_file", "raw_ft_socket", "raw_ft_pipe",
        "fd_cnt", "last_snap",
    )

    def __init__(self, n_features: int, ngram_n: int, history_len: int):
        self.mu           = [0.0] * n_features
        self.sigma        = [1.0] * n_features
        self.window:      deque[list[float]] = deque(maxlen=history_len)
        self.ngram_buf:   deque[int]         = deque(maxlen=ngram_n)
        self.ngram_counts: dict[tuple[int, ...], int] = {}

        self.raw_op       = 0
        self.raw_open     = 0
        self.raw_close    = 0
        self.raw_rbytes   = 0
        self.raw_wbytes   = 0
        self.raw_ft_file  = 0
        self.raw_ft_socket = 0
        self.raw_ft_pipe  = 0
        self.fd_cnt       = 0
        self.last_snap    = time.time()


# ── engine ───────────────────────────────────────────────────

class MetricsEngine:
    """Per-process metrics engine with EWMA baselines."""

    N_FEATURES = 7

    def __init__(self, settings: Settings | None = None):
        cfg = settings or get_settings()
        self.alpha       = cfg.ewma_alpha
        self.n_gram_size = cfg.n_gram_size
        self._hist_len   = cfg.history_maxlen
        self._profiles: dict[int, _Profile] = {}

    @property
    def profiles(self) -> dict[int, _Profile]:
        return self._profiles

    # ── public API ───────────────────────────────────────────

    def update(self, event: dict[str, Any]) -> None:
        """Ingest a single eBPF event and update counters.

        Once per second the accumulated counters are snapshotted
        into an ``M(t)`` vector and the EWMA baseline is updated.
        """
        pid = event.get("pid")
        if pid is None:
            return

        op    = event.get("op_type", 0)
        fd_ty = event.get("fd_type", 0)

        p = self._ensure(pid)

        # bump raw counters
        p.raw_op += 1
        if op == OpType.OPEN:
            p.raw_open += 1
            p.fd_cnt   += 1
        elif op == OpType.CLOSE:
            p.raw_close += 1
            if p.fd_cnt > 0:
                p.fd_cnt -= 1
        elif op == OpType.READ:
            p.raw_rbytes += event.get("bytes", 0)
        elif op == OpType.WRITE:
            p.raw_wbytes += event.get("bytes", 0)

        # fd-type distribution
        if fd_ty == FdType.FILE:
            p.raw_ft_file += 1
        elif fd_ty == FdType.SOCKET:
            p.raw_ft_socket += 1
        elif fd_ty == FdType.PIPE:
            p.raw_ft_pipe += 1

        # n-gram buffer
        self._push_ngram(pid, op)

        # periodic snapshot
        now = time.time()
        if now - p.last_snap >= 1.0:
            self._snapshot(pid, now)

    def get_current_vector(self, pid: int) -> list[float]:
        """Return the most recent metric-snapshot vector."""
        p = self._profiles.get(pid)
        if p and p.window:
            return list(p.window[-1])
        if p:
            return list(p.mu)
        return [0.0] * self.N_FEATURES

    def get_z_scores(self, pid: int, vec: list[float]) -> list[float]:
        """Compute per-component Z-scores against the EWMA baseline."""
        p = self._profiles.get(pid)
        if not p:
            return [0.0] * len(vec)
        z = []
        for v, m, s in zip(vec, p.mu, p.sigma, strict=False):
            denom = s if s > 1e-9 else 1e-9
            z.append((v - m) / denom)
        return z

    def get_ngram_anomaly_score(self, pid: int) -> float:
        """Inverse-frequency score: rare n-grams → high anomaly."""
        p = self._profiles.get(pid)
        if not p or len(p.ngram_buf) < self.n_gram_size:
            return 0.0
        ngram = tuple(p.ngram_buf)
        total = sum(p.ngram_counts.values())
        if total == 0:
            return 1.0
        freq = p.ngram_counts.get(ngram, 0) / total
        return 1.0 - freq

    # ── internals ─────────────────────────────────────────────

    def _ensure(self, pid: int) -> _Profile:
        if pid not in self._profiles:
            self._profiles[pid] = _Profile(
                n_features=self.N_FEATURES,
                ngram_n=self.n_gram_size,
                history_len=self._hist_len,
            )
        return self._profiles[pid]

    def _push_ngram(self, pid: int, op: int) -> None:
        p = self._profiles[pid]
        p.ngram_buf.append(op)
        if len(p.ngram_buf) == self.n_gram_size:
            ngram = tuple(p.ngram_buf)
            p.ngram_counts[ngram] = p.ngram_counts.get(ngram, 0) + 1

    def _snapshot(self, pid: int, now: float) -> None:
        p = self._profiles[pid]

        # build M(t) vector
        m1       = float(p.raw_open + p.raw_close)
        denom_ty = max(p.raw_ft_file + p.raw_ft_socket + p.raw_ft_pipe, 1)
        m2_file  = p.raw_ft_file   / denom_ty
        m2_sock  = p.raw_ft_socket / denom_ty
        m2_pipe  = p.raw_ft_pipe   / denom_ty
        m3_read  = float(p.raw_rbytes)
        m3_wrt   = float(p.raw_wbytes)
        m4       = float(p.fd_cnt)

        vec = [m1, m2_file, m2_sock, m2_pipe, m3_read, m3_wrt, m4]
        p.window.append(vec)

        # EWMA update
        old_mu = p.mu
        a = self.alpha
        new_mu = [a * v + (1.0 - a) * o for v, o in zip(vec, old_mu, strict=False)]
        p.mu = new_mu

        for i in range(self.N_FEATURES):
            delta = vec[i] - old_mu[i]
            old_s = p.sigma[i]
            new_s = ((1.0 - a) * (old_s ** 2 + a * delta ** 2)) ** 0.5
            p.sigma[i] = max(new_s, 0.01)

        # reset accumulator counters
        p.raw_op       = 0
        p.raw_open     = 0
        p.raw_close    = 0
        p.raw_rbytes   = 0
        p.raw_wbytes   = 0
        p.raw_ft_file  = 0
        p.raw_ft_socket = 0
        p.raw_ft_pipe  = 0
        p.last_snap    = now
