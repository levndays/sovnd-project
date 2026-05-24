import time, sys, os, json, dataclasses
from pathlib import Path
import random

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None
    print("⚠️ numpy not available - statistical detection disabled")

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    nx = None
    print("⚠️ networkx not available - graph detection disabled")

try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from drivers.ebpf.bridge import EBPFAgent
    from core.detection.signature import SignatureDetector
    
    if HAS_NUMPY:
        from core.detection.statistical import StatisticalDetector
        from core.metrics.engine import MetricsEngine
        from core.scoring.engine import ScoringEngine
        STAT_DETECTOR = True
    else:
        from core.scoring.engine import ScoringEngine
        STAT_DETECTOR = False
    
    if HAS_NETWORKX:
        from core.graph.builder import ProvenanceGraphBuilder
    else:
        ProvenanceGraphBuilder = None
    
    from internal.storage.sqlite import StorageManager
except Exception as e:
    print(f"⚠️ Import error: {e}")
    raise

def run_agent():
    print("🛡️ Starting SovND Real-time eBPF Engine...")
    lib_path = Path(__file__).parent.parent / "drivers" / "ebpf" / "libloader.so"
    
    # Pre-populated process heap for demo (simulates baseline profiles)
    preloaded_pids = list(range(1000, 1100))
    random.shuffle(preloaded_pids)
    
    agent = EBPFAgent(lib_path=str(lib_path))
    sig_detector = SignatureDetector()
    scoring = ScoringEngine(threshold=15.0)
    storage = StorageManager()
    
    if STAT_DETECTOR and HAS_NUMPY:
        print("📊 Statistical detection enabled")
        metrics_engine = MetricsEngine()
        stat_detector = StatisticalDetector(engine=metrics_engine, threshold_z=2.5)
    else:
        print("📊 Statistical detection DISABLED")
        metrics_engine = None
        stat_detector = None
    
    if HAS_NETWORKX and ProvenanceGraphBuilder:
        print("🔗 Graph detection enabled")
        graph_builder = ProvenanceGraphBuilder()
    else:
        print("🔗 Graph detection DISABLED")
        graph_builder = None

    # Clear old data for demo freshness
    storage.clear_alerts()

    try:
        agent.start()
        print("✅ eBPF Agent attached. Monitoring...")
        events_this_second = 0
        last_heartbeat = time.time()
        
        while True:
            current_time = time.time()
            if current_time - last_heartbeat >= 1.0:
                print(f"📊 [Agent Heartbeat] Processing {events_this_second} events/sec", flush=True)
                with open("data/heartbeat.json", "w") as f:
                    json.dump({"events_per_sec": events_this_second, "timestamp": current_time}, f)
                os.chmod("data/heartbeat.json", 0o666)
                events_this_second = 0
                last_heartbeat = current_time

            event = agent.get_event(timeout=0.1)
            if event:
                events_this_second += 1
                
                graph_heuristics = []
                
                if graph_builder:
                    graph_builder.add_event(event)
                    subgraph = graph_builder.get_process_subgraph(event["pid"])
                    if subgraph.number_of_nodes() > 3:
                        graph_heuristics.append("high_connectivity")
                
                if event.get("filename", "").startswith("/etc") or event.get("filename", "").startswith("/root"):
                    graph_heuristics.append("sensitive_access")
                
                sig_match = sig_detector.analyze_event(event)
                
                if STAT_DETECTOR and metrics_engine and stat_detector:
                    metrics_engine.update(event)
                    stat_report = stat_detector.evaluate(
                        pid=event["pid"],
                        current_metrics=metrics_engine.get_current_vector(event["pid"])
                    )
                else:
                    stat_report = {"pid": event["pid"], "is_anomalous": False, "max_z_score": 0.0}
                
                alert = scoring.compute_score(
                    event=event,
                    stat_report=stat_report,
                    sig_match=sig_match,
                    graph_heuristics=graph_heuristics
                )
                
                if alert:
                    storage.save_alert(dataclasses.asdict(alert))
                    try: os.chmod(storage.db_path, 0o666)
                    except: pass
                    print(f"🚨 ALERT: PID {event['pid']} [{event['comm']}] - SCORE {alert.score}", flush=True)
    except KeyboardInterrupt: pass
    finally: agent.stop()

if __name__ == "__main__":
    run_agent()