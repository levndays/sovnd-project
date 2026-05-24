"""Signature-based IOC detector (§1.4, §2.2).

Fast-pattern matching against known Indicators of Compromise:
sensitive file paths and suspicious command invocations.
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional, Pattern

from core.config import CRITICAL_PATH_PATTERNS, SUSPICIOUS_COMMANDS

logger = logging.getLogger(__name__)


class SignatureDetector:
    """Regex-based fast path for known IOCs.

    Critical-path matches are high-confidence (e.g. ``/etc/shadow``).
    Suspicious-comm matches are lower-confidence heuristics that
    require context confirmation.
    """

    def __init__(
        self,
        critical_paths: Optional[List[Pattern]] = None,
        suspicious_commands: Optional[List[str]] = None,
    ):
        self._critical_paths = critical_paths or CRITICAL_PATH_PATTERNS
        self._suspicious = suspicious_commands or SUSPICIOUS_COMMANDS

    # ── public API ───────────────────────────────────────────

    def analyze(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Scan a single eBPF event for signature matches.

        Returns
        -------
        dict or None
            ``{"type": "SIGNATURE_MATCH", "reason": ..., "severity": ..., "ioc": ...}``
            for a critical match, or ``{"type": "HEURISTIC_MATCH", ...}``
            for a suspicious-command match.  Returns ``None`` if nothing
            matched.
        """
        filename = str(event.get("filename") or "")
        comm     = str(event.get("comm") or "")

        if not filename:
            return None

        # ── critical paths (IOC) ───────────────────────────
        for pattern in self._critical_paths:
            if pattern.match(filename):
                return {
                    "type": "SIGNATURE_MATCH",
                    "reason": f"Access to critical file: {filename}",
                    "severity": "critical",
                    "ioc": filename,
                }

        # ── suspicious command heuristics ───────────────────
        if any(cmd in comm for cmd in self._suspicious):
            if "/bin/" in filename or "/usr/bin/" in filename:
                return {
                    "type": "HEURISTIC_MATCH",
                    "reason": f"Suspicious process activity: {comm}",
                    "severity": "warning",
                }

        return None

