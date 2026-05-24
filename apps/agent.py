import time
import json
import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("agent")

from drivers.ebpf.bridge import EBPFAgent
from core.config import get_settings
from core.detection.signature import SignatureDetector
from core.detection.statistical import StatisticalDetector
from core.metrics.engine import MetricsEngine
from core.scoring.engine import ScoringEngine
from core.graph.builder import ProvenanceGraphBuilder
from internal.storage.sqlite import StorageManager


def run_agent():
    print("\N{SHIELD} Starting SovND Real-time eBPF Engine...")
    settings = get_settings()
    lib_path = Path(__file__).parent.parent / "drivers" / "ebpf" / "libloader.so"

    agent = EBPFAgent(lib_path=str(lib_path))
    sig_detector = SignatureDetector()
    scoring = ScoringEngine(settings=settings)
    storage = StorageManager(db_path=settings.db_path)
    metrics_engine = MetricsEngine(settings=settings)
    stat_detector = StatisticalDetector(engine=metrics_engine)
    graph_builder = ProvenanceGraphBuilder(settings=settings)

    storage.clear_alerts()
    os.makedirs(settings.data_dir, exist_ok=True)

    try:
        agent.start()
        print("\N{WHITE HEAVY CHECK MARK} eBPF Agent attached. Monitoring...")
        events_this_second = 0
        last_heartbeat = time.time()

        while True:
            now = time.time()
            if now - last_heartbeat >= settings.heartbeat_interval:
                with open(settings.heartbeat_path, "w") as f:
                    json.dump({"events_per_sec": events_this_second, "timestamp": now}, f)
                os.chmod(settings.heartbeat_path, 0o666)
                events_this_second = 0
                last_heartbeat = now

            event = agent.get_event(timeout=0.1)
            if not event:
                continue

            events_this_second += 1
            pid = event["pid"]

            # ── metrics & statistical ─────────────────────────
            metrics_engine.update(event)
            current_vec = metrics_engine.get_current_vector(pid)
            stat_report = stat_detector.evaluate(pid, current_vec)

            # ── signature ─────────────────────────────────────
            sig_match = sig_detector.analyze(event)

            # ── graph ─────────────────────────────────────────
            graph_builder.add_event(event)
            graph_heuristics = graph_builder.heuristics(pid, event)

            # ── scoring ───────────────────────────────────────
            alert = scoring.compute(
                event=event,
                stat_report=stat_report,
                sig_match=sig_match,
                graph_heuristics=graph_heuristics,
            )
            if alert:
                storage.save_alert(alert)
                print(f"\N{POLICE CARS REVOLVING LIGHT} ALERT: "
                      f"PID {event['pid']} [{event.get('comm','?')}] "
                      f"op={event.get('op_name','?')} "
                      f"SCORE {alert.score} "
                      f"{alert.severity}", flush=True)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        agent.stop()


if __name__ == "__main__":
    run_agent()
