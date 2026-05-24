"""Centralised configuration for the SovND security monitoring system.

All thresholds, weights, paths and IOC lists live here so they can be
tuned without touching business-logic modules.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Pattern


# ── file-system defaults ────────────────────────────────────────

DEFAULT_DB_PATH     = os.environ.get("DB_PATH", "data/sovnd.db")
DEFAULT_HEARTBEAT   = "data/heartbeat.json"
DEFAULT_PID_DIR     = ".pids"
DEFAULT_LOG_DIR     = ".logs"
BPF_PIN_DIR         = "/sys/fs/bpf/sovnd"


# ── detection defaults ───────────────────────────────────────────

@dataclass(frozen=True)
class ScoringWeights:
    signature:   float = 15.0
    statistical: float = 1.0
    graph:       float = 5.0

@dataclass(frozen=True)
class Settings:
    # ── scoring ──────────────────────────────────────────────
    score_threshold:    float = 16.0
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


# ── singleton ────────────────────────────────────────────────────

_default = Settings()


def get_settings() -> Settings:
    """Return the application-wide Settings singleton.

    Override by calling ``set_settings(...)`` before app start.
    """
    return _default


def set_settings(s: Settings) -> None:
    global _default
    _default = s
