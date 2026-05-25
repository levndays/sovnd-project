"""Statistical anomaly detector (§2.2).

Uses Z-scores computed against an EWMA baseline (Exponentially
Weighted Moving Average) to flag metric vectors that deviate
significantly from the learned normal-behaviour profile.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.metrics.engine import MetricsEngine

from core.config import Settings, get_settings


class StatisticalDetector:
    """Per-process statistical anomaly detector.

    Parameters
    ----------
    engine : MetricsEngine
        The EWMA engine that maintains per-PID baselines.
    threshold_z : float
        Z-score above which a single metric component is
        considered anomalous (default from settings, typically 3.0).
    """

    def __init__(
        self,
        engine: MetricsEngine,
        settings: Settings | None = None,
    ):
        cfg = settings or get_settings()
        self._engine      = engine
        self.threshold_z  = cfg.z_threshold
        self._severe_z    = cfg.z_threshold_severe

    @property
    def engine(self) -> MetricsEngine:
        return self._engine

    # ── public API ───────────────────────────────────────────

    def evaluate(
        self, pid: int, current_vector: list[float]
    ) -> dict[str, Any]:
        """Score the current metric vector against the EWMA baseline.

        Returns
        -------
        dict with keys:
            pid, is_anomalous, max_z_score, z_vector,
            euclidean_distance, severity, ngram_anomaly
        """
        z_scores = self._engine.get_z_scores(pid, current_vector)
        if not z_scores:
            return self._no_data(pid)

        max_z = float(max(abs(z) for z in z_scores))
        anomalous = max_z > self.threshold_z

        p = self._engine.profiles.get(pid)
        mu = p.mu if p else current_vector
        distance = sum((c - m) ** 2 for c, m in zip(current_vector, mu, strict=False)) ** 0.5

        # n-gram anomaly (0..1): high when the latest syscall window
        # is rare against the per-PID baseline. See §2.1 (n-gram-tree).
        ngram_anomaly = float(self._engine.get_ngram_anomaly_score(pid))

        return {
            "pid":                pid,
            "is_anomalous":       anomalous,
            "max_z_score":        max_z,
            "z_vector":           z_scores,
            "euclidean_distance": float(distance),
            "severity":           self._severity(max_z),
            "ngram_anomaly":      ngram_anomaly,
        }

    # ── helpers ──────────────────────────────────────────────

    @staticmethod
    def _no_data(pid: int) -> dict[str, Any]:
        return {
            "pid":                pid,
            "is_anomalous":       False,
            "max_z_score":        0.0,
            "z_vector":           [],
            "euclidean_distance": 0.0,
            "severity":           "info",
            "ngram_anomaly":      0.0,
        }

    def _severity(self, z_score: float) -> str:
        if z_score >= self._severe_z:
            return "critical"
        if z_score >= self.threshold_z:
            return "warning"
        return "info"
