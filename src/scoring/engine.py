import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class Alert:
    timestamp: str
    pid: int
    score: float
    severity: str
    reasons: List[str]
    container_info: Optional[Dict[str, Any]] = None

class ScoringEngine:
    """
    Final decision engine (Section 2.2).
    S = sum(w_i * d_i) * P_ctx
    Combines Statistical, Signature, and Graph-based insights.
    """
    
    def __init__(self, threshold: float = 10.0):
        self.threshold = threshold
        # Weights for different detection types
        self.weights = {
            "signature": 15.0,  # Immediate critical
            "statistical": 1.0,  # Scaled by Z-score
            "graph": 5.0        # Heuristic matches
        }

    def compute_score(self, 
                      stat_report: Dict[str, Any], 
                      sig_match: Optional[Dict[str, Any]], 
                      graph_heuristics: List[str],
                      container_info: Optional[Dict[str, Any]] = None) -> Optional[Alert]:
        """
        Aggregates detection results and generates an Alert if above threshold.
        """
        score = 0.0
        reasons = []
        
        # 1. Signature weight
        if sig_match:
            score += self.weights["signature"]
            reasons.append(f"Signature match: {sig_match['reason']}")
            
        # 2. Statistical weight (Z-score based)
        max_z = stat_report.get("max_z_score", 0.0)
        if stat_report.get("is_anomalous"):
            score += self.weights["statistical"] * max_z
            reasons.append(f"Statistical anomaly (Z={max_z:.2f})")
            
        # 3. Graph heuristics
        for h in graph_heuristics:
            score += self.weights["graph"]
            reasons.append(f"Graph heuristic: {h}")

        if score >= self.threshold:
            severity = "critical" if score > self.threshold * 2 else "warning"
            if any(r for r in reasons if "Signature" in r):
                severity = "critical"

            alert = Alert(
                timestamp=datetime.now().isoformat(),
                pid=stat_report["pid"],
                score=float(score),
                severity=severity,
                reasons=reasons,
                container_info=container_info
            )
            logger.warning("ALERT GENERATED: %s (Score: %.2f)", reasons[0], score)
            return alert
            
        return None
