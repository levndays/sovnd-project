"""Training / validation / threshold-tuning harness — SCAFFOLDING.

**This file is intentionally not implemented.** Every action below
raises NotImplementedError. What's here is the CLI surface and a
documented contract for each step, so a future implementation can
slot in without breaking callers.

Background
==========

The audit found that the paper's §2.2 references a "training phase"
that derives baseline profiles and a "validation set" that selects
``T`` for a target FPR — none of which exist in the runtime. Today
the thresholds in ``core/config.py`` are hand-tuned constants and
the recent commit history is a sequence of manual threshold tweaks.

This harness, once implemented, will replace that with a
reproducible three-stage pipeline.

Pipeline
========

  1. ``collect``       record a baseline window of legitimate workload
                       and snapshot per-PID profiles (μ, σ, n-gram
                       counts) to disk
  2. ``validate``      replay a labelled corpus (positives + negatives)
                       through the scoring engine with the loaded
                       baseline, build a precision/recall vs. threshold
                       curve
  3. ``tune-threshold`` pick the largest ``T`` where FPR(T) ≤ target
                       and report TPR(T), precision(T), recall(T) at
                       that operating point

Output of each stage feeds the next:

    collect → baseline.json
    validate(baseline.json, holdout.json) → curves.json
    tune-threshold(curves.json, --fpr 0.02) → suggested threshold + metrics

Contract details (read before implementing)
===========================================

``collect``
    Snapshots ``MetricsEngine`` per-PID state to JSON. Requires a
    side channel from the running agent — easiest path is to add
    a periodic ``storage.save_profile(identifier, mu, sigma)`` call
    in the agent loop guarded by ``TRAINING=1`` env var, and to
    read back from the ``profiles`` table here. Don't try to share
    the in-memory engine.

``validate``
    Holdout corpus format (proposed):
        [{"event": {...}, "label": "ioc" | "benign"}]
    For each event, instantiate a fresh ``ScoringEngine`` and
    ``StatisticalDetector`` seeded with the baseline profiles, run
    ``compute(...)``, record (score, label) pairs.

``tune-threshold``
    Sweep T ∈ [0, max_observed_score] in steps; at each T compute
    FPR = FP / (FP + TN) and TPR = TP / (TP + FN); return the
    largest T with FPR ≤ target_fpr. If no T satisfies the target,
    print a warning and return the lowest-FPR T.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent


# ── data contracts ──────────────────────────────────────────────────


@dataclass
class BaselineSnapshot:
    """Snapshot of per-PID profiles at the end of a training window."""
    window_seconds:  int
    captured_at:     str            # ISO-8601 UTC
    n_processes:     int
    profiles:        dict[str, dict[str, Any]]  # identifier -> {mu, sigma, ...}


@dataclass
class ValidationCurves:
    """Precision/recall/FPR/TPR curve over a threshold sweep."""
    thresholds: list[float]
    precision:  list[float]
    recall:     list[float]
    fpr:        list[float]
    tpr:        list[float]


@dataclass
class TunedOperatingPoint:
    threshold:        float
    fpr:              float
    tpr:              float
    precision:        float
    recall:           float
    target_fpr:       float
    satisfied_target: bool


# ── pipeline stages (stubs) ─────────────────────────────────────────


def collect_baseline(window_seconds: int,
                     output_path: Path) -> BaselineSnapshot:
    """Record legitimate-workload baseline; snapshot to ``output_path``.

    TODO:
      1. Verify the agent is running with TRAINING=1 (snapshots
         per-PID μ/σ to ``profiles`` table every ~5 s).
      2. Sleep ``window_seconds``.
      3. Query the ``profiles`` table for all entries newer than
         start-of-window.
      4. Pack into BaselineSnapshot, write JSON.

    See module docstring → "collect" for the contract.
    """
    raise NotImplementedError(
        "collect_baseline is scaffolding only — wire MetricsEngine "
        "→ storage.save_profile during a training window first"
    )


def validate(baseline_path: Path,
             holdout_path: Path,
             output_path: Path) -> ValidationCurves:
    """Replay holdout corpus, return precision/recall vs. threshold.

    TODO:
      1. Load BaselineSnapshot from ``baseline_path``.
      2. Load labelled events from ``holdout_path`` (JSON list).
      3. Construct a ScoringEngine + StatisticalDetector seeded
         with the baseline.
      4. For each event, call ``scoring.compute(...)`` with
         ``threshold=0`` so every event gets a score back; record
         (score, label).
      5. Sweep T ∈ [0, max_score] in small steps; compute the
         confusion matrix at each T; pack into ValidationCurves,
         write JSON.

    See module docstring → "validate" for the contract.
    """
    raise NotImplementedError(
        "validate is scaffolding only — needs (a) a labelled holdout "
        "corpus, (b) a way to seed ScoringEngine with a saved baseline"
    )


def tune_threshold(curves_path: Path,
                   target_fpr: float) -> TunedOperatingPoint:
    """Pick the largest T where FPR(T) ≤ ``target_fpr``.

    TODO:
      1. Load ValidationCurves from ``curves_path``.
      2. Filter thresholds where fpr ≤ target_fpr.
      3. If none, warn and return the threshold with lowest fpr.
      4. Else return the largest such threshold along with its
         (precision, recall, fpr, tpr).

    Pure post-processing — no side effects beyond stdout. Once
    implemented, the returned threshold can be written into
    ``core/config.py::Settings.score_threshold`` (or just exported
    via THREAT_LEVEL env).
    """
    raise NotImplementedError(
        "tune_threshold is scaffolding only — depends on validate()"
    )


# ── CLI ─────────────────────────────────────────────────────────────


def _cmd_collect(args: argparse.Namespace) -> int:
    print(f"[collect] window={args.window}s → {args.out}", file=sys.stderr)
    if args.dry_run:
        print("[dry-run] would call collect_baseline(...) (stub)")
        return 0
    collect_baseline(args.window, Path(args.out))
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    print(f"[validate] baseline={args.baseline} holdout={args.holdout} "
          f"→ {args.out}", file=sys.stderr)
    if args.dry_run:
        print("[dry-run] would call validate(...) (stub)")
        return 0
    validate(Path(args.baseline), Path(args.holdout), Path(args.out))
    return 0


def _cmd_tune(args: argparse.Namespace) -> int:
    print(f"[tune-threshold] curves={args.curves} target-fpr={args.fpr}",
          file=sys.stderr)
    if args.dry_run:
        print("[dry-run] would call tune_threshold(...) (stub)")
        return 0
    point = tune_threshold(Path(args.curves), args.fpr)
    print(json.dumps(point.__dict__, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.strip().split("\n\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="print intent without invoking stubs")
    sub = parser.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("collect", help="snapshot baseline profiles")
    c.add_argument("--window", type=int, default=300,
                   help="training window in seconds (default 300)")
    c.add_argument("--out", default=str(ROOT / "data" / "baseline.json"))
    c.set_defaults(func=_cmd_collect)

    v = sub.add_parser("validate", help="run holdout corpus, build curves")
    v.add_argument("--baseline", required=True)
    v.add_argument("--holdout", required=True)
    v.add_argument("--out", default=str(ROOT / "data" / "curves.json"))
    v.set_defaults(func=_cmd_validate)

    t = sub.add_parser("tune-threshold",
                       help="pick T satisfying a target FPR")
    t.add_argument("--curves", required=True)
    t.add_argument("--fpr", type=float, default=0.02,
                   help="target false-positive rate (default 0.02)")
    t.set_defaults(func=_cmd_tune)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
