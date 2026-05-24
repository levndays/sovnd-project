import os
import sys
import time
import json
import sqlite3
import psutil
import subprocess
from pathlib import Path
from datetime import datetime

# Path setup
ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "sovnd.db"
HB_PATH = ROOT / "data" / "heartbeat.json"

def get_process_by_name(name):
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = " ".join(proc.info['cmdline'] or [])
            if name in cmdline:
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None

def measure_load(duration=5):
    """Measures CPU usage and captures peak EPS during load."""
    agent_proc = get_process_by_name("apps/agent.py")
    server_proc = get_process_by_name("apps.server")
    num_cores = psutil.cpu_count()
    
    if not agent_proc:
        print("⚠️ Agent not found. Make sure it's running (sudo python3 apps/demo.py start)")
        return 0, 0, 0, 0, 0

    print(f"📊 Monitoring performance for {duration}s on {num_cores}-core system...")
    
    # Initialize psutil counters
    agent_proc.cpu_percent(interval=None)
    if server_proc: server_proc.cpu_percent(interval=None)
    
    agent_samples = []
    server_samples = []
    eps_samples = []
    
    for _ in range(duration):
        time.sleep(1.0)
        agent_samples.append(agent_proc.cpu_percent(interval=None))
        if server_proc:
            server_samples.append(server_proc.cpu_percent(interval=None))
        
        # Capture current heartbeat
        try:
            with open(HB_PATH, "r") as f:
                hb = json.load(f)
                eps_samples.append(hb.get("events_per_sec", 0))
        except:
            pass
            
    avg_agent_raw = sum(agent_samples) / len(agent_samples)
    avg_server_raw = sum(server_samples) / len(server_samples) if server_samples else 0
    peak_eps = max(eps_samples) if eps_samples else 0
    
    # Normalized: (Process % / Total Cores)
    return avg_agent_raw, avg_server_raw, avg_agent_raw/num_cores, avg_server_raw/num_cores, peak_eps

def test_latency_and_precision():
    """Triggers an IOC and measures time to database entry."""
    print("⏱️  Testing Latency and Precision...")
    
    test_file = "/etc/shadow"
    start_time = time.time()
    subprocess.run(["cat", test_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    timeout = 5.0
    found = False
    latency = 0
    
    conn = sqlite3.connect(DB_PATH)
    while time.time() - start_time < timeout:
        cursor = conn.execute("SELECT timestamp FROM alerts WHERE reasons LIKE ? ORDER BY id DESC LIMIT 1", (f'%{test_file}%',))
        row = cursor.fetchone()
        if row:
            latency = (time.time() - start_time) * 1000 # ms
            found = True
            break
        time.sleep(0.1)
    conn.close()
    
    return found, latency

def run_suite():
    print("="*50)
    print("🛠️  SovND PERFORMANCE VALIDATION SUITE")
    print("="*50)

    # 1. Start Background Load
    # Increase load to ensure we hit measurable EPS
    stressor = subprocess.Popen(["bash", "-c", "while true; do ls -R /etc > /dev/null 2>&1; sleep 0.01; done"])
    time.sleep(2) # Let it warm up
    
    # 2. Measure CPU & EPS during load
    agent_raw, server_raw, agent_norm, server_norm, eps = measure_load(5)
    stressor.terminate()
    
    # 3. Latency & Precision
    found, latency = test_latency_and_precision()
    
    print("\n" + "="*50)
    print(f"{'Параметр':<30} | {'Значення':<15}")
    print("-" * 50)
    print(f"{'CPU Usage (Per-Core)':<30} | {agent_raw + server_raw:>6.2f}%")
    print(f"{'Total System Overhead':<30} | {agent_norm + server_norm:>6.2f}%")
    print(f"{'Затримка детектування':<30} | {latency:>6.2f} ms")
    print(f"{'Точність на IOC':<30} | {'100%' if found else '0%'}")
    print(f"{'Швидкість обробки (Peak EPS)':<30} | {eps:>6} EPS")
    print("="*50)

if __name__ == "__main__":
    run_suite()
