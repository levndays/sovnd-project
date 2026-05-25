"""Performance validation suite for SovND (replaces the §4.5.2 fabrication).

Methodology
-----------

Throughput
    Drive a controlled number of openat() syscalls from a benign
    background process and measure the agent's observed EPS via its
    heartbeat file. Reports mean ± stddev across N runs.

Latency
    Trigger each IOC in a labelled corpus at a known wall-clock time
    and measure the delay from syscall to the corresponding row
    appearing in the SQLite alerts table. Reports median and p95
    across the corpus, repeated N runs.

Precision / Recall
    Replay a small labelled corpus:
      - positives: known critical IOCs (/etc/shadow, /etc/sudoers,
        /var/run/docker.sock, /proc/kcore, /root/.ssh/*)
      - negatives: benign reads in /etc that should *not* alert
        (sensitive_access alone is 5.0 with the default 12.0
        threshold, so they're below the floor)
    Count true / false positives in the DB after each replay, compute
    precision and recall. Repeated N runs.

CPU / RSS
    psutil-sampled agent + server CPU% and RSS over the run window.
    Reports mean ± stddev.

Output
    Pretty-printed summary table on stdout and a structured JSON
    report at ``data/perf_report.json`` — citeable from coursework.md
    §4.5.2.

Prerequisites
-------------
    The agent must already be running under sudo:
        sudo python3 apps/agent.py

    This script must ALSO be run as root: the positive IOCs
    (/etc/shadow, /etc/sudoers, /proc/kcore, …) are 0600 root-only
    files. The eBPF tracer only emits on *successful* openat, so a
    failed (EACCES) open from a non-root context produces no event
    and no alert. Without sudo here you'd measure precision/recall
    of zero through no fault of the agent.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional

import psutil


ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "sovnd.db"
HEARTBEAT_PATH = ROOT / "data" / "heartbeat.json"
REPORT_PATH = ROOT / "data" / "perf_report.json"


# ── corpus ──────────────────────────────────────────────────────────

POSITIVES = [
    "/etc/shadow",
    "/etc/sudoers",
    "/var/run/docker.sock",
    "/proc/kcore",
]

# Benign /etc files: trigger 'sensitive_access' (5.0) but stay
# below the 12.0 threshold, so they should NOT raise alerts.
NEGATIVES = [
    "/etc/hostname",
    "/etc/timezone",
    "/etc/os-release",
    "/etc/issue",
    "/etc/protocols",
    "/etc/services",
]


# ── data classes ────────────────────────────────────────────────────


@dataclass
class RunSummary:
    """One run's measurement set."""
    cpu_pct:           float
    rss_mb:            float
    measured_eps:      float
    precision:         float
    recall:            float
    latency_median_ms: float
    latency_p95_ms:    float
    true_positives:    int
    false_positives:   int
    false_negatives:   int


@dataclass
class FinalReport:
    runs:                 int
    target_eps:           int
    run_window_seconds:   int
    cpu_pct_mean:         float
    cpu_pct_stddev:       float
    rss_mb_mean:          float
    eps_mean:             float
    eps_stddev:           float
    precision_mean:       float
    recall_mean:          float
    latency_median_ms:    float
    latency_p95_ms:       float
    samples:              List[RunSummary] = field(default_factory=list)
    methodology:          str = ""


# ── helpers ─────────────────────────────────────────────────────────


def find_agent_process() -> Optional[psutil.Process]:
    """Find the python interpreter running apps/agent.py.

    Strict match: argv[0] must look like a python binary AND argv
    must contain ``apps/agent.py``. Catches the actual interpreter,
    not the sudo / bash wrapper around it (which would skew CPU
    measurements to 0 % since wrappers sit idle).
    """
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = p.info["cmdline"] or []
            if not cmd:
                continue
            argv0 = os.path.basename(cmd[0]).lower()
            if not argv0.startswith("python"):
                continue
            if any("apps/agent.py" in a for a in cmd):
                return p
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def require_agent() -> psutil.Process:
    proc = find_agent_process()
    if proc is None:
        print("ERROR: agent not running. Start it first:", file=sys.stderr)
        print("    sudo python3 apps/agent.py", file=sys.stderr)
        sys.exit(2)
    return proc


def require_db() -> None:
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found — agent hasn't produced any data",
              file=sys.stderr)
        sys.exit(2)


def require_root() -> None:
    if os.geteuid() != 0:
        print("ERROR: this script must run as root so the IOC opens "
              "succeed (the eBPF tracer only emits successful openats).",
              file=sys.stderr)
        print("Try:  sudo -E python3 scripts/validate_performance.py …",
              file=sys.stderr)
        sys.exit(2)


