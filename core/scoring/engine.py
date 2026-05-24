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
            comp["signature"] = self.weights["signature"]
            reasons.append(sig_match["reason"])

        # ── statistical ────────────────────────────────────
        max_z = stat_report.get("max_z_score", 0.0)
        if stat_report.get("is_anomalous"):
            comp["statistical"] = self.weights["statistical"] * max_z
            reasons.append(f"Statistical Anomaly (Z={max_z:.1f})")

        # ── graph ──────────────────────────────────────────
        for heuristic in (graph_heuristics or []):
            comp["graph"] += self.weights["graph"]
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

