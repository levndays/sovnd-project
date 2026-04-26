import numpy as np
import logging
from typing import Dict, Optional, List
from src.metrics.engine import MetricsEngine

logger = logging.getLogger(__name__)

class StatisticalDetector:
    """
    Implements the Statistical Module from Section 2.2.
    Evaluates process behavior based on Z-scores and vector distances.
    """
    
    def __init__(self, engine: MetricsEngine, threshold_z: float = 3.0):
        self.engine = engine
        self.threshold_z = threshold_z

    def evaluate(self, pid: int, current_metrics: np.ndarray) -> Dict[str, Any]:
        """
        Analyzes the current metrics vector for a PID.
        
        Returns:
            A report containing anomaly status and specific scores.
        """
        z_scores = self.engine.get_z_scores(pid, current_metrics)
        max_z = np.max(np.abs(z_scores))
        
        is_anomalous = max_z > self.threshold_z
        
        # Calculate Euclidean distance to centroid as a secondary metric
        prof = self.engine.profiles.get(pid)
        distance = 0.0
        if prof is not None:
            distance = np.linalg.norm(current_metrics - prof["mu"])

        return {
            "pid": pid,
            "is_anomalous": bool(is_anomalous),
            "max_z_score": float(max_z),
            "z_vector": z_scores.tolist(),
            "euclidean_distance": float(distance),
            "severity": self._map_to_severity(max_z)
        }

    def _map_to_severity(self, z_score: float) -> str:
        if z_score < self.threshold_z:
            return "info"
        elif z_score < self.threshold_z * 2:
            return "warning"
        else:
            return "critical"

# Need to fix the Any import in the generated code
sed -i '1i from typing import Any' src/detector/statistical.py