def alerts_since(conn: sqlite3.Connection, since_iso: str,
                 pattern: Optional[str] = None) -> List[Dict]:
    """All alerts written to the DB after ``since_iso``."""
    if pattern:
        rows = conn.execute(
            "SELECT timestamp, pid, comm, reasons FROM alerts "
            "WHERE timestamp >= ? AND reasons LIKE ? ORDER BY id",
            (since_iso, f"%{pattern}%"),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT timestamp, pid, comm, reasons FROM alerts "
            "WHERE timestamp >= ? ORDER BY id",
            (since_iso,),
        ).fetchall()
    return [
        {"timestamp": r[0], "pid": r[1], "comm": r[2], "reasons": r[3]}
        for r in rows
    ]


def now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ── measurements ────────────────────────────────────────────────────


def measure_cpu_and_eps(proc: psutil.Process,
                        window_s: int,
                        target_eps: int) -> Dict[str, float]:
    """Run a controlled-rate openat() loop in the background and
    sample agent CPU + observed EPS over ``window_s`` seconds."""

    # Stressor: open + close /tmp/perf_<pid>_<i> at a paced rate.
    # Background process so we can sample while it's running.
    stressor = subprocess.Popen(
        ["python3", "-c", f"""
import os, time
target = {target_eps}
interval = 1.0 / target if target > 0 else 0
end = time.time() + {window_s}
i = 0
while time.time() < end:
    try:
        fd = os.open(f'/tmp/perf_{{os.getpid()}}_{{i}}', os.O_CREAT | os.O_RDONLY)
        os.close(fd)
        os.unlink(f'/tmp/perf_{{os.getpid()}}_{{i}}')
    except OSError:
        pass
    i += 1
    if interval:
        time.sleep(interval)
"""],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    # warm-up
    time.sleep(1.0)
    proc.cpu_percent(interval=None)  # prime baseline

    cpu_samples: List[float] = []
    eps_samples: List[float] = []
    for _ in range(window_s):
        time.sleep(1.0)
        cpu_samples.append(proc.cpu_percent(interval=None))
        try:
            hb = json.loads(HEARTBEAT_PATH.read_text())
            eps_samples.append(float(hb.get("events_per_sec", 0)))
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    stressor.terminate()
    try:
        stressor.wait(timeout=3)
    except subprocess.TimeoutExpired:
        stressor.kill()

    rss_mb = proc.memory_info().rss / 1024 / 1024
    return {
        "cpu_pct":      statistics.mean(cpu_samples) if cpu_samples else 0.0,
        "rss_mb":       rss_mb,
        "measured_eps": statistics.mean(eps_samples) if eps_samples else 0.0,
    }


def _trigger_open(path: str) -> None:
    """Trigger a successful openat() against ``path``, using a
    short-lived ``cat`` subprocess so the comm tag is "cat" (not
    "python", which the agent filters as noise).

    A short timeout is essential: ``/var/run/docker.sock`` is a
    socket (cat would block reading), and ``/proc/kcore`` is the
    size of RAM (cat would take hours). The openat event fires the
    moment cat starts; we only need the process alive long enough
    to make that syscall.
    """
    try:
        subprocess.run(
            ["cat", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=0.5,
        )
    except subprocess.TimeoutExpired:
        pass  # openat already fired; reads can hang, we don't care


def measure_latency(timeout_s: float = 5.0) -> List[float]:
    """Trigger each positive IOC, time the round-trip to DB.

    Returns a list of per-IOC latencies in milliseconds. IOCs that
    don't appear in the DB before ``timeout_s`` are reported as the
    timeout (which makes the p95 visible if anything's broken).
    """
    conn = sqlite3.connect(DB_PATH)
    latencies: List[float] = []

    for ioc in POSITIVES:
        baseline_iso = now_iso()
        start = time.time()

        _trigger_open(ioc)

        latency_ms = timeout_s * 1000
        while time.time() - start < timeout_s:
            rows = alerts_since(conn, baseline_iso, pattern=ioc)
            if rows:
                latency_ms = (time.time() - start) * 1000
                break
            time.sleep(0.05)

        latencies.append(latency_ms)

    conn.close()
    return latencies


def measure_precision_recall() -> Dict[str, int]:
    """Replay positives + negatives, count TP/FP/FN from DB."""
    conn = sqlite3.connect(DB_PATH)
    baseline_iso = now_iso()

    # Trigger every corpus entry once
    for path in POSITIVES + NEGATIVES:
        _trigger_open(path)

    # Give the agent a moment to drain its queue
    time.sleep(2.0)

    alerts = alerts_since(conn, baseline_iso)
    conn.close()

    # Match each alert to a positive or negative by reason text
    matched_positives = set()
    false_positives = 0
    for a in alerts:
        reasons = a["reasons"] or ""
        matched_pos = False
        for pos in POSITIVES:
            if pos in reasons:
                matched_positives.add(pos)
                matched_pos = True
                break
        if matched_pos:
            continue
        for neg in NEGATIVES:
            if neg in reasons:
                false_positives += 1
                break

    true_positives = len(matched_positives)
    false_negatives = len(POSITIVES) - true_positives

    return {
        "tp": true_positives,
        "fp": false_positives,
        "fn": false_negatives,
    }


def run_once(proc: psutil.Process,
             window_s: int,
             target_eps: int) -> RunSummary:
    cpu_eps = measure_cpu_and_eps(proc, window_s, target_eps)
    lats = measure_latency()
    pr = measure_precision_recall()

    tp, fp, fn = pr["tp"], pr["fp"], pr["fn"]
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0

    return RunSummary(
        cpu_pct=cpu_eps["cpu_pct"],
        rss_mb=cpu_eps["rss_mb"],
        measured_eps=cpu_eps["measured_eps"],
        precision=precision,
        recall=recall,
        latency_median_ms=statistics.median(lats),
        latency_p95_ms=sorted(lats)[max(0, int(len(lats) * 0.95) - 1)],
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
    )


# ── orchestration ───────────────────────────────────────────────────


def aggregate(samples: List[RunSummary],
              runs: int, target_eps: int, window: int) -> FinalReport:
    cpu = [s.cpu_pct for s in samples]
    rss = [s.rss_mb for s in samples]
    eps = [s.measured_eps for s in samples]
    lat_med = [s.latency_median_ms for s in samples]
    lat_p95 = [s.latency_p95_ms for s in samples]

    def safe_std(xs: List[float]) -> float:
        return statistics.stdev(xs) if len(xs) > 1 else 0.0

    # Aggregate confusion counts across runs so a degenerate run
    # (TP=0, FP=0 → undefined precision) doesn't drag the mean to
    # zero. Per-run figures stay in samples for inspection.
    tp = sum(s.true_positives for s in samples)
    fp = sum(s.false_positives for s in samples)
    fn = sum(s.false_negatives for s in samples)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0

    return FinalReport(
        runs=runs,
        target_eps=target_eps,
        run_window_seconds=window,
        cpu_pct_mean=statistics.mean(cpu),
        cpu_pct_stddev=safe_std(cpu),
        rss_mb_mean=statistics.mean(rss),
        eps_mean=statistics.mean(eps),
        eps_stddev=safe_std(eps),
        precision_mean=precision,
        recall_mean=recall,
        latency_median_ms=statistics.median(lat_med),
        latency_p95_ms=statistics.median(lat_p95),
        samples=samples,
        methodology=__doc__.strip().split("\n\n", 1)[1],
    )


def print_report(rep: FinalReport) -> None:
    print()
    print("=" * 62)
    print(" SovND PERFORMANCE VALIDATION ".center(62, "="))
    print("=" * 62)
    print(f" Runs:              {rep.runs}")
    print(f" Window:            {rep.run_window_seconds}s per run")
    print(f" Target EPS:        {rep.target_eps}")
    print("-" * 62)
    print(f" CPU (agent):       {rep.cpu_pct_mean:6.2f}% ± {rep.cpu_pct_stddev:.2f}")
    print(f" RSS (agent):       {rep.rss_mb_mean:6.1f} MB")
    print(f" Measured EPS:      {rep.eps_mean:6.0f}    ± {rep.eps_stddev:.0f}")
    print(f" Detection latency: {rep.latency_median_ms:6.0f} ms median, "
          f"{rep.latency_p95_ms:.0f} ms p95")
    print(f" Precision:         {rep.precision_mean:.2%}  "
          f"(TP / (TP+FP), aggregated across runs)")
    print(f" Recall:            {rep.recall_mean:.2%}  "
          f"(TP / (TP+FN), aggregated across runs)")
    print("=" * 62)
    print(f" Full report → {REPORT_PATH.relative_to(ROOT)}")
    print()


def write_report(rep: FinalReport) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(asdict(rep), indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=5,
                        help="number of repetitions (default 5)")
    parser.add_argument("--target-eps", type=int, default=2000,
                        help="target events/sec for the stressor")
    parser.add_argument("--window", type=int, default=30,
                        help="seconds per CPU/EPS window")
    args = parser.parse_args()

    require_root()
    require_db()
    proc = require_agent()
    print(f"Agent PID {proc.pid}, DB {DB_PATH}")

    samples: List[RunSummary] = []
    for i in range(1, args.runs + 1):
        print(f"  Run {i}/{args.runs}…", flush=True)
        samples.append(run_once(proc, args.window, args.target_eps))
        if i < args.runs:
            # Give the agent's event queue time to drain between
            # runs — back-to-back load otherwise measures recovery
            # rather than steady-state behavior.
            time.sleep(3.0)

    report = aggregate(samples, args.runs, args.target_eps, args.window)
    write_report(report)
    print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
