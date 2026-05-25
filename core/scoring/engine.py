"""Hybrid-signature scoring engine (§2.2 Explainable Scoring).

Computes ``S = Σ(wᵢ · dᵢ) · P_ctx`` aggregating signature,
statistical, graph-provenance, and n-gram signals into a single
interpretable threat score with detailed breakdown.

P_ctx is a per-process context coefficient (see
``core.config.CONTEXT_COEFFICIENTS``) that dampens known-quiet
system tools and amplifies high-risk shell/script interpreters
launched in unusual contexts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.config import (
    CONTEXT_COEFFICIENTS,
    DEFAULT_CONTEXT_COEFFICIENT,
    Settings,
    get_settings,
)


@dataclass
class Alert:
    timestamp:      str
    pid:            int
    comm:           str
    score:          float
    severity:       str
    reasons:        list[str] = field(default_factory=list)
    breakdown:      dict[str, float] = field(default_factory=dict)
    container_info: dict[str, Any] | None = None


class ScoringEngine:
    """Weighted-sum explainable scoring engine."""

    def __init__(self, settings: Settings | None = None):
        cfg = settings or get_settings()
        self.threshold = cfg.score_threshold
        self.critical  = cfg.score_critical
        self.weights   = {
            "signature":   cfg.weights.signature,
            "statistical": cfg.weights.statistical,
            "graph":       cfg.weights.graph,
            "ngram":       cfg.weights.ngram,
        }

    def compute(
        self,
        event:            dict[str, Any],
        stat_report:      dict[str, Any],
        sig_match:        dict[str, Any] | None = None,
        graph_heuristics: list[str] | None = None,
        container_info:   dict[str, Any] | None = None,
    ) -> Alert | None:
        """Evaluate an event against all detection vectors.

        Returns an ``Alert`` if the composite score exceeds the
        configured threshold, otherwise ``None``.
        """
        comp   = {"signature": 0.0, "statistical": 0.0,
                  "graph": 0.0, "ngram": 0.0}
        reasons: list[str] = []

        # ── signature ──────────────────────────────────────
        if sig_match:
            sig_type = sig_match.get("type", "")
            if sig_type == "SIGNATURE_MATCH":
                comp["signature"] = self.weights["signature"]  # 15.0 — IOC match
            else:
                comp["signature"] = 5.0  # suspicious command, low confidence
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

        # ── n-gram (rare syscall sequence) ─────────────────
        ngram_anomaly = float(stat_report.get("ngram_anomaly", 0.0))
        # Only contribute when the sequence is meaningfully rare;
        # the inverse-frequency metric saturates near 1.0 for cold
        # starts, so an absolute floor avoids cold-start noise.
        if ngram_anomaly >= 0.7:
            comp["ngram"] = self.weights["ngram"] * ngram_anomaly
            reasons.append(f"Rare syscall n-gram (p={1 - ngram_anomaly:.2f})")

        # ── context multiplier (P_ctx) ─────────────────────
        comm = str(event.get("comm", "")) or "unknown"
        p_ctx = self._context_coefficient(comm)
        total = round(sum(comp.values()) * p_ctx, 2)

        if total < self.threshold:
            return None

        severity = "critical" if total >= self.critical else "warning"

        # Expose P_ctx so the dashboard / alert log can show why a
        # score landed where it did.
        breakdown_out = dict(comp)
        breakdown_out["p_ctx"] = p_ctx

        return Alert(
            timestamp=datetime.now(timezone.utc).isoformat(),
            pid=event["pid"],
            comm=comm,
            score=total,
            severity=severity,
            reasons=reasons,
            breakdown=breakdown_out,
            container_info=container_info,
        )

    @staticmethod
    def _context_coefficient(comm: str) -> float:
        """Return P_ctx for *comm* (defaults to 1.0 if unmapped)."""
        return CONTEXT_COEFFICIENTS.get(comm, DEFAULT_CONTEXT_COEFFICIENT)

