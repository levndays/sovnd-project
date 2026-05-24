"""Hybrid-signature scoring engine (§2.2 Explainable Scoring).

Computes ``S = Σ(wᵢ · dᵢ) · P_ctx`` aggregating signature,
statistical, and graph-provenance signals into a single
interpretable threat score with detailed breakdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.config import get_settings, Settings


@dataclass
class Alert:
    timestamp:      str
    pid:            int
    comm:           str
    score:          float
    severity:       str
    reasons:        List[str] = field(default_factory=list)
    breakdown:      Dict[str, float] = field(default_factory=dict)
    container_info: Optional[Dict[str, Any]] = None


class ScoringEngine:
    """Weighted-sum explainable scoring engine."""

    def __init__(self, settings: Optional[Settings] = None):
        cfg = settings or get_settings()
        self.threshold = cfg.score_threshold
        self.critical  = cfg.score_critical
        self.weights   = {
            "signature":   cfg.weights.signature,
            "statistical": cfg.weights.statistical,
            "graph":       cfg.weights.graph,
        }

    def compute(
        self,
        event:            Dict[str, Any],
        stat_report:      Dict[str, Any],
        sig_match:        Optional[Dict[str, Any]] = None,
        graph_heuristics: Optional[List[str]] = None,
        container_info:   Optional[Dict[str, Any]] = None,
    ) -> Optional[Alert]:
        """Evaluate an event against all detection vectors.

        Returns an ``Alert`` if the composite score exceeds the
        configured threshold, otherwise ``None``.
        """
        comp   = {"signature": 0.0, "statistical": 0.0, "graph": 0.0}
        reasons: List[str] = []

        # ── signature ──────────────────────────────────────
        if sig_match:
            sig_type = sig_match.get("type", "")
            if sig_type == "SIGNATURE_MATCH":
                comp["signature"] = self.weights["signature"]  # 15.0 — IOC match
            else:
                comp["signature"] = 8.0  # suspicious command, lower confidence
            reasons.append(sig_match["reason"])

        # ── statistical ────────────────────────────────────
        max_z = stat_report.get("max_z_score", 0.0)
        if stat_report.get("is_anomalous"):
            comp["statistical"] = self.weights["statistical"] * max_z
            reasons.append(f"Statistical Anomaly (Z={max_z:.1f})")
        elif stat_report.get("euclidean_distance", 0) > 10:
            comp["statistical"] = min(5.0, stat_report["euclidean_distance"] * 0.1)
            reasons.append("Cold-start activity spike")

        # ── graph ──────────────────────────────────────────
        weights = {
            "high_connectivity": 3.0,
            "sensitive_access": 5.0,
            "mass_file_ops": 7.0,
            "pipe_usage": 3.0,
        }
        for heuristic in (graph_heuristics or []):
            w = weights.get(heuristic, self.weights["graph"])
            comp["graph"] += w
            reasons.append(f"Graph Heuristic: {heuristic}")

        total = round(sum(comp.values()), 2)

        if total < self.threshold:
            return None

        severity = "critical" if total >= self.critical else "warning"

        return Alert(
            timestamp=datetime.now(timezone.utc).isoformat(),
            pid=event["pid"],
            comm=str(event.get("comm", "unknown")),
            score=total,
            severity=severity,
            reasons=reasons,
            breakdown=comp,
            container_info=container_info,
        )

