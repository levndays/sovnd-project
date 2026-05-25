"""Centralised configuration for the SovND security monitoring system.

All thresholds, weights, paths and IOC lists live here so they can be
tuned without touching business-logic modules.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Pattern


# ── file-system defaults ────────────────────────────────────────

DEFAULT_DB_PATH     = os.environ.get("DB_PATH", "data/sovnd.db")
DEFAULT_HEARTBEAT   = "data/heartbeat.json"
DEFAULT_PID_DIR     = ".pids"
DEFAULT_LOG_DIR     = ".logs"
BPF_PIN_DIR         = "/sys/fs/bpf/sovnd"

THREAT_LEVEL = os.environ.get("THREAT_LEVEL", "medium")  # low, medium, high


# ── detection defaults ───────────────────────────────────────────

@dataclass(frozen=True)
class ScoringWeights:
    signature:   float = 15.0
    statistical: float = 1.0
    graph:       float = 5.0
    ngram:       float = 3.0     # weight on n-gram anomaly score (0..1)

@dataclass(frozen=True)
class Settings:
    # ── scoring ──────────────────────────────────────────────
    score_threshold:    float = 12.0
    score_critical:     float = 22.0     # severity ≥ this → critical
    weights:            ScoringWeights = field(default_factory=ScoringWeights)

    # ── statistical ──────────────────────────────────────────
    ewma_alpha:         float = 0.3
    n_gram_size:        int   = 3
    z_threshold:        float = 3.0
    z_threshold_severe: float = 6.0      # z ≥ this → critical severity
    history_maxlen:     int   = 100

    # ── graph ─────────────────────────────────────────────────
    graph_high_connectivity_nodes: int = 10
    graph_bulk_file_ops_nodes:     int = 8

    # ── eBPF rate limiting ────────────────────────────────────
    rate_limit_eps:     int   = 1000    # max events/sec/pid before sampling
    rate_sample_mod:    int   = 10      # emit every Nth event when throttling

    # ── heartbeat ─────────────────────────────────────────────
    heartbeat_interval: float = 1.0

    # ── paths ─────────────────────────────────────────────────
    db_path:            str = DEFAULT_DB_PATH
    heartbeat_path:     str = DEFAULT_HEARTBEAT
    data_dir:           str = "data"
    web_dir:            str = "web"


# ── IOC (Indicators of Compromise) ───────────────────────────────

CRITICAL_PATH_PATTERNS: List[Pattern] = [
    re.compile(r'^/etc/shadow$'),
    re.compile(r'^/etc/sudoers$'),
    re.compile(r'^/var/run/docker\.sock$'),
    re.compile(r'^/root/\.ssh/.*'),
    re.compile(r'^/proc/kcore$'),
]

SUSPICIOUS_COMMANDS: List[str] = [
    "nc", "ncat", "wget", "curl",
]


# ── P_ctx context coefficients (per §2.2) ────────────────────────
#
# Final score is multiplied by a per-comm coefficient: < 1 dampens
# noisy system tools, > 1 amplifies high-risk script interpreters.
# Unmapped processes get DEFAULT_CONTEXT_COEFFICIENT (1.0).
#
# The intent (per the paper): "lower for system utilities, higher
# for unknown scripts." Keep this table small and conservative —
# every coefficient is a tunable false-positive lever.

DEFAULT_CONTEXT_COEFFICIENT: float = 1.0

CONTEXT_COEFFICIENTS: Dict[str, float] = {
    # quiet, mostly-trusted system housekeeping
    "systemd":         0.5,
    "systemd-logind":  0.5,
    "systemd-journal": 0.5,
    "dbus-daemon":     0.5,
    "polkitd":         0.5,
    "cron":            0.6,
    "sudo":            0.7,
    # routine read-only utilities
    "cat":             0.8,
    "ls":              0.8,
    "find":            0.8,
    "grep":            0.8,
    # high-risk: script interpreters / shells launched in unusual contexts
    "sh":              1.3,
    "bash":            1.3,
    "perl":            1.3,
    "python":          1.2,
    "python3":         1.2,
}


# ── singleton ────────────────────────────────────────────────────

_level_thresholds = {"low": 20.0, "medium": 12.0, "high": 6.0}
_default = Settings(score_threshold=_level_thresholds.get(THREAT_LEVEL, 12.0))


def get_settings() -> Settings:
    return _default

def set_settings(s: Settings) -> None:
    global _default
    _default = s
