import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class StatisticalDetector:
    """
    Statistical anomaly detector per §2.2.

    Computes Z-scores for the current metric vector M(t) against
    the EWMA baseline (mu, sigma).  An anomaly is flagged when
    |z_max| >= threshold_z (default 3.0).

    Returns:
        is_anomalous, max_z_score, z_vector, euclidean_distance,
        severity (info / warning / critical)
    """

    def __init__(self, engine, threshold_z: float = 3.0):
        self.engine = engine
        self.threshold_z = threshold_z

    def evaluate(self, pid: int, current_vector: List[float]) -> Dict[str, Any]:
        z_scores = self.engine.get_z_scores(pid, current_vector)
        if not z_scores:
            return self._no_data(pid)

        max_z = max(abs(z) for z in z_scores)
        is_anomalous = max_z > self.threshold_z

        prof = self.engine.profiles.get(pid, {})
        mu = prof.get("mu", current_vector)
        distance = sum((c - m) ** 2 for c, m in zip(current_vector, mu)) ** 0.5

        return {
            "pid":              pid,
            "is_anomalous":     bool(is_anomalous),
            "max_z_score":      float(max_z),
            "z_vector":         [float(z) for z in z_scores],
            "euclidean_distance": float(distance),
            "severity":         self._map_to_severity(max_z),
        }

    @staticmethod
    def _no_data(pid: int) -> Dict[str, Any]:
        return {
            "pid": pid, "is_anomalous": False,
            "max_z_score": 0.0, "z_vector": [],
            "euclidean_distance": 0.0, "severity": "info",
        }

    def _map_to_severity(self, z_score: float) -> str:
        if z_score < self.threshold_z:
            return "info"
        if z_score >= self.threshold_z * 2:
            return "critical"
        return "warning"
