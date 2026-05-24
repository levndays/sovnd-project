import time
import json
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("agent")

from drivers.ebpf.bridge import EBPFAgent, OP_OPEN, OP_CLOSE, OP_READ, OP_WRITE, \
    FD_TYPE_FILE, FD_TYPE_SOCKET, FD_TYPE_PIPE
from core.detection.signature import SignatureDetector
from core.detection.statistical import StatisticalDetector
from core.metrics.engine import MetricsEngine
from core.scoring.engine import ScoringEngine
from core.graph.builder import ProvenanceGraphBuilder
from internal.storage.sqlite import StorageManager

HEARTBEAT_INTERVAL = 1.0


def run_agent():
    print("\N{SHIELD} Starting SovND Real-time eBPF Engine...")
    lib_path = Path(__file__).parent.parent / "drivers" / "ebpf" / "libloader.so"

    agent = EBPFAgent(lib_path=str(lib_path))
    sig_detector = SignatureDetector()
    scoring = ScoringEngine(threshold=15.0)
    storage = StorageManager()
    metrics_engine = MetricsEngine(alpha=0.3, n_gram_size=3)
    stat_detector = StatisticalDetector(engine=metrics_engine)
    graph_builder = ProvenanceGraphBuilder()

    storage.clear_alerts()
    os.makedirs("data", exist_ok=True)

    try:
        agent.start()
        print("\N{WHITE HEAVY CHECK MARK} eBPF Agent attached. Monitoring...")
        events_this_second = 0
        last_heartbeat = time.time()

        while True:
            now = time.time()
            if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                with open("data/heartbeat.json", "w") as f:
                    json.dump({"events_per_sec": events_this_second, "timestamp": now}, f)
                os.chmod("data/heartbeat.json", 0o666)
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
            graph_heuristics = []
            graph_builder.add_event(event)
            subgraph = graph_builder.get_process_subgraph(pid)
            if subgraph.number_of_nodes() > 5:
                graph_heuristics.append("high_connectivity")

            fname = event.get("filename", "")
            if fname.startswith("/etc") or fname.startswith("/root") or fname.startswith("/var/run"):
                graph_heuristics.append("sensitive_access")

            # detect bulk open/close bursts (ransomware indicator)
            op_type = event.get("op_type")
            if op_type in (OP_OPEN, OP_CLOSE):
                fd_type = event.get("fd_type")
                if fd_type == FD_TYPE_FILE and subgraph.number_of_nodes() > 8:
                    graph_heuristics.append("mass_file_ops")

            # detect unusual pipe/anonymous fd usage
            if event.get("fd_type") in (FD_TYPE_PIPE,):
                graph_heuristics.append("pipe_usage")

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
