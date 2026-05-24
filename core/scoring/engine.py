from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional

@dataclass
class Alert:
    timestamp: str
    pid: int
    comm: str
    score: float
    severity: str
    reasons: List[str]
    breakdown: Dict[str, float]
    container_info: Optional[Dict[str, Any]] = None

class ScoringEngine:
    def __init__(self, threshold: float = 10.0):
        self.threshold = threshold
        self.weights = {"signature": 15.0, "statistical": 1.0, "graph": 5.0}

    def compute_score(self, event: Dict[str, Any], stat_report: Dict[str, Any], 
                      sig_match: Optional[Dict[str, Any]], 
                      graph_heuristics: List[str],
                      container_info: Optional[Dict[str, Any]] = None) -> Optional[Alert]:
        
        comp = {"signature": 0.0, "statistical": 0.0, "graph": 0.0}
        reasons = []
        
        if sig_match:
            comp["signature"] = self.weights["signature"]
            reasons.append(sig_match['reason'])
            
        max_z = stat_report.get("max_z_score", 0.0)
        if stat_report.get("is_anomalous"):
            comp["statistical"] = self.weights["statistical"] * max_z
            reasons.append(f"Statistical Anomaly (Z={max_z:.1f})")
            
        for h in graph_heuristics:
            comp["graph"] += self.weights["graph"]
            reasons.append(f"Graph Heuristic: {h}")

        total_score = sum(comp.values())

        if total_score >= self.threshold:
            return Alert(
                timestamp=datetime.now().isoformat(),
                pid=event["pid"],
                comm=event.get("comm", "unknown"),
                score=round(total_score, 2),
                severity="critical" if total_score > 20 else "warning",
                reasons=reasons,
                breakdown=comp,
                container_info=container_info
            )
        return None
