# Source Code

## Python (src/)

### __init__.py

```python

```

### api/main.py

```python
   1 | import asyncio, json, os, time, random
   2 | from fastapi import FastAPI, WebSocket, WebSocketDisconnect
   3 | from fastapi.staticfiles import StaticFiles
   4 | from fastapi.responses import FileResponse
   5 | from src.storage.sqlite import StorageManager
   6 | 
   7 | app = FastAPI()
   8 | storage = StorageManager()
   9 | 
  10 | os.makedirs("static", exist_ok=True)
  11 | app.mount("/static", StaticFiles(directory="static"), name="static")
  12 | 
  13 | @app.get("/")
  14 | async def get_index():
  15 |     return FileResponse("static/index.html")
  16 | 
  17 | @app.websocket("/ws/telemetry")
  18 | async def websocket_endpoint(websocket: WebSocket):
  19 |     await websocket.accept()
  20 |     try:
  21 |         while True:
  22 |             alerts = storage.get_recent_alerts(limit=10)
  23 |             eps = 0
  24 |             try:
  25 |                 with open("data/heartbeat.json", "r") as f:
  26 |                     hb = json.load(f)
  27 |                     if time.time() - hb.get("timestamp", 0) < 3:
  28 |                         eps = hb.get("events_per_sec", 0)
  29 |             except: pass
  30 |             await websocket.send_json({"eps": eps, "alerts": alerts})
  31 |             await asyncio.sleep(0.5)
  32 |     except WebSocketDisconnect:
  33 |         pass
  34 | 
  35 | @app.post("/api/attack")
  36 | async def trigger_attack():
  37 |     payloads = [
  38 |         "cat /etc/shadow",
  39 |         "cat /var/run/docker.sock",
  40 |         "cat /etc/sudoers",
  41 |         "python3 -c 'import os; os.open(\"/proc/kcore\", 0)'",
  42 |         "python3 -c 'import os; os.open(\"/root/.ssh/id_rsa\", 0)'",
  43 |         "bash -c 'echo \"backdoor\" > /tmp/check'"
  44 |     ]
  45 |     selected = random.sample(payloads, 3)
  46 |     for cmd in selected:
  47 |         os.system(f"{cmd} > /dev/null 2>&1 &")
  48 |     return {"status": "3_attacks_launched"}
```

### dashboard/app.py

```python
   1 | import streamlit as st
   2 | import pandas as pd
   3 | import plotly.express as px
   4 | import json
   5 | import os
   6 | import time
   7 | import subprocess
   8 | from datetime import datetime
   9 | import sys
  10 | 
  11 | sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
  12 | from src.storage.sqlite import StorageManager
  13 | 
  14 | # Get project root (parent of src/)
  15 | PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  16 | if PROJECT_ROOT.endswith('/src'):
  17 |     PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)
  18 | HEARTBEAT_FILE = os.path.join(PROJECT_ROOT, "data", "heartbeat.json")
  19 | 
  20 | # ----------------- PAGE CONFIG -----------------
  21 | st.set_page_config(
  22 |     page_title="SovND | Command Center",
  23 |     page_icon="🛡️",
  24 |     layout="wide",
  25 |     initial_sidebar_state="expanded"
  26 | )
  27 | 
  28 | # Force Dark Mode CSS & Custom Styling
  29 | st.markdown("""
  30 |     <style>
  31 |     .stApp { background-color: #0e1117; color: #fafafa; }
  32 |     .metric-card { 
  33 |         background-color: #1e293b; padding: 20px; border-radius: 8px; 
  34 |         border-left: 5px solid #3b82f6; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  35 |     }
  36 |     .alert-critical { 
  37 |         background-color: #450a0a; border-left: 5px solid #ef4444; 
  38 |         padding: 15px; border-radius: 5px; margin-bottom: 10px;
  39 |     }
  40 |     .stButton>button { width: 100%; font-weight: bold; }
  41 |     .attack-btn>button { background-color: #7f1d1d !important; color: white !important; border: 1px solid #ef4444 !important; }
  42 |     
  43 |     /* Attack flash animation */
  44 |     @keyframes flash-red {
  45 |         0% { box-shadow: inset 0 0 0 0 rgba(239, 68, 68, 0); }
  46 |         50% { box-shadow: inset 0 0 100px 50px rgba(239, 68, 68, 0.5); }
  47 |         100% { box-shadow: inset 0 0 0 0 rgba(239, 68, 68, 0); }
  48 |     }
  49 |     .attack-flash {
  50 |         animation: flash-red 1s ease-out;
  51 |     }
  52 |     </style>
  53 | """, unsafe_allow_html=True)
  54 | 
  55 | # ----------------- STATE & DATA -----------------
  56 | storage = StorageManager()
  57 | 
  58 | if 'syscall_history' not in st.session_state:
  59 |     st.session_state.syscall_history =[]
  60 | if 'live_monitor' not in st.session_state:
  61 |     st.session_state.live_monitor = True
  62 | if 'attack_events' not in st.session_state:
  63 |     st.session_state.attack_events = []
  64 | if 'last_alert_count' not in st.session_state:
  65 |     st.session_state.last_alert_count = 0
  66 | if 'flash_screen' not in st.session_state:
  67 |     st.session_state.flash_screen = False
  68 | 
  69 | # Use PROJECT_ROOT which is correctly calculated above
  70 | 
  71 | def load_heartbeat():
  72 |     try:
  73 |         with open(HEARTBEAT_FILE, "r") as f:
  74 |             data = json.load(f)
  75 |             return data.get("events_per_sec", 0)
  76 |     except:
  77 |         return 0
  78 | 
  79 | def launch_real_attack():
  80 |     """Executes the actual attacks directly from Python, no external scripts needed."""
  81 |     try:
  82 |         # 1. Trigger /etc/shadow read alert (Signature Match)
  83 |         subprocess.run(["cat", "/etc/shadow"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
  84 |         
  85 |         # 2. Trigger Docker sock access alert (Signature Match)
  86 |         subprocess.run(["cat", "/var/run/docker.sock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
  87 |         
  88 |         # 3. Trigger suspicious shell (Heuristic)
  89 |         subprocess.run(["bash", "-c", "echo 'stealth shell'"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
  90 |         
  91 |         # Mark attack time for graph highlighting
  92 |         st.session_state.attack_events.append(datetime.now())
  93 |         # Clean up old attack markers (older than 60 seconds)
  94 |         st.session_state.attack_events = [
  95 |             t for t in st.session_state.attack_events 
  96 |             if (datetime.now() - t).total_seconds() < 60
  97 |         ]
  98 |         
  99 |         return True
 100 |     except Exception as e:
 101 |         st.error(f"Failed to launch attack: {e}")
 102 |         return False
 103 | 
 104 | # ----------------- SIDEBAR -----------------
 105 | with st.sidebar:
 106 |     st.image("https://img.icons8.com/fluency/96/shield.png", width=60)
 107 |     st.title("SovND Control")
 108 |     st.markdown("---")
 109 |     
 110 |     st.session_state.live_monitor = st.toggle("🔴 Live Auto-Refresh", value=st.session_state.live_monitor)
 111 |     
 112 |     st.markdown("---")
 113 |     st.markdown("### ⚠️ Live Demo Actions")
 114 |     st.caption("These buttons execute REAL scripts on the host machine.")
 115 |     
 116 |     # Wrap button in custom class for red styling
 117 |     st.markdown('<div class="attack-btn">', unsafe_allow_html=True)
 118 |     if st.button("💥 LAUNCH REAL ATTACK", use_container_width=True):
 119 |         launch_real_attack()
 120 |     st.markdown('</div>', unsafe_allow_html=True)
 121 | 
 122 | # ----------------- MAIN DASHBOARD -----------------
 123 | st.title("🛡️ SovND Security Command Center")
 124 | st.caption("Live eBPF Kernel Telemetry & Threat Detection")
 125 | 
 126 | # Apply flash effect if new alerts
 127 | if st.session_state.flash_screen:
 128 |     st.markdown("""
 129 |         <div class="attack-flash" style="position:fixed; top:0; left:0; right:0; bottom:0; pointer-events:none; z-index:9999;"></div>
 130 |     """, unsafe_allow_html=True)
 131 |     st.session_state.flash_screen = False
 132 | 
 133 | # 1. Fetch live data
 134 | alerts_data = storage.get_recent_alerts(limit=50)
 135 | df_alerts = pd.DataFrame(alerts_data) if alerts_data else pd.DataFrame()
 136 | total_alerts = len(df_alerts)
 137 | 
 138 | # Trigger flash if new alerts appeared
 139 | if total_alerts > st.session_state.last_alert_count:
 140 |     st.session_state.flash_screen = True
 141 | st.session_state.last_alert_count = total_alerts
 142 | 
 143 | current_eps = load_heartbeat()
 144 | st.session_state.syscall_history.append({"time": datetime.now(), "events": current_eps})
 145 | if len(st.session_state.syscall_history) > 30: # Keep last 30 seconds
 146 |     st.session_state.syscall_history.pop(0)
 147 | 
 148 | # 2. Top KPIs
 149 | k1, k2, k3 = st.columns(3)
 150 | with k1:
 151 |     st.markdown(f"""
 152 |         <div class="metric-card">
 153 |             <h3 style="margin:0; color:#94a3b8; font-size:1rem;">Kernel Events / Sec</h3>
 154 |             <h1 style="margin:0; font-size:2.5rem;">{current_eps}</h1>
 155 |         </div>
 156 |     """, unsafe_allow_html=True)
 157 | with k2:
 158 |     alert_color = "#ef4444" if total_alerts > 0 else "#22c55e"
 159 |     st.markdown(f"""
 160 |         <div class="metric-card" style="border-left-color: {alert_color};">
 161 |             <h3 style="margin:0; color:#94a3b8; font-size:1rem;">Total Critical Alerts</h3>
 162 |             <h1 style="margin:0; font-size:2.5rem; color:{alert_color};">{total_alerts}</h1>
 163 |         </div>
 164 |     """, unsafe_allow_html=True)
 165 | with k3:
 166 |     status = "Active & Enforcing" if st.session_state.live_monitor else "Paused"
 167 |     st.markdown(f"""
 168 |         <div class="metric-card" style="border-left-color: #10b981;">
 169 |             <h3 style="margin:0; color:#94a3b8; font-size:1rem;">eBPF Engine Status</h3>
 170 |             <h1 style="margin:0; font-size:1.8rem; padding-top:10px; color:#10b981;">{status}</h1>
 171 |         </div>
 172 |     """, unsafe_allow_html=True)
 173 | 
 174 | st.markdown("<br>", unsafe_allow_html=True)
 175 | 
 176 | # 3. Main View: Chart on left, Alerts on right
 177 | col_chart, col_alerts = st.columns([2, 1])
 178 | 
 179 | with col_chart:
 180 |     st.markdown("### 📈 Live System Call Throughput")
 181 |     if len(st.session_state.syscall_history) > 1:
 182 |         df_history = pd.DataFrame(st.session_state.syscall_history)
 183 |         
 184 |         # Create the chart
 185 |         fig = px.area(df_history, x='time', y='events', 
 186 |                      color_discrete_sequence=['#3b82f6'],
 187 |                      template="plotly_dark")
 188 |         
 189 |         # Add red zones for attack periods (last 10 seconds after each attack)
 190 |         now = datetime.now()
 191 |         for attack_time in st.session_state.attack_events:
 192 |             time_diff = (now - attack_time).total_seconds()
 193 |             if time_diff < 10:
 194 |                 # Convert datetime to timestamp for plotly
 195 |                 attack_ts = attack_time.timestamp()
 196 |                 end_ts = min(attack_ts + 5, now.timestamp())
 197 |                 if end_ts > attack_ts:
 198 |                     fig.add_vrect(
 199 |                         x0=attack_ts, 
 200 |                         x1=end_ts,
 201 |                         fillcolor="rgba(239, 68, 68, 0.25)", 
 202 |                         opacity=0.25, 
 203 |                         line_width=0,
 204 |                         annotation_text="ATTACK", 
 205 |                         annotation_position="top left",
 206 |                         annotation_font_color="red"
 207 |                     )
 208 |         
 209 |         fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=350,
 210 |                           xaxis_title="", yaxis_title="Events / Sec")
 211 |         st.plotly_chart(fig, use_container_width=True)
 212 |     else:
 213 |         st.info("Gathering kernel telemetry...")
 214 | 
 215 | with col_alerts:
 216 |     st.markdown("### 🚨 Live Threat Feed")
 217 |     if not df_alerts.empty:
 218 |         # Show top 4 most recent alerts
 219 |         for _, row in df_alerts.head(4).iterrows():
 220 |             reasons = ", ".join(row['reasons']) if isinstance(row['reasons'], list) else row['reasons']
 221 |             st.markdown(f"""
 222 |                 <div class="alert-critical">
 223 |                     <div style="font-size: 0.8rem; color: #fca5a5;">{row['timestamp']}</div>
 224 |                     <strong style="font-size: 1.1rem;">PID {row['pid']} - {row.get('severity', 'CRITICAL').upper()}</strong><br>
 225 |                     <span style="font-size: 0.9rem;">{reasons}</span>
 226 |                 </div>
 227 |             """, unsafe_allow_html=True)
 228 |         if len(df_alerts) > 4:
 229 |             st.caption(f"+ {len(df_alerts) - 4} older alerts hidden.")
 230 |     else:
 231 |         st.markdown("""
 232 |             <div style="padding:20px; text-align:center; color:#94a3b8; border: 1px dashed #334155; border-radius: 5px;">
 233 |                 ✅ System is secure. No anomalous activity detected.
 234 |             </div>
 235 |         """, unsafe_allow_html=True)
 236 | 
 237 | # 4. Auto-refresh loop
 238 | if st.session_state.live_monitor:
 239 |     time.sleep(1.5)
 240 |     st.rerun()
```

### detector/signature.py

```python
   1 | import re
   2 | import logging
   3 | from typing import List, Dict, Optional, Any
   4 | 
   5 | logger = logging.getLogger(__name__)
   6 | 
   7 | class SignatureDetector:
   8 |     """
   9 |     Implements fast signature-based detection (Section 2.2).
  10 |     Checks for sensitive file access and known malicious patterns.
  11 |     """
  12 |     
  13 |     def __init__(self):
  14 |         # High-priority sensitive paths (IOCs)
  15 |         self.critical_paths = [
  16 |             re.compile(r'^/etc/shadow$'),
  17 |             re.compile(r'^/etc/sudoers$'),
  18 |             re.compile(r'^/var/run/docker\.sock$'),
  19 |             re.compile(r'^/root/.ssh/.*'),
  20 |             re.compile(r'^/proc/kcore$')
  21 |         ]
  22 |         
  23 |         # Suspicious patterns (e.g., shell access from web server)
  24 |         self.suspicious_comm = ["bash", "sh", "nc", "ncat", "python", "perl"]
  25 | 
  26 |     def analyze_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
  27 |         """
  28 |         Quickly scans an event for signature matches.
  29 |         """
  30 |         filename = event.get("filename") or ""
  31 |         comm = event.get("comm") or ""
  32 |         
  33 |         if not filename:
  34 |             return None
  35 |         
  36 |         # Check for sensitive path access
  37 |         for pattern in self.critical_paths:
  38 |             if pattern.match(filename):
  39 |                 return {
  40 |                     "type": "SIGNATURE_MATCH",
  41 |                     "reason": f"Access to critical file: {filename}",
  42 |                     "severity": "critical",
  43 |                     "ioc": filename
  44 |                 }
  45 |         
  46 |         # Check for suspicious process execution (simplified)
  47 |         # In a real impl, we'd check if a non-shell process spawns a shell
  48 |         if any(s in comm for s in self.suspicious_comm):
  49 |             # This is a heuristic, should be combined with context
  50 |             if "/bin/" in filename or "/usr/bin/" in filename:
  51 |                 return {
  52 |                     "type": "HEURISTIC_MATCH",
  53 |                     "reason": f"Suspicious process activity: {comm}",
  54 |                     "severity": "warning"
  55 |                 }
  56 |                 
  57 |         return None
```

### detector/statistical.py

```python
   1 | import numpy as np
   2 | import logging
   3 | from typing import Any, Dict, Optional, List
   4 | from src.metrics.engine import MetricsEngine
   5 | 
   6 | logger = logging.getLogger(__name__)
   7 | 
   8 | class StatisticalDetector:
   9 |     """
  10 |     Implements the Statistical Module from Section 2.2.
  11 |     Evaluates process behavior based on Z-scores and vector distances.
  12 |     """
  13 |     
  14 |     def __init__(self, engine: MetricsEngine, threshold_z: float = 3.0):
  15 |         self.engine = engine
  16 |         self.threshold_z = threshold_z
  17 | 
  18 |     def evaluate(self, pid: int, current_metrics: np.ndarray) -> Dict[str, Any]:
  19 |         """
  20 |         Analyzes the current metrics vector for a PID.
  21 |         
  22 |         Returns:
  23 |             A report containing anomaly status and specific scores.
  24 |         """
  25 |         z_scores = self.engine.get_z_scores(pid, current_metrics)
  26 |         max_z = np.max(np.abs(z_scores)) if z_scores.size > 0 else 0.0
  27 |         
  28 |         is_anomalous = max_z > self.threshold_z if self.threshold_z > 0 else False
  29 |         
  30 |         prof = self.engine.profiles.get(pid)
  31 |         distance = 0.0
  32 |         if prof is not None and current_metrics.size > 0:
  33 |             distance = np.linalg.norm(current_metrics - prof["mu"])
  34 | 
  35 |         return {
  36 |             "pid": pid,
  37 |             "is_anomalous": bool(is_anomalous),
  38 |             "max_z_score": float(max_z),
  39 |             "z_vector": z_scores.tolist(),
  40 |             "euclidean_distance": float(distance),
  41 |             "severity": self._map_to_severity(max_z)
  42 |         }
  43 | 
  44 |     def _map_to_severity(self, z_score: float) -> str:
  45 |         if z_score < self.threshold_z:
  46 |             return "info"
  47 |         elif z_score >= self.threshold_z * 2:
  48 |             return "critical"
  49 |         elif z_score >= self.threshold_z:
  50 |             return "warning"
  51 |         else:
  52 |             return "info"
```

### docker/resolver.py

```python
   1 | import logging
   2 | import os
   3 | import threading
   4 | from typing import Dict, Optional, Any
   5 | import docker
   6 | from docker.errors import DockerException
   7 | 
   8 | logger = logging.getLogger(__name__)
   9 | 
  10 | class ContainerResolver:
  11 |     """
  12 |     Maps Linux cgroup IDs to Docker container metadata.
  13 |     Implements a thread-safe cache to minimize overhead of Docker API calls.
  14 |     """
  15 |     
  16 |     def __init__(self, socket_path: str = "unix://var/run/docker.sock", target_label: str = None):
  17 |         self.target_label = target_label or os.environ.get("TARGET_LABEL")
  18 |         try:
  19 |             self.client = docker.DockerClient(base_url=socket_path)
  20 |             self._cache: Dict[int, Dict[str, Any]] = {}
  21 |             self._lock = threading.RLock()
  22 |             logger.info("ContainerResolver initialized with Docker socket: %s, target_label: %s", 
  23 |                       socket_path, self.target_label)
  24 |         except DockerException as e:
  25 |             logger.error("Failed to connect to Docker daemon: %s", e)
  26 |             self.client = None
  27 | 
  28 |     def _container_matches_label(self, container) -> bool:
  29 |         """Check if container has the target label."""
  30 |         if not self.target_label:
  31 |             return True
  32 |         label_key, label_value = self.target_label.split("=") if "=" in self.target_label else (self.target_label, "")
  33 |         container_labels = container.labels or {}
  34 |         actual_value = container_labels.get(label_key)
  35 |         if label_value:
  36 |             return actual_value == label_value
  37 |         return label_key in container_labels
  38 | 
  39 |     def resolve(self, cgroup_id: int) -> Optional[Dict[str, Any]]:
  40 |         """
  41 |         Resolves a cgroup_id to container metadata.
  42 |         
  43 |         Args:
  44 |             cgroup_id: The 64-bit cgroup identifier from eBPF.
  45 |             
  46 |         Returns:
  47 |             A dictionary with container info or None if not found/error.
  48 |         """
  49 |         if not self.client:
  50 |             return None
  51 | 
  52 |         with self._lock:
  53 |             if cgroup_id in self._cache:
  54 |                 return self._cache[cgroup_id]
  55 | 
  56 |         return self._refresh_and_resolve(cgroup_id)
  57 | 
  58 |     def _refresh_and_resolve(self, target_cgroup_id: int) -> Optional[Dict[str, Any]]:
  59 |         """
  60 |         Refreshes the internal cache by enumerating running containers.
  61 |         In a high-churn environment, this could be optimized to use Docker events.
  62 |         """
  63 |         try:
  64 |             containers = self.client.containers.list()
  65 |             new_cache = {}
  66 |             
  67 |             for container in containers:
  68 |                 if not self._container_matches_label(container):
  69 |                     continue
  70 |                 try:
  71 |                     # Basic metadata
  72 |                     meta = {
  73 |                         "id": container.id,
  74 |                         "name": container.name,
  75 |                         "image": container.image.tags[0] if container.image.tags else "unknown",
  76 |                         "labels": container.labels
  77 |                     }
  78 |                     
  79 |                     # Implementation detail: Extracting the numeric cgroup ID
  80 |                     # requires reading /sys/fs/cgroup/... or using a heuristic.
  81 |                     # For the purpose of the Stage 4 skeleton, we store by name.
  82 |                     # Real-world eBPF agents often use a BPF map populated by 
  83 |                     # a sidecar or by this resolver upon container start.
  84 |                     
  85 |                     # Placeholder: In a production senior-level impl, we'd match 
  86 |                     # container.attrs['State']['Pid'] to its cgroup inode.
  87 |                     # Here we simulate the successful resolution.
  88 |                     new_cache[target_cgroup_id] = meta # Simplified for demo
  89 |                 except (KeyError, IndexError):
  90 |                     continue
  91 | 
  92 |             with self._lock:
  93 |                 self._cache.update(new_cache)
  94 |                 return self._cache.get(target_cgroup_id)
  95 | 
  96 |         except DockerException as e:
  97 |             logger.error("Error refreshing container cache: %s", e)
  98 |             return None
  99 | 
 100 |     def clear_cache(self):
 101 |         with self._lock:
 102 |             self._cache.clear()
```

### ebpf_agent.py

```python
   1 | import ctypes
   2 | import os
   3 | import threading
   4 | import queue
   5 | from dataclasses import dataclass
   6 | 
   7 | # Define the event structure matching tracer.bpf.c
   8 | class Event(ctypes.Structure):
   9 |     _fields_ = [
  10 |         ("pid", ctypes.c_uint32),
  11 |         ("tgid", ctypes.c_uint32),
  12 |         ("cgroup_id", ctypes.c_uint64),
  13 |         ("syscall_id", ctypes.c_uint32),
  14 |         ("comm", ctypes.c_char * 16),
  15 |         ("filename", ctypes.c_char * 256),
  16 |     ]
  17 | 
  18 | # Callback type for the C loader
  19 | EVENT_CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(Event), ctypes.c_size_t)
  20 | 
  21 | class EBPFAgent:
  22 |     def __init__(self, lib_path="./ebpf/libloader.so"):
  23 |         self.lib = ctypes.CDLL(os.path.abspath(lib_path))
  24 |         self.event_queue = queue.Queue()
  25 |         
  26 |         self.lib.start_loader.argtypes = [EVENT_CB]
  27 |         self.lib.start_loader.restype = ctypes.c_int
  28 |         
  29 |         self.lib.poll_events.argtypes = [ctypes.c_int]
  30 |         self.lib.poll_events.restype = ctypes.c_int
  31 |         
  32 |         self.lib.stop_loader.argtypes = []
  33 |         self.lib.stop_loader.restype = None
  34 |         
  35 |         self._callback_ref = EVENT_CB(self._event_handler)
  36 |         self.running = False
  37 |         self.thread = None
  38 | 
  39 |     def _event_handler(self, ctx, event_ptr, size):
  40 |         event = event_ptr.contents
  41 |         # Copy data out of the BPF ring buffer to the Python queue
  42 |         self.event_queue.put({
  43 |             "pid": event.pid,
  44 |             "tgid": event.tgid,
  45 |             "cgroup_id": event.cgroup_id,
  46 |             "syscall_id": event.syscall_id,
  47 |             "comm": event.comm.decode('utf-8', 'replace'),
  48 |             "filename": event.filename.decode('utf-8', 'replace')
  49 |         })
  50 | 
  51 |     def start(self):
  52 |         err = self.lib.start_loader(self._callback_ref)
  53 |         if err != 0:
  54 |             raise RuntimeError(f"Failed to start eBPF loader: {err}")
  55 |         
  56 |         self.running = True
  57 |         self.thread = threading.Thread(target=self._poll_loop, daemon=True)
  58 |         self.thread.start()
  59 | 
  60 |     def _poll_loop(self):
  61 |         while self.running:
  62 |             self.lib.poll_events(100) # 100ms timeout
  63 | 
  64 |     def stop(self):
  65 |         self.running = False
  66 |         if self.thread:
  67 |             self.thread.join()
  68 |         self.lib.stop_loader()
  69 | 
  70 |     def get_event(self, block=True, timeout=None):
  71 |         try:
  72 |             return self.event_queue.get(block=block, timeout=timeout)
  73 |         except queue.Empty:
  74 |             return None
  75 | 
  76 | if __name__ == "__main__":
  77 |     # Basic test if run directly
  78 |     import time
  79 |     agent = EBPFAgent()
  80 |     print("Starting agent... (requires root/CAP_BPF)")
  81 |     try:
  82 |         agent.start()
  83 |         print("Monitoring... Press Ctrl+C to stop")
  84 |         while True:
  85 |             event = agent.get_event(timeout=1)
  86 |             if event:
  87 |                 print(f"Event: {event}")
  88 |     except KeyboardInterrupt:
  89 |         pass
  90 |     finally:
  91 |         agent.stop()
```

### graph/builder.py

```python
   1 | import networkx as nx
   2 | import logging
   3 | from typing import Dict, Any, Optional
   4 | from datetime import datetime
   5 | 
   6 | logger = logging.getLogger(__name__)
   7 | 
   8 | class ProvenanceGraphBuilder:
   9 |     """
  10 |     Constructs a directed provenance graph (Section 2.2).
  11 |     Nodes: Processes, Files, Sockets.
  12 |     Edges: Actions (open, read, write).
  13 |     """
  14 |     
  15 |     def __init__(self):
  16 |         self.graph = nx.DiGraph()
  17 |         logger.info("ProvenanceGraphBuilder initialized.")
  18 | 
  19 |     def add_event(self, event: Dict[str, Any]):
  20 |         """
  21 |         Adds an event to the graph. 
  22 |         Event structure: pid, comm, filename, syscall_id, timestamp
  23 |         """
  24 |         pid = event.get("pid")
  25 |         comm = event.get("comm", "unknown")
  26 |         filename = event.get("filename", "")
  27 |         syscall = event.get("syscall_id")
  28 |         
  29 |         # Process node
  30 |         proc_node = f"proc_{pid}"
  31 |         if not self.graph.has_node(proc_node):
  32 |             self.graph.add_node(proc_node, type="process", pid=pid, comm=comm)
  33 |             
  34 |         # Resource node (if applicable)
  35 |         if filename:
  36 |             res_node = f"file_{filename}"
  37 |             if not self.graph.has_node(res_node):
  38 |                 self.graph.add_node(res_node, type="file", path=filename)
  39 |             
  40 |             # Add edge representing the action
  41 |             self.graph.add_edge(
  42 |                 proc_node, 
  43 |                 res_node, 
  44 |                 syscall=syscall, 
  45 |                 timestamp=datetime.now().isoformat()
  46 |             )
  47 | 
  48 |     def get_process_subgraph(self, pid: int) -> nx.DiGraph:
  49 |         """
  50 |         Returns the neighborhood of a specific process.
  51 |         """
  52 |         proc_node = f"proc_{pid}"
  53 |         if not self.graph.has_node(proc_node):
  54 |             return nx.DiGraph()
  55 |             
  56 |         nodes = [proc_node] + list(self.graph.neighbors(proc_node))
  57 |         return self.graph.subgraph(nodes)
  58 | 
  59 |     def get_serialized_graph(self) -> Dict[str, Any]:
  60 |         """
  61 |         Serializes the graph for UI consumption (e.g., cytoscape or d3 format).
  62 |         """
  63 |         return nx.node_link_data(self.graph)
  64 | 
  65 |     def clear(self):
  66 |         self.graph.clear()
```

### main_agent.py

```python
   1 | import time, sys, os, json, dataclasses
   2 | from pathlib import Path
   3 | 
   4 | sys.path.insert(0, str(Path(__file__).parent.parent))
   5 | from src.ebpf_agent import EBPFAgent
   6 | from src.detector.signature import SignatureDetector
   7 | from src.scoring.engine import ScoringEngine
   8 | from src.storage.sqlite import StorageManager
   9 | 
  10 | def run_agent():
  11 |     print("🛡️ Starting SovND Real-time eBPF Engine...")
  12 |     lib_path = Path(__file__).parent.parent / "ebpf" / "libloader.so"
  13 |     
  14 |     agent = EBPFAgent(lib_path=str(lib_path))
  15 |     sig_detector = SignatureDetector()
  16 |     scoring = ScoringEngine(threshold=10.0)
  17 |     storage = StorageManager()
  18 | 
  19 |     # Clear old data for demo freshness
  20 |     storage.clear_alerts()
  21 | 
  22 |     try:
  23 |         agent.start()
  24 |         print("✅ eBPF Agent attached. Monitoring...")
  25 |         events_this_second = 0
  26 |         last_heartbeat = time.time()
  27 |         
  28 |         while True:
  29 |             current_time = time.time()
  30 |             if current_time - last_heartbeat >= 1.0:
  31 |                 with open("data/heartbeat.json", "w") as f:
  32 |                     json.dump({"events_per_sec": events_this_second, "timestamp": current_time}, f)
  33 |                 os.chmod("data/heartbeat.json", 0o666)
  34 |                 events_this_second = 0
  35 |                 last_heartbeat = current_time
  36 | 
  37 |             event = agent.get_event(timeout=0.1)
  38 |             if event:
  39 |                 events_this_second += 1
  40 |                 sig_match = sig_detector.analyze_event(event)
  41 |                 if sig_match:
  42 |                     alert = scoring.compute_score(
  43 |                         event=event,
  44 |                         stat_report={"pid": event["pid"], "is_anomalous": False}, 
  45 |                         sig_match=sig_match,
  46 |                         graph_heuristics=[]
  47 |                     )
  48 |                     if alert:
  49 |                         storage.save_alert(dataclasses.asdict(alert))
  50 |                         try: os.chmod(storage.db_path, 0o666)
  51 |                         except: pass
  52 |                         print(f"🚨 ALERT: PID {event['pid']} [{event['comm']}]")
  53 |     except KeyboardInterrupt: pass
  54 |     finally: agent.stop()
  55 | 
  56 | if __name__ == "__main__":
  57 |     run_agent()
```

### metrics/engine.py

```python
   1 | # src/scoring/engine.py
   2 | from dataclasses import dataclass, asdict
   3 | from datetime import datetime
   4 | from typing import List, Dict, Any, Optional
   5 | 
   6 | @dataclass
   7 | class Alert:
   8 |     timestamp: str
   9 |     pid: int
  10 |     comm: str
  11 |     score: float
  12 |     severity: str
  13 |     reasons: List[str]
  14 |     # New: Explainable components of the formula S = sum(w_i * d_i)
  15 |     breakdown: Dict[str, float] 
  16 | 
  17 | class ScoringEngine:
  18 |     def __init__(self, threshold: float = 10.0):
  19 |         self.threshold = threshold
  20 |         self.weights = {"signature": 15.0, "statistical": 1.0, "graph": 5.0}
  21 | 
  22 |     def compute_score(self, event: Dict[str, Any], stat_report: Dict[str, Any], 
  23 |                       sig_match: Optional[Dict[str, Any]], 
  24 |                       graph_heuristics: List[str]) -> Optional[Alert]:
  25 |         
  26 |         comp = {"signature": 0.0, "statistical": 0.0, "graph": 0.0}
  27 |         reasons = []
  28 |         
  29 |         if sig_match:
  30 |             comp["signature"] = self.weights["signature"]
  31 |             reasons.append(sig_match['reason'])
  32 |             
  33 |         max_z = stat_report.get("max_z_score", 0.0)
  34 |         if stat_report.get("is_anomalous"):
  35 |             comp["statistical"] = self.weights["statistical"] * max_z
  36 |             reasons.append(f"Statistical Anomaly (Z={max_z:.1f})")
  37 |             
  38 |         for h in graph_heuristics:
  39 |             comp["graph"] += self.weights["graph"]
  40 |             reasons.append(f"Graph Heuristic: {h}")
  41 | 
  42 |         total_score = sum(comp.values())
  43 | 
  44 |         if total_score >= self.threshold:
  45 |             return Alert(
  46 |                 timestamp=datetime.now().isoformat(),
  47 |                 pid=event["pid"],
  48 |                 comm=event.get("comm", "unknown"),
  49 |                 score=round(total_score, 2),
  50 |                 severity="CRITICAL" if total_score > 20 else "WARNING",
  51 |                 reasons=reasons,
  52 |                 breakdown=comp
  53 |             )
  54 |         return None
```

### scoring/engine.py

```python
   1 | from dataclasses import dataclass, asdict
   2 | from datetime import datetime
   3 | from typing import List, Dict, Any, Optional
   4 | 
   5 | @dataclass
   6 | class Alert:
   7 |     timestamp: str
   8 |     pid: int
   9 |     comm: str
  10 |     score: float
  11 |     severity: str
  12 |     reasons: List[str]
  13 |     breakdown: Dict[str, float] 
  14 | 
  15 | class ScoringEngine:
  16 |     def __init__(self, threshold: float = 10.0):
  17 |         self.threshold = threshold
  18 |         self.weights = {"signature": 15.0, "statistical": 1.0, "graph": 5.0}
  19 | 
  20 |     def compute_score(self, event: Dict[str, Any], stat_report: Dict[str, Any], 
  21 |                       sig_match: Optional[Dict[str, Any]], 
  22 |                       graph_heuristics: List[str]) -> Optional[Alert]:
  23 |         
  24 |         comp = {"signature": 0.0, "statistical": 0.0, "graph": 0.0}
  25 |         reasons = []
  26 |         
  27 |         if sig_match:
  28 |             comp["signature"] = self.weights["signature"]
  29 |             reasons.append(sig_match['reason'])
  30 |             
  31 |         max_z = stat_report.get("max_z_score", 0.0)
  32 |         if stat_report.get("is_anomalous"):
  33 |             comp["statistical"] = self.weights["statistical"] * max_z
  34 |             reasons.append(f"Statistical Anomaly (Z={max_z:.1f})")
  35 |             
  36 |         for h in graph_heuristics:
  37 |             comp["graph"] += self.weights["graph"]
  38 |             reasons.append(f"Graph Heuristic: {h}")
  39 | 
  40 |         total_score = sum(comp.values())
  41 | 
  42 |         if total_score >= self.threshold:
  43 |             return Alert(
  44 |                 timestamp=datetime.now().isoformat(),
  45 |                 pid=event["pid"],
  46 |                 comm=event.get("comm", "unknown"),
  47 |                 score=round(total_score, 2),
  48 |                 severity="CRITICAL" if total_score > 20 else "WARNING",
  49 |                 reasons=reasons,
  50 |                 breakdown=comp
  51 |             )
  52 |         return None
```

### storage/sqlite.py

```python
   1 | import sqlite3
   2 | import json
   3 | import logging
   4 | import os
   5 | import threading
   6 | from typing import List, Dict, Any, Optional
   7 | from datetime import datetime
   8 | from contextlib import contextmanager
   9 | 
  10 | logger = logging.getLogger(__name__)
  11 | 
  12 | class StorageManager:
  13 |     """
  14 |     Handles persistence for security profiles and alerts (Section 3.2).
  15 |     Uses a thread-safe connection pattern and context managers.
  16 |     """
  17 |     
  18 |     def __init__(self, db_path: str = None):
  19 |         self.db_path = db_path or os.environ.get("DB_PATH", "data/sovnd.db")
  20 |         self._lock = threading.Lock()
  21 |         self._init_db()
  22 | 
  23 |     @contextmanager
  24 |     def _get_connection(self):
  25 |         conn = sqlite3.connect(self.db_path)
  26 |         conn.row_factory = sqlite3.Row
  27 |         try:
  28 |             yield conn
  29 |         finally:
  30 |             conn.close()
  31 | 
  32 |     def _init_db(self):
  33 |         """Initializes the database schema."""
  34 |         os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else "data", exist_ok=True)
  35 |         with self._get_connection() as conn:
  36 |             conn.execute("""
  37 |                 CREATE TABLE IF NOT EXISTS profiles (
  38 |                     id INTEGER PRIMARY KEY AUTOINCREMENT,
  39 |                     identifier TEXT UNIQUE, -- e.g., process name or container image
  40 |                     mu BLOB,
  41 |                     sigma BLOB,
  42 |                     last_updated TIMESTAMP
  43 |                 )
  44 |             """)
  45 |             conn.execute("""
  46 |                 CREATE TABLE IF NOT EXISTS alerts (
  47 |                     id INTEGER PRIMARY KEY AUTOINCREMENT,
  48 |                     timestamp TIMESTAMP,
  49 |                     pid INTEGER,
  50 |                     comm TEXT,
  51 |                     score REAL,
  52 |                     severity TEXT,
  53 |                     reasons TEXT,       -- JSON string
  54 |                     breakdown TEXT     -- JSON string
  55 |                 )
  56 |             """)
  57 |             conn.commit()
  58 |         try:
  59 |             os.chmod(self.db_path, 0o644)
  60 |         except PermissionError:
  61 |             pass
  62 |         logger.info("Database initialized at %s", self.db_path)
  63 | 
  64 |     def save_alert(self, alert_data: Dict[str, Any]):
  65 |         """Persists a generated alert."""
  66 |         with self._lock:
  67 |             with self._get_connection() as conn:
  68 |                 conn.execute(
  69 |                     "INSERT INTO alerts (timestamp, pid, comm, score, severity, reasons, breakdown) VALUES (?, ?, ?, ?, ?, ?, ?)",
  70 |                     (
  71 |                         alert_data.get("timestamp"),
  72 |                         alert_data.get("pid"),
  73 |                         alert_data.get("comm", "unknown"),
  74 |                         alert_data.get("score"),
  75 |                         alert_data.get("severity"),
  76 |                         json.dumps(alert_data.get("reasons")),
  77 |                         json.dumps(alert_data.get("breakdown", {}))
  78 |                     )
  79 |                 )
  80 |                 conn.commit()
  81 |         try:
  82 |             os.chmod(self.db_path, 0o644)
  83 |         except PermissionError:
  84 |             pass
  85 | 
  86 |     def get_recent_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
  87 |         """Retrieves most recent security alerts."""
  88 |         with self._get_connection() as conn:
  89 |             cursor = conn.execute(
  90 |                 "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,)
  91 |             )
  92 |             rows = cursor.fetchall()
  93 |             alerts = []
  94 |             for row in rows:
  95 |                 alert = dict(row)
  96 |                 alert["reasons"] = json.loads(alert["reasons"]) if alert["reasons"] else []
  97 |                 alert["breakdown"] = json.loads(alert["breakdown"]) if alert["breakdown"] else {}
  98 |                 alerts.append(alert)
  99 |             return alerts
 100 | 
 101 |     def save_profile(self, identifier: str, mu: bytes, sigma: bytes):
 102 |         """Saves or updates a behavioral profile."""
 103 |         with self._lock:
 104 |             with self._get_connection() as conn:
 105 |                 conn.execute("""
 106 |                     INSERT INTO profiles (identifier, mu, sigma, last_updated)
 107 |                     VALUES (?, ?, ?, ?)
 108 |                     ON CONFLICT(identifier) DO UPDATE SET
 109 |                         mu=excluded.mu,
 110 |                         sigma=excluded.sigma,
 111 |                         last_updated=excluded.last_updated
 112 |                 """, (identifier, mu, sigma, datetime.now().isoformat()))
 113 |                 conn.commit()
 114 | 
 115 |     def get_profile(self, identifier: str) -> Optional[Dict[str, Any]]:
 116 |         """Retrieves a behavioral profile by identifier."""
 117 |         with self._get_connection() as conn:
 118 |             cursor = conn.execute(
 119 |                 "SELECT * FROM profiles WHERE identifier = ?", (identifier,)
 120 |             )
 121 |             row = cursor.fetchone()
 122 |             return dict(row) if row else None
 123 | 
 124 |     def clear_alerts(self):
 125 |         """Clears all alerts from the database."""
 126 |         with self._lock:
 127 |             with self._get_connection() as conn:
 128 |                 conn.execute("DELETE FROM alerts")
 129 |                 conn.commit()
 130 |         try:
 131 |             os.chmod(self.db_path, 0o644)
 132 |         except PermissionError:
 133 |             pass
 134 |         logger.info("All alerts cleared")
```

## eBPF (ebpf/)

### fd_tracker.bpf.c

```c
   1 | #include "vmlinux.h"
   2 | #include <bpf/bpf_helpers.h>
   3 | #include "maps.bpf.h"
   4 | 
   5 | // Logic for tracking open FDs
```

### filter.bpf.c

```c
   1 | #include "vmlinux.h"
   2 | #include <bpf/bpf_helpers.h>
   3 | #include "maps.bpf.h"
   4 | 
   5 | // Logic for dropping events from non-target PIDs
   6 | // This can be expanded with more complex filtering rules
```

### loader.c

```c
   1 | #include <stdio.h>
   2 | #include <stdlib.h>
   3 | #include <string.h>
   4 | #include <errno.h>
   5 | #include <getopt.h>
   6 | #include <sys/resource.h>
   7 | #include <bpf/libbpf.h>
   8 | #include <bpf/bpf.h>
   9 | #include "tracer.skel.h"
  10 | 
  11 | static int libbpf_print_fn(enum libbpf_print_level level, const char *format, va_list args)
  12 | {
  13 |     return vfprintf(stderr, format, args);
  14 | }
  15 | 
  16 | struct tracer_bpf *skel;
  17 | struct ring_buffer *rb = NULL;
  18 | 
  19 | typedef void (*event_cb_t)(void *ctx, void *data, size_t size);
  20 | event_cb_t user_callback = NULL;
  21 | 
  22 | static int handle_event(void *ctx, void *data, size_t data_sz)
  23 | {
  24 |     if (user_callback) {
  25 |         user_callback(ctx, data, data_sz);
  26 |     }
  27 |     return 0;
  28 | }
  29 | 
  30 | int start_loader(event_cb_t cb)
  31 | {
  32 |     int err;
  33 | 
  34 |     user_callback = cb;
  35 |     libbpf_set_print(libbpf_print_fn);
  36 | 
  37 |     skel = tracer_bpf__open();
  38 |     if (!skel) {
  39 |         fprintf(stderr, "Failed to open BPF skeleton\n");
  40 |         return 1;
  41 |     }
  42 | 
  43 |     err = tracer_bpf__load(skel);
  44 |     if (err) {
  45 |         fprintf(stderr, "Failed to load BPF skeleton\n");
  46 |         goto cleanup;
  47 |     }
  48 | 
  49 |     err = tracer_bpf__attach(skel);
  50 |     if (err) {
  51 |         fprintf(stderr, "Failed to attach BPF skeleton\n");
  52 |         goto cleanup;
  53 |     }
  54 | 
  55 |     rb = ring_buffer__new(bpf_map__fd(skel->maps.rb), handle_event, NULL, NULL);
  56 |     if (!rb) {
  57 |         err = -1;
  58 |         fprintf(stderr, "Failed to create ring buffer\n");
  59 |         goto cleanup;
  60 |     }
  61 | 
  62 |     return 0;
  63 | 
  64 | cleanup:
  65 |     tracer_bpf__destroy(skel);
  66 |     return err;
  67 | }
  68 | 
  69 | int poll_events(int timeout_ms)
  70 | {
  71 |     return ring_buffer__poll(rb, timeout_ms);
  72 | }
  73 | 
  74 | void stop_loader()
  75 | {
  76 |     ring_buffer__free(rb);
  77 |     tracer_bpf__destroy(skel);
  78 | }
```

### maps.bpf.h

```c
   1 | #ifndef __MAPS_BPF_H
   2 | #define __MAPS_BPF_H
   3 | 
   4 | #include "vmlinux.h"
   5 | #include <bpf/bpf_helpers.h>
   6 | 
   7 | /* Ring buffer for sending events to user space */
   8 | struct {
   9 |     __uint(type, BPF_MAP_TYPE_RINGBUF);
  10 |     __uint(max_entries, 256 * 1024);
  11 | } rb SEC(".maps");
  12 | 
  13 | /* Hash map for storing process metrics in kernel space */
  14 | struct {
  15 |     __uint(type, BPF_MAP_TYPE_HASH);
  16 |     __uint(max_entries, 10240);
  17 |     __type(key, __u32);   /* PID */
  18 |     __type(value, __u64); /* Metric counter (e.g., syscall count) */
  19 | } proc_metrics SEC(".maps");
  20 | 
  21 | /* Map to store container ID (cgroup id) to metadata mapping if needed */
  22 | struct {
  23 |     __uint(type, BPF_MAP_TYPE_HASH);
  24 |     __uint(max_entries, 1024);
  25 |     __type(key, __u64);   /* cgroup id */
  26 |     __type(value, __u32); /* Placeholder for metadata/flags */
  27 | } container_map SEC(".maps");
  28 | 
  29 | #endif /* __MAPS_BPF_H */
```

### tracer.bpf.c

```c
   1 | #include "vmlinux.h"
   2 | #include <bpf/bpf_helpers.h>
   3 | #include <bpf/bpf_tracing.h>
   4 | #include <bpf/bpf_core_read.h>
   5 | #include "maps.bpf.h"
   6 | 
   7 | char LICENSE[] SEC("license") = "GPL";
   8 | 
   9 | struct event {
  10 |     __u32 pid;
  11 |     __u32 tgid;
  12 |     __u64 cgroup_id;
  13 |     __u32 syscall_id;
  14 |     char comm[16];
  15 |     char filename[256];
  16 | };
  17 | 
  18 | SEC("tracepoint/syscalls/sys_enter_openat")
  19 | int trace_openat(struct trace_event_raw_sys_enter *ctx) {
  20 |     struct event *e;
  21 |     __u64 id = bpf_get_current_pid_tgid();
  22 |     __u32 pid = id >> 32;
  23 | 
  24 |     e = bpf_ringbuf_reserve(&rb, sizeof(*e), 0);
  25 |     if (!e)
  26 |         return 0;
  27 | 
  28 |     e->pid = pid;
  29 |     e->tgid = id;
  30 |     e->cgroup_id = bpf_get_current_cgroup_id();
  31 |     e->syscall_id = 257; // openat
  32 |     bpf_get_current_comm(&e->comm, sizeof(e->comm));
  33 |     
  34 |     const char *pathname = (const char *)ctx->args[1];
  35 |     bpf_probe_read_user_str(&e->filename, sizeof(e->filename), pathname);
  36 |     
  37 |     bpf_ringbuf_submit(e, 0);
  38 | 
  39 |     __u64 *count, one = 1;
  40 |     count = bpf_map_lookup_elem(&proc_metrics, &pid);
  41 |     if (count) {
  42 |         __sync_fetch_and_add(count, 1);
  43 |     } else {
  44 |         bpf_map_update_elem(&proc_metrics, &pid, &one, BPF_ANY);
  45 |     }
  46 | 
  47 |     return 0;
  48 | }
  49 | 
  50 | SEC("tracepoint/syscalls/sys_enter_close")
  51 | int trace_close(struct trace_event_raw_sys_enter *ctx) {
  52 |     // Similar logic for close
  53 |     return 0;
  54 | }
```

### tracer.skel.h

```c
   1 | /* SPDX-License-Identifier: (LGPL-2.1 OR BSD-2-Clause) */
   2 | 
   3 | /* THIS FILE IS AUTOGENERATED BY BPFTOOL! */
   4 | #ifndef __TRACER_BPF_SKEL_H__
   5 | #define __TRACER_BPF_SKEL_H__
   6 | 
   7 | #include <errno.h>
   8 | #include <stdlib.h>
   9 | #include <bpf/libbpf.h>
  10 | 
  11 | #define BPF_SKEL_SUPPORTS_MAP_AUTO_ATTACH 1
  12 | 
  13 | struct tracer_bpf {
  14 | 	struct bpf_object_skeleton *skeleton;
  15 | 	struct bpf_object *obj;
  16 | 	struct {
  17 | 		struct bpf_map *rb;
  18 | 		struct bpf_map *proc_metrics;
  19 | 		struct bpf_map *container_map;
  20 | 	} maps;
  21 | 	struct {
  22 | 		struct bpf_program *trace_openat;
  23 | 		struct bpf_program *trace_close;
  24 | 	} progs;
  25 | 	struct {
  26 | 		struct bpf_link *trace_openat;
  27 | 		struct bpf_link *trace_close;
  28 | 	} links;
  29 | 
  30 | #ifdef __cplusplus
  31 | 	static inline struct tracer_bpf *open(const struct bpf_object_open_opts *opts = nullptr);
  32 | 	static inline struct tracer_bpf *open_and_load();
  33 | 	static inline int load(struct tracer_bpf *skel);
  34 | 	static inline int attach(struct tracer_bpf *skel);
  35 | 	static inline void detach(struct tracer_bpf *skel);
  36 | 	static inline void destroy(struct tracer_bpf *skel);
  37 | 	static inline const void *elf_bytes(size_t *sz);
  38 | #endif /* __cplusplus */
  39 | };
  40 | 
  41 | static void
  42 | tracer_bpf__destroy(struct tracer_bpf *obj)
  43 | {
  44 | 	if (!obj)
  45 | 		return;
  46 | 	if (obj->skeleton)
  47 | 		bpf_object__destroy_skeleton(obj->skeleton);
  48 | 	free(obj);
  49 | }
  50 | 
  51 | static inline int
  52 | tracer_bpf__create_skeleton(struct tracer_bpf *obj);
  53 | 
  54 | static inline struct tracer_bpf *
  55 | tracer_bpf__open_opts(const struct bpf_object_open_opts *opts)
  56 | {
  57 | 	struct tracer_bpf *obj;
  58 | 	int err;
  59 | 
  60 | 	obj = (struct tracer_bpf *)calloc(1, sizeof(*obj));
  61 | 	if (!obj) {
  62 | 		errno = ENOMEM;
  63 | 		return NULL;
  64 | 	}
  65 | 
  66 | 	err = tracer_bpf__create_skeleton(obj);
  67 | 	if (err)
  68 | 		goto err_out;
  69 | 
  70 | 	err = bpf_object__open_skeleton(obj->skeleton, opts);
  71 | 	if (err)
  72 | 		goto err_out;
  73 | 
  74 | 	return obj;
  75 | err_out:
  76 | 	tracer_bpf__destroy(obj);
  77 | 	errno = -err;
  78 | 	return NULL;
  79 | }
  80 | 
  81 | static inline struct tracer_bpf *
  82 | tracer_bpf__open(void)
  83 | {
  84 | 	return tracer_bpf__open_opts(NULL);
  85 | }
  86 | 
  87 | static inline int
  88 | tracer_bpf__load(struct tracer_bpf *obj)
  89 | {
  90 | 	return bpf_object__load_skeleton(obj->skeleton);
  91 | }
  92 | 
  93 | static inline struct tracer_bpf *
  94 | tracer_bpf__open_and_load(void)
  95 | {
  96 | 	struct tracer_bpf *obj;
  97 | 	int err;
  98 | 
  99 | 	obj = tracer_bpf__open();
 100 | 	if (!obj)
 101 | 		return NULL;
 102 | 	err = tracer_bpf__load(obj);
 103 | 	if (err) {
 104 | 		tracer_bpf__destroy(obj);
 105 | 		errno = -err;
 106 | 		return NULL;
 107 | 	}
 108 | 	return obj;
 109 | }
 110 | 
 111 | static inline int
 112 | tracer_bpf__attach(struct tracer_bpf *obj)
 113 | {
 114 | 	return bpf_object__attach_skeleton(obj->skeleton);
 115 | }
 116 | 
 117 | static inline void
 118 | tracer_bpf__detach(struct tracer_bpf *obj)
 119 | {
 120 | 	bpf_object__detach_skeleton(obj->skeleton);
 121 | }
 122 | 
 123 | static inline const void *tracer_bpf__elf_bytes(size_t *sz);
 124 | 
 125 | static inline int
 126 | tracer_bpf__create_skeleton(struct tracer_bpf *obj)
 127 | {
 128 | 	struct bpf_object_skeleton *s;
 129 | 	struct bpf_map_skeleton *map __attribute__((unused));
 130 | 	int err;
 131 | 
 132 | 	s = (struct bpf_object_skeleton *)calloc(1, sizeof(*s));
 133 | 	if (!s)	{
 134 | 		err = -ENOMEM;
 135 | 		goto err;
 136 | 	}
 137 | 
 138 | 	s->sz = sizeof(*s);
 139 | 	s->name = "tracer_bpf";
 140 | 	s->obj = &obj->obj;
 141 | 
 142 | 	/* maps */
 143 | 	s->map_cnt = 3;
 144 | 	s->map_skel_sz = 24;
 145 | 	s->maps = (struct bpf_map_skeleton *)calloc(s->map_cnt,
 146 | 			sizeof(*s->maps) > 24 ? sizeof(*s->maps) : 24);
 147 | 	if (!s->maps) {
 148 | 		err = -ENOMEM;
 149 | 		goto err;
 150 | 	}
 151 | 
 152 | 	map = (struct bpf_map_skeleton *)((char *)s->maps + 0 * s->map_skel_sz);
 153 | 	map->name = "rb";
 154 | 	map->map = &obj->maps.rb;
 155 | 
 156 | 	map = (struct bpf_map_skeleton *)((char *)s->maps + 1 * s->map_skel_sz);
 157 | 	map->name = "proc_metrics";
 158 | 	map->map = &obj->maps.proc_metrics;
 159 | 
 160 | 	map = (struct bpf_map_skeleton *)((char *)s->maps + 2 * s->map_skel_sz);
 161 | 	map->name = "container_map";
 162 | 	map->map = &obj->maps.container_map;
 163 | 
 164 | 	/* programs */
 165 | 	s->prog_cnt = 2;
 166 | 	s->prog_skel_sz = sizeof(*s->progs);
 167 | 	s->progs = (struct bpf_prog_skeleton *)calloc(s->prog_cnt, s->prog_skel_sz);
 168 | 	if (!s->progs) {
 169 | 		err = -ENOMEM;
 170 | 		goto err;
 171 | 	}
 172 | 
 173 | 	s->progs[0].name = "trace_openat";
 174 | 	s->progs[0].prog = &obj->progs.trace_openat;
 175 | 	s->progs[0].link = &obj->links.trace_openat;
 176 | 
 177 | 	s->progs[1].name = "trace_close";
 178 | 	s->progs[1].prog = &obj->progs.trace_close;
 179 | 	s->progs[1].link = &obj->links.trace_close;
 180 | 
 181 | 	s->data = tracer_bpf__elf_bytes(&s->data_sz);
 182 | 
 183 | 	obj->skeleton = s;
 184 | 	return 0;
 185 | err:
 186 | 	bpf_object__destroy_skeleton(s);
 187 | 	return err;
 188 | }
 189 | 
 190 | static inline const void *tracer_bpf__elf_bytes(size_t *sz)
 191 | {
 192 | 	static const char data[] __attribute__((__aligned__(8))) = "\
 193 | \x7f\x45\x4c\x46\x02\x01\x01\0\0\0\0\0\0\0\0\0\x01\0\xf7\0\x01\0\0\0\0\0\0\0\0\
 194 | \0\0\0\0\0\0\0\0\0\0\0\xc0\x22\0\0\0\0\0\0\0\0\0\0\x40\0\0\0\0\0\x40\0\x1d\0\
 195 | \x01\0\xbf\x16\0\0\0\0\0\0\x85\0\0\0\x0e\0\0\0\xbf\x07\0\0\0\0\0\0\xbf\x78\0\0\
 196 | \0\0\0\0\x77\x08\0\0\x20\0\0\0\x63\x8a\xfc\xff\0\0\0\0\x18\x01\0\0\0\0\0\0\0\0\
 197 | \0\0\0\0\0\0\xb7\x02\0\0\x28\x01\0\0\xb7\x03\0\0\0\0\0\0\x85\0\0\0\x83\0\0\0\
 198 | \x15\0\x25\0\0\0\0\0\x63\x70\x04\0\0\0\0\0\x63\x80\0\0\0\0\0\0\xbf\x07\0\0\0\0\
 199 | \0\0\x85\0\0\0\x50\0\0\0\xb7\x01\0\0\x01\x01\0\0\x63\x17\x10\0\0\0\0\0\x7b\x07\
 200 | \x08\0\0\0\0\0\xbf\x71\0\0\0\0\0\0\x07\x01\0\0\x14\0\0\0\xb7\x02\0\0\x10\0\0\0\
 201 | \x85\0\0\0\x10\0\0\0\x79\x63\x18\0\0\0\0\0\xbf\x71\0\0\0\0\0\0\x07\x01\0\0\x24\
 202 | \0\0\0\xb7\x02\0\0\0\x01\0\0\x85\0\0\0\x72\0\0\0\xbf\x71\0\0\0\0\0\0\xb7\x02\0\
 203 | \0\0\0\0\0\x85\0\0\0\x84\0\0\0\xb7\x06\0\0\x01\0\0\0\x7b\x6a\xf0\xff\0\0\0\0\
 204 | \xbf\xa2\0\0\0\0\0\0\x07\x02\0\0\xfc\xff\xff\xff\x18\x01\0\0\0\0\0\0\0\0\0\0\0\
 205 | \0\0\0\x85\0\0\0\x01\0\0\0\x15\0\x02\0\0\0\0\0\xdb\x60\0\0\0\0\0\0\x05\0\x08\0\
 206 | \0\0\0\0\xbf\xa2\0\0\0\0\0\0\x07\x02\0\0\xfc\xff\xff\xff\xbf\xa3\0\0\0\0\0\0\
 207 | \x07\x03\0\0\xf0\xff\xff\xff\x18\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\xb7\x04\0\0\0\
 208 | \0\0\0\x85\0\0\0\x02\0\0\0\xb7\0\0\0\0\0\0\0\x95\0\0\0\0\0\0\0\xb7\0\0\0\0\0\0\
 209 | \0\x95\0\0\0\0\0\0\0\x47\x50\x4c\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 210 | \0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 211 | \0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x4f\0\0\0\x05\0\x08\0\x05\0\0\0\
 212 | \x14\0\0\0\x22\0\0\0\x2a\0\0\0\x33\0\0\0\x3d\0\0\0\x01\x04\x04\0\x08\x01\x51\
 213 | \x04\x08\x80\x02\x01\x56\0\x01\x04\x04\x18\x78\x01\x57\0\x01\x04\x04\x58\x80\
 214 | \x01\x01\x50\0\x01\x04\x04\xc0\x01\xe0\x01\x01\x53\0\x01\x04\x04\xb0\x02\x88\
 215 | \x03\x01\x50\0\x01\x11\x01\x25\x25\x13\x05\x03\x25\x72\x17\x10\x17\x1b\x25\x11\
 216 | \x01\x55\x23\x73\x17\x74\x17\x8c\x01\x17\0\0\x02\x34\0\x03\x25\x49\x13\x3f\x19\
 217 | \x3a\x0b\x3b\x0b\x02\x18\0\0\x03\x01\x01\x49\x13\0\0\x04\x21\0\x49\x13\x37\x0b\
 218 | \0\0\x05\x24\0\x03\x25\x3e\x0b\x0b\x0b\0\0\x06\x24\0\x03\x25\x0b\x0b\x3e\x0b\0\
 219 | \0\x07\x13\x01\x0b\x0b\x3a\x0b\x3b\x0b\0\0\x08\x0d\0\x03\x25\x49\x13\x3a\x0b\
 220 | \x3b\x0b\x38\x0b\0\0\x09\x0f\0\x49\x13\0\0\x0a\x21\0\x49\x13\x37\x06\0\0\x0b\
 221 | \x21\0\x49\x13\x37\x05\0\0\x0c\x16\0\x49\x13\x03\x25\x3a\x0b\x3b\x05\0\0\x0d\
 222 | \x34\0\x03\x25\x49\x13\x3a\x0b\x3b\x05\x1c\x0f\0\0\x0e\x15\0\x49\x13\x27\x19\0\
 223 | \0\x0f\x15\x01\x49\x13\x27\x19\0\0\x10\x05\0\x49\x13\0\0\x11\x0f\0\0\0\x12\x26\
 224 | \0\0\0\x13\x15\x01\x27\x19\0\0\x14\x34\0\x03\x25\x49\x13\x3a\x0b\x3b\x0b\x1c\
 225 | \x0f\0\0\x15\x04\x01\x49\x13\x0b\x0b\x3a\x0b\x3b\x05\0\0\x16\x28\0\x03\x25\x1c\
 226 | \x0f\0\0\x17\x26\0\x49\x13\0\0\x18\x2e\x01\x11\x1b\x12\x06\x40\x18\x7a\x19\x03\
 227 | \x25\x3a\x0b\x3b\x0b\x27\x19\x49\x13\x3f\x19\0\0\x19\x05\0\x02\x22\x03\x25\x3a\
 228 | \x0b\x3b\x0b\x49\x13\0\0\x1a\x34\0\x02\x18\x03\x25\x3a\x0b\x3b\x0b\x49\x13\0\0\
 229 | \x1b\x34\0\x02\x22\x03\x25\x3a\x0b\x3b\x0b\x49\x13\0\0\x1c\x05\0\x03\x25\x3a\
 230 | \x0b\x3b\x0b\x49\x13\0\0\x1d\x13\x01\x03\x25\x0b\x0b\x3a\x0b\x3b\x06\0\0\x1e\
 231 | \x0d\0\x03\x25\x49\x13\x3a\x0b\x3b\x06\x38\x0b\0\0\x1f\x13\x01\x03\x25\x0b\x0b\
 232 | \x3a\x0b\x3b\x05\0\0\x20\x0d\0\x03\x25\x49\x13\x3a\x0b\x3b\x05\x38\x0b\0\0\x21\
 233 | \x13\x01\x03\x25\x0b\x05\x3a\x0b\x3b\x0b\0\0\0\xc1\x03\0\0\x05\0\x01\x08\0\0\0\
 234 | \0\x01\0\x1d\0\x01\x08\0\0\0\0\0\0\0\x02\0\0\0\0\0\0\0\0\0\x08\0\0\0\x0c\0\0\0\
 235 | \x0c\0\0\0\x02\x03\x3a\0\0\0\0\x07\x02\xa1\0\x03\x46\0\0\0\x04\x4a\0\0\0\x04\0\
 236 | \x05\x04\x06\x01\x06\x05\x08\x07\x02\x06\x59\0\0\0\x01\x0b\x02\xa1\x01\x07\x10\
 237 | \x01\x08\x08\x07\x70\0\0\0\x01\x09\0\x08\x09\x85\0\0\0\x01\x0a\x08\0\x09\x75\0\
 238 | \0\0\x03\x81\0\0\0\x04\x4a\0\0\0\x1b\0\x05\x08\x05\x04\x09\x8a\0\0\0\x03\x81\0\
 239 | \0\0\x0a\x4a\0\0\0\0\0\x04\0\0\x02\x0a\xa4\0\0\0\x01\x13\x02\xa1\x02\x07\x20\
 240 | \x01\x0e\x08\x07\xcd\0\0\0\x01\x0f\0\x08\x09\xde\0\0\0\x01\x10\x08\x08\x0b\xf0\
 241 | \0\0\0\x01\x11\x10\x08\x0e\x02\x01\0\0\x01\x12\x18\0\x09\xd2\0\0\0\x03\x81\0\0\
 242 | \0\x04\x4a\0\0\0\x01\0\x09\xe3\0\0\0\x03\x81\0\0\0\x0b\x4a\0\0\0\0\x28\0\x09\
 243 | \xf5\0\0\0\x0c\xfe\0\0\0\x0d\x02\x9b\x7c\x05\x0c\x07\x04\x09\x07\x01\0\0\x0c\
 244 | \x10\x01\0\0\x10\x02\x35\x7b\x05\x0f\x07\x08\x02\x11\x1f\x01\0\0\x01\x1b\x02\
 245 | \xa1\x03\x07\x20\x01\x16\x08\x07\xcd\0\0\0\x01\x17\0\x08\x09\x48\x01\0\0\x01\
 246 | \x18\x08\x08\x0b\x02\x01\0\0\x01\x19\x10\x08\x0e\xf0\0\0\0\x01\x1a\x18\0\x09\
 247 | \x4d\x01\0\0\x03\x81\0\0\0\x0b\x4a\0\0\0\0\x04\0\x0d\x12\x64\x01\0\0\x03\x72\
 248 | \x01\x0e\x09\x69\x01\0\0\x0e\x07\x01\0\0\x0d\x13\x79\x01\0\0\x03\x68\x0c\x83\
 249 | \x01\x09\x7e\x01\0\0\x0f\x93\x01\0\0\x10\x93\x01\0\0\x10\x07\x01\0\0\x10\x07\
 250 | \x01\0\0\0\x11\x0d\x14\x64\x01\0\0\x03\x4c\x08\x50\x0d\x15\xa8\x01\0\0\x03\x8c\
 251 | \x01\x10\x09\xad\x01\0\0\x0f\xbd\x01\0\0\x10\x93\x01\0\0\x10\xf5\0\0\0\0\x05\
 252 | \x16\x05\x08\x0d\x17\xcb\x01\0\0\x03\x27\x0b\x72\x09\xd0\x01\0\0\x0f\xbd\x01\0\
 253 | \0\x10\x93\x01\0\0\x10\xf5\0\0\0\x10\xe5\x01\0\0\0\x09\xea\x01\0\0\x12\x0d\x18\
 254 | \xf6\x01\0\0\x03\x7a\x0c\x84\x01\x09\xfb\x01\0\0\x13\x10\x93\x01\0\0\x10\x07\
 255 | \x01\0\0\0\x14\x19\x10\x02\0\0\x03\x38\x01\x09\x15\x02\0\0\x0f\x93\x01\0\0\x10\
 256 | \x93\x01\0\0\x10\xe5\x01\0\0\0\x14\x1a\x2e\x02\0\0\x03\x4e\x02\x09\x33\x02\0\0\
 257 | \x0f\xbd\x01\0\0\x10\x93\x01\0\0\x10\xe5\x01\0\0\x10\xe5\x01\0\0\x10\x07\x01\0\
 258 | \0\0\x15\xfe\0\0\0\x04\x02\x3e\x03\x16\x1b\0\x16\x1c\x01\x16\x1d\x02\x16\x1e\
 259 | \x04\0\x09\x68\x02\0\0\x17\x46\0\0\0\x03\x79\x02\0\0\x04\x4a\0\0\0\x06\0\x05\
 260 | \x1f\x07\x08\x18\x04\x98\x01\0\0\x01\x5a\x20\0\x13\x81\0\0\0\x19\0\x24\0\x13\
 261 | \xe8\x02\0\0\x1a\x02\x91\x0c\x22\0\x16\xf5\0\0\0\x1a\x02\x91\0\x23\0\x27\x07\
 262 | \x01\0\0\x1b\x01\x2b\0\x15\x07\x01\0\0\x1b\x02\x2f\0\x14\x69\x03\0\0\x1b\x03\
 263 | \x36\0\x22\x63\x02\0\0\x1b\x04\x37\0\x27\x02\x01\0\0\0\x18\x05\x10\0\0\0\x01\
 264 | \x5a\x21\0\x33\x81\0\0\0\x1c\x24\0\x33\xe8\x02\0\0\0\x09\xed\x02\0\0\x1d\x2e\
 265 | \x40\x02\xd8\x3b\x02\0\x1e\x25\x26\x03\0\0\x02\xd9\x3b\x02\0\0\x1e\x2b\xbd\x01\
 266 | \0\0\x02\xda\x3b\x02\0\x08\x1e\x2c\x6d\x02\0\0\x02\xdb\x3b\x02\0\x10\x1e\x2d\
 267 | \x5d\x03\0\0\x02\xdc\x3b\x02\0\x40\0\x1f\x2a\x08\x02\x06\xcf\x20\x07\x55\x03\0\
 268 | \0\x02\x07\xcf\0\x20\x27\x59\x03\0\0\x02\x08\xcf\x02\x20\x29\x59\x03\0\0\x02\
 269 | \x09\xcf\x03\x20\x22\x81\0\0\0\x02\x0a\xcf\x04\0\x05\x26\x07\x02\x05\x28\x08\
 270 | \x01\x03\x46\0\0\0\x04\x4a\0\0\0\0\0\x09\x6e\x03\0\0\x21\x35\x28\x01\0\x09\x08\
 271 | \x22\xf5\0\0\0\0\x0a\0\x08\x30\xf5\0\0\0\0\x0b\x04\x08\x31\x07\x01\0\0\0\x0c\
 272 | \x08\x08\x32\xf5\0\0\0\0\x0d\x10\x08\x33\xab\x03\0\0\0\x0e\x14\x08\x34\xb7\x03\
 273 | \0\0\0\x0f\x24\0\x03\x46\0\0\0\x04\x4a\0\0\0\x10\0\x03\x46\0\0\0\x0b\x4a\0\0\0\
 274 | \0\x01\0\0\x14\0\0\0\x05\0\x08\0\x01\0\0\0\x04\0\0\0\x03\x04\x98\x03\x03\x05\
 275 | \x10\0\xe4\0\0\0\x05\0\0\0\0\0\0\0\x27\0\0\0\x34\0\0\0\x5e\0\0\0\x66\0\0\0\x6b\
 276 | \0\0\0\x7f\0\0\0\x82\0\0\0\x87\0\0\0\x8b\0\0\0\x97\0\0\0\xa4\0\0\0\xa8\0\0\0\
 277 | \xb5\0\0\0\xbb\0\0\0\xc1\0\0\0\xd4\0\0\0\xda\0\0\0\xe8\0\0\0\x01\x01\0\0\x15\
 278 | \x01\0\0\x2f\x01\0\0\x44\x01\0\0\x49\x01\0\0\x61\x01\0\0\x74\x01\0\0\x88\x01\0\
 279 | \0\x9c\x01\0\0\xa4\x01\0\0\xb0\x01\0\0\xba\x01\0\0\xc5\x01\0\0\xd3\x01\0\0\xe0\
 280 | \x01\0\0\xec\x01\0\0\xf0\x01\0\0\xf4\x01\0\0\xf8\x01\0\0\xfc\x01\0\0\x0b\x02\0\
 281 | \0\x11\x02\0\0\x1f\x02\0\0\x2d\x02\0\0\x39\x02\0\0\x3c\x02\0\0\x41\x02\0\0\x48\
 282 | \x02\0\0\x62\x02\0\0\x64\x02\0\0\x69\x02\0\0\x73\x02\0\0\x7e\x02\0\0\x83\x02\0\
 283 | \0\x8c\x02\0\0\x92\x02\0\0\x9b\x02\0\0\x55\x62\x75\x6e\x74\x75\x20\x63\x6c\x61\
 284 | \x6e\x67\x20\x76\x65\x72\x73\x69\x6f\x6e\x20\x31\x38\x2e\x31\x2e\x33\x20\x28\
 285 | \x31\x75\x62\x75\x6e\x74\x75\x31\x29\0\x74\x72\x61\x63\x65\x72\x2e\x62\x70\x66\
 286 | \x2e\x63\0\x2f\x68\x6f\x6d\x65\x2f\x6c\x65\x76\x6e\x64\x61\x79\x73\x2f\x44\x65\
 287 | \x73\x6b\x74\x6f\x70\x2f\x73\x6f\x76\x6e\x64\x2d\x70\x72\x6f\x6a\x65\x63\x74\
 288 | \x2f\x65\x62\x70\x66\0\x4c\x49\x43\x45\x4e\x53\x45\0\x63\x68\x61\x72\0\x5f\x5f\
 289 | \x41\x52\x52\x41\x59\x5f\x53\x49\x5a\x45\x5f\x54\x59\x50\x45\x5f\x5f\0\x72\x62\
 290 | \0\x74\x79\x70\x65\0\x69\x6e\x74\0\x6d\x61\x78\x5f\x65\x6e\x74\x72\x69\x65\x73\
 291 | \0\x70\x72\x6f\x63\x5f\x6d\x65\x74\x72\x69\x63\x73\0\x6b\x65\x79\0\x75\x6e\x73\
 292 | \x69\x67\x6e\x65\x64\x20\x69\x6e\x74\0\x5f\x5f\x75\x33\x32\0\x76\x61\x6c\x75\
 293 | \x65\0\x75\x6e\x73\x69\x67\x6e\x65\x64\x20\x6c\x6f\x6e\x67\x20\x6c\x6f\x6e\x67\
 294 | \0\x5f\x5f\x75\x36\x34\0\x63\x6f\x6e\x74\x61\x69\x6e\x65\x72\x5f\x6d\x61\x70\0\
 295 | \x62\x70\x66\x5f\x67\x65\x74\x5f\x63\x75\x72\x72\x65\x6e\x74\x5f\x70\x69\x64\
 296 | \x5f\x74\x67\x69\x64\0\x62\x70\x66\x5f\x72\x69\x6e\x67\x62\x75\x66\x5f\x72\x65\
 297 | \x73\x65\x72\x76\x65\0\x62\x70\x66\x5f\x67\x65\x74\x5f\x63\x75\x72\x72\x65\x6e\
 298 | \x74\x5f\x63\x67\x72\x6f\x75\x70\x5f\x69\x64\0\x62\x70\x66\x5f\x67\x65\x74\x5f\
 299 | \x63\x75\x72\x72\x65\x6e\x74\x5f\x63\x6f\x6d\x6d\0\x6c\x6f\x6e\x67\0\x62\x70\
 300 | \x66\x5f\x70\x72\x6f\x62\x65\x5f\x72\x65\x61\x64\x5f\x75\x73\x65\x72\x5f\x73\
 301 | \x74\x72\0\x62\x70\x66\x5f\x72\x69\x6e\x67\x62\x75\x66\x5f\x73\x75\x62\x6d\x69\
 302 | \x74\0\x62\x70\x66\x5f\x6d\x61\x70\x5f\x6c\x6f\x6f\x6b\x75\x70\x5f\x65\x6c\x65\
 303 | \x6d\0\x62\x70\x66\x5f\x6d\x61\x70\x5f\x75\x70\x64\x61\x74\x65\x5f\x65\x6c\x65\
 304 | \x6d\0\x42\x50\x46\x5f\x41\x4e\x59\0\x42\x50\x46\x5f\x4e\x4f\x45\x58\x49\x53\
 305 | \x54\0\x42\x50\x46\x5f\x45\x58\x49\x53\x54\0\x42\x50\x46\x5f\x46\x5f\x4c\x4f\
 306 | \x43\x4b\0\x75\x6e\x73\x69\x67\x6e\x65\x64\x20\x6c\x6f\x6e\x67\0\x74\x72\x61\
 307 | \x63\x65\x5f\x6f\x70\x65\x6e\x61\x74\0\x74\x72\x61\x63\x65\x5f\x63\x6c\x6f\x73\
 308 | \x65\0\x70\x69\x64\0\x6f\x6e\x65\0\x63\x74\x78\0\x65\x6e\x74\0\x75\x6e\x73\x69\
 309 | \x67\x6e\x65\x64\x20\x73\x68\x6f\x72\x74\0\x66\x6c\x61\x67\x73\0\x75\x6e\x73\
 310 | \x69\x67\x6e\x65\x64\x20\x63\x68\x61\x72\0\x70\x72\x65\x65\x6d\x70\x74\x5f\x63\
 311 | \x6f\x75\x6e\x74\0\x74\x72\x61\x63\x65\x5f\x65\x6e\x74\x72\x79\0\x69\x64\0\x61\
 312 | \x72\x67\x73\0\x5f\x5f\x64\x61\x74\x61\0\x74\x72\x61\x63\x65\x5f\x65\x76\x65\
 313 | \x6e\x74\x5f\x72\x61\x77\x5f\x73\x79\x73\x5f\x65\x6e\x74\x65\x72\0\x65\0\x74\
 314 | \x67\x69\x64\0\x63\x67\x72\x6f\x75\x70\x5f\x69\x64\0\x73\x79\x73\x63\x61\x6c\
 315 | \x6c\x5f\x69\x64\0\x63\x6f\x6d\x6d\0\x66\x69\x6c\x65\x6e\x61\x6d\x65\0\x65\x76\
 316 | \x65\x6e\x74\0\x70\x61\x74\x68\x6e\x61\x6d\x65\0\x63\x6f\x75\x6e\x74\0\x34\0\0\
 317 | \0\x05\0\x08\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 318 | \0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x9f\xeb\x01\0\x18\0\0\0\0\0\0\0\xa4\x03\0\
 319 | \0\xa4\x03\0\0\x9f\x04\0\0\0\0\0\0\0\0\0\x02\x03\0\0\0\x01\0\0\0\0\0\0\x01\x04\
 320 | \0\0\0\x20\0\0\x01\0\0\0\0\0\0\0\x03\0\0\0\0\x02\0\0\0\x04\0\0\0\x1b\0\0\0\x05\
 321 | \0\0\0\0\0\0\x01\x04\0\0\0\x20\0\0\0\0\0\0\0\0\0\0\x02\x06\0\0\0\0\0\0\0\0\0\0\
 322 | \x03\0\0\0\0\x02\0\0\0\x04\0\0\0\0\0\x04\0\0\0\0\0\x02\0\0\x04\x10\0\0\0\x19\0\
 323 | \0\0\x01\0\0\0\0\0\0\0\x1e\0\0\0\x05\0\0\0\x40\0\0\0\x2a\0\0\0\0\0\0\x0e\x07\0\
 324 | \0\0\x01\0\0\0\0\0\0\0\0\0\0\x02\x0a\0\0\0\0\0\0\0\0\0\0\x03\0\0\0\0\x02\0\0\0\
 325 | \x04\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\x02\x0c\0\0\0\0\0\0\0\0\0\0\x03\0\0\0\0\x02\
 326 | \0\0\0\x04\0\0\0\0\x28\0\0\0\0\0\0\0\0\0\x02\x0e\0\0\0\x2d\0\0\0\0\0\0\x08\x0f\
 327 | \0\0\0\x33\0\0\0\0\0\0\x01\x04\0\0\0\x20\0\0\0\0\0\0\0\0\0\0\x02\x11\0\0\0\x40\
 328 | \0\0\0\0\0\0\x08\x12\0\0\0\x46\0\0\0\0\0\0\x01\x08\0\0\0\x40\0\0\0\0\0\0\0\x04\
 329 | \0\0\x04\x20\0\0\0\x19\0\0\0\x09\0\0\0\0\0\0\0\x1e\0\0\0\x0b\0\0\0\x40\0\0\0\
 330 | \x59\0\0\0\x0d\0\0\0\x80\0\0\0\x5d\0\0\0\x10\0\0\0\xc0\0\0\0\x63\0\0\0\0\0\0\
 331 | \x0e\x13\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\x02\x16\0\0\0\0\0\0\0\0\0\0\x03\0\0\0\0\
 332 | \x02\0\0\0\x04\0\0\0\0\x04\0\0\0\0\0\0\x04\0\0\x04\x20\0\0\0\x19\0\0\0\x09\0\0\
 333 | \0\0\0\0\0\x1e\0\0\0\x15\0\0\0\x40\0\0\0\x59\0\0\0\x10\0\0\0\x80\0\0\0\x5d\0\0\
 334 | \0\x0d\0\0\0\xc0\0\0\0\x70\0\0\0\0\0\0\x0e\x17\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\
 335 | \x02\x1a\0\0\0\x7e\0\0\0\x04\0\0\x04\x40\0\0\0\x98\0\0\0\x1b\0\0\0\0\0\0\0\x9c\
 336 | \0\0\0\x1e\0\0\0\x40\0\0\0\x9f\0\0\0\x20\0\0\0\x80\0\0\0\xa4\0\0\0\x22\0\0\0\0\
 337 | \x02\0\0\xab\0\0\0\x04\0\0\x04\x08\0\0\0\x19\0\0\0\x1c\0\0\0\0\0\0\0\xb7\0\0\0\
 338 | \x1d\0\0\0\x10\0\0\0\xbd\0\0\0\x1d\0\0\0\x18\0\0\0\xcb\0\0\0\x02\0\0\0\x20\0\0\
 339 | \0\xcf\0\0\0\0\0\0\x01\x02\0\0\0\x10\0\0\0\xde\0\0\0\0\0\0\x01\x01\0\0\0\x08\0\
 340 | \0\0\xec\0\0\0\0\0\0\x01\x08\0\0\0\x40\0\0\x01\xf1\0\0\0\0\0\0\x01\x08\0\0\0\
 341 | \x40\0\0\0\0\0\0\0\0\0\0\x03\0\0\0\0\x1f\0\0\0\x04\0\0\0\x06\0\0\0\xff\0\0\0\0\
 342 | \0\0\x01\x01\0\0\0\x08\0\0\x01\0\0\0\0\0\0\0\x03\0\0\0\0\x21\0\0\0\x04\0\0\0\0\
 343 | \0\0\0\0\0\0\0\x01\0\0\x0d\x02\0\0\0\x04\x01\0\0\x19\0\0\0\x08\x01\0\0\x01\0\0\
 344 | \x0c\x23\0\0\0\0\0\0\0\x01\0\0\x0d\x02\0\0\0\x04\x01\0\0\x19\0\0\0\x4b\x04\0\0\
 345 | \x01\0\0\x0c\x25\0\0\0\0\0\0\0\0\0\0\x03\0\0\0\0\x21\0\0\0\x04\0\0\0\x04\0\0\0\
 346 | \x89\x04\0\0\0\0\0\x0e\x27\0\0\0\x01\0\0\0\x91\x04\0\0\x03\0\0\x0f\0\0\0\0\x08\
 347 | \0\0\0\0\0\0\0\x10\0\0\0\x14\0\0\0\0\0\0\0\x20\0\0\0\x18\0\0\0\0\0\0\0\x20\0\0\
 348 | \0\x97\x04\0\0\x01\0\0\x0f\0\0\0\0\x28\0\0\0\0\0\0\0\x04\0\0\0\0\x69\x6e\x74\0\
 349 | \x5f\x5f\x41\x52\x52\x41\x59\x5f\x53\x49\x5a\x45\x5f\x54\x59\x50\x45\x5f\x5f\0\
 350 | \x74\x79\x70\x65\0\x6d\x61\x78\x5f\x65\x6e\x74\x72\x69\x65\x73\0\x72\x62\0\x5f\
 351 | \x5f\x75\x33\x32\0\x75\x6e\x73\x69\x67\x6e\x65\x64\x20\x69\x6e\x74\0\x5f\x5f\
 352 | \x75\x36\x34\0\x75\x6e\x73\x69\x67\x6e\x65\x64\x20\x6c\x6f\x6e\x67\x20\x6c\x6f\
 353 | \x6e\x67\0\x6b\x65\x79\0\x76\x61\x6c\x75\x65\0\x70\x72\x6f\x63\x5f\x6d\x65\x74\
 354 | \x72\x69\x63\x73\0\x63\x6f\x6e\x74\x61\x69\x6e\x65\x72\x5f\x6d\x61\x70\0\x74\
 355 | \x72\x61\x63\x65\x5f\x65\x76\x65\x6e\x74\x5f\x72\x61\x77\x5f\x73\x79\x73\x5f\
 356 | \x65\x6e\x74\x65\x72\0\x65\x6e\x74\0\x69\x64\0\x61\x72\x67\x73\0\x5f\x5f\x64\
 357 | \x61\x74\x61\0\x74\x72\x61\x63\x65\x5f\x65\x6e\x74\x72\x79\0\x66\x6c\x61\x67\
 358 | \x73\0\x70\x72\x65\x65\x6d\x70\x74\x5f\x63\x6f\x75\x6e\x74\0\x70\x69\x64\0\x75\
 359 | \x6e\x73\x69\x67\x6e\x65\x64\x20\x73\x68\x6f\x72\x74\0\x75\x6e\x73\x69\x67\x6e\
 360 | \x65\x64\x20\x63\x68\x61\x72\0\x6c\x6f\x6e\x67\0\x75\x6e\x73\x69\x67\x6e\x65\
 361 | \x64\x20\x6c\x6f\x6e\x67\0\x63\x68\x61\x72\0\x63\x74\x78\0\x74\x72\x61\x63\x65\
 362 | \x5f\x6f\x70\x65\x6e\x61\x74\0\x74\x72\x61\x63\x65\x70\x6f\x69\x6e\x74\x2f\x73\
 363 | \x79\x73\x63\x61\x6c\x6c\x73\x2f\x73\x79\x73\x5f\x65\x6e\x74\x65\x72\x5f\x6f\
 364 | \x70\x65\x6e\x61\x74\0\x2f\x68\x6f\x6d\x65\x2f\x6c\x65\x76\x6e\x64\x61\x79\x73\
 365 | \x2f\x44\x65\x73\x6b\x74\x6f\x70\x2f\x73\x6f\x76\x6e\x64\x2d\x70\x72\x6f\x6a\
 366 | \x65\x63\x74\x2f\x65\x62\x70\x66\x2f\x74\x72\x61\x63\x65\x72\x2e\x62\x70\x66\
 367 | \x2e\x63\0\x69\x6e\x74\x20\x74\x72\x61\x63\x65\x5f\x6f\x70\x65\x6e\x61\x74\x28\
 368 | \x73\x74\x72\x75\x63\x74\x20\x74\x72\x61\x63\x65\x5f\x65\x76\x65\x6e\x74\x5f\
 369 | \x72\x61\x77\x5f\x73\x79\x73\x5f\x65\x6e\x74\x65\x72\x20\x2a\x63\x74\x78\x29\
 370 | \x20\x7b\0\x20\x20\x20\x20\x5f\x5f\x75\x36\x34\x20\x69\x64\x20\x3d\x20\x62\x70\
 371 | \x66\x5f\x67\x65\x74\x5f\x63\x75\x72\x72\x65\x6e\x74\x5f\x70\x69\x64\x5f\x74\
 372 | \x67\x69\x64\x28\x29\x3b\0\x20\x20\x20\x20\x5f\x5f\x75\x33\x32\x20\x70\x69\x64\
 373 | \x20\x3d\x20\x69\x64\x20\x3e\x3e\x20\x33\x32\x3b\0\x20\x20\x20\x20\x65\x20\x3d\
 374 | \x20\x62\x70\x66\x5f\x72\x69\x6e\x67\x62\x75\x66\x5f\x72\x65\x73\x65\x72\x76\
 375 | \x65\x28\x26\x72\x62\x2c\x20\x73\x69\x7a\x65\x6f\x66\x28\x2a\x65\x29\x2c\x20\
 376 | \x30\x29\x3b\0\x20\x20\x20\x20\x69\x66\x20\x28\x21\x65\x29\0\x20\x20\x20\x20\
 377 | \x65\x2d\x3e\x74\x67\x69\x64\x20\x3d\x20\x69\x64\x3b\0\x20\x20\x20\x20\x65\x2d\
 378 | \x3e\x70\x69\x64\x20\x3d\x20\x70\x69\x64\x3b\0\x20\x20\x20\x20\x65\x2d\x3e\x63\
 379 | \x67\x72\x6f\x75\x70\x5f\x69\x64\x20\x3d\x20\x62\x70\x66\x5f\x67\x65\x74\x5f\
 380 | \x63\x75\x72\x72\x65\x6e\x74\x5f\x63\x67\x72\x6f\x75\x70\x5f\x69\x64\x28\x29\
 381 | \x3b\0\x20\x20\x20\x20\x65\x2d\x3e\x73\x79\x73\x63\x61\x6c\x6c\x5f\x69\x64\x20\
 382 | \x3d\x20\x32\x35\x37\x3b\x20\x2f\x2f\x20\x6f\x70\x65\x6e\x61\x74\0\x20\x20\x20\
 383 | \x20\x62\x70\x66\x5f\x67\x65\x74\x5f\x63\x75\x72\x72\x65\x6e\x74\x5f\x63\x6f\
 384 | \x6d\x6d\x28\x26\x65\x2d\x3e\x63\x6f\x6d\x6d\x2c\x20\x73\x69\x7a\x65\x6f\x66\
 385 | \x28\x65\x2d\x3e\x63\x6f\x6d\x6d\x29\x29\x3b\0\x30\x3a\x32\x3a\x31\0\x20\x20\
 386 | \x20\x20\x63\x6f\x6e\x73\x74\x20\x63\x68\x61\x72\x20\x2a\x70\x61\x74\x68\x6e\
 387 | \x61\x6d\x65\x20\x3d\x20\x28\x63\x6f\x6e\x73\x74\x20\x63\x68\x61\x72\x20\x2a\
 388 | \x29\x63\x74\x78\x2d\x3e\x61\x72\x67\x73\x5b\x31\x5d\x3b\0\x20\x20\x20\x20\x62\
 389 | \x70\x66\x5f\x70\x72\x6f\x62\x65\x5f\x72\x65\x61\x64\x5f\x75\x73\x65\x72\x5f\
 390 | \x73\x74\x72\x28\x26\x65\x2d\x3e\x66\x69\x6c\x65\x6e\x61\x6d\x65\x2c\x20\x73\
 391 | \x69\x7a\x65\x6f\x66\x28\x65\x2d\x3e\x66\x69\x6c\x65\x6e\x61\x6d\x65\x29\x2c\
 392 | \x20\x70\x61\x74\x68\x6e\x61\x6d\x65\x29\x3b\0\x20\x20\x20\x20\x62\x70\x66\x5f\
 393 | \x72\x69\x6e\x67\x62\x75\x66\x5f\x73\x75\x62\x6d\x69\x74\x28\x65\x2c\x20\x30\
 394 | \x29\x3b\0\x20\x20\x20\x20\x5f\x5f\x75\x36\x34\x20\x2a\x63\x6f\x75\x6e\x74\x2c\
 395 | \x20\x6f\x6e\x65\x20\x3d\x20\x31\x3b\0\x20\x20\x20\x20\x63\x6f\x75\x6e\x74\x20\
 396 | \x3d\x20\x62\x70\x66\x5f\x6d\x61\x70\x5f\x6c\x6f\x6f\x6b\x75\x70\x5f\x65\x6c\
 397 | \x65\x6d\x28\x26\x70\x72\x6f\x63\x5f\x6d\x65\x74\x72\x69\x63\x73\x2c\x20\x26\
 398 | \x70\x69\x64\x29\x3b\0\x20\x20\x20\x20\x69\x66\x20\x28\x63\x6f\x75\x6e\x74\x29\
 399 | \x20\x7b\0\x20\x20\x20\x20\x20\x20\x20\x20\x5f\x5f\x73\x79\x6e\x63\x5f\x66\x65\
 400 | \x74\x63\x68\x5f\x61\x6e\x64\x5f\x61\x64\x64\x28\x63\x6f\x75\x6e\x74\x2c\x20\
 401 | \x31\x29\x3b\0\x20\x20\x20\x20\x20\x20\x20\x20\x62\x70\x66\x5f\x6d\x61\x70\x5f\
 402 | \x75\x70\x64\x61\x74\x65\x5f\x65\x6c\x65\x6d\x28\x26\x70\x72\x6f\x63\x5f\x6d\
 403 | \x65\x74\x72\x69\x63\x73\x2c\x20\x26\x70\x69\x64\x2c\x20\x26\x6f\x6e\x65\x2c\
 404 | \x20\x42\x50\x46\x5f\x41\x4e\x59\x29\x3b\0\x7d\0\x74\x72\x61\x63\x65\x5f\x63\
 405 | \x6c\x6f\x73\x65\0\x74\x72\x61\x63\x65\x70\x6f\x69\x6e\x74\x2f\x73\x79\x73\x63\
 406 | \x61\x6c\x6c\x73\x2f\x73\x79\x73\x5f\x65\x6e\x74\x65\x72\x5f\x63\x6c\x6f\x73\
 407 | \x65\0\x20\x20\x20\x20\x72\x65\x74\x75\x72\x6e\x20\x30\x3b\0\x4c\x49\x43\x45\
 408 | \x4e\x53\x45\0\x2e\x6d\x61\x70\x73\0\x6c\x69\x63\x65\x6e\x73\x65\0\0\x9f\xeb\
 409 | \x01\0\x20\0\0\0\0\0\0\0\x24\0\0\0\x24\0\0\0\xa4\x01\0\0\xc8\x01\0\0\x1c\0\0\0\
 410 | \x08\0\0\0\x15\x01\0\0\x01\0\0\0\0\0\0\0\x24\0\0\0\x57\x04\0\0\x01\0\0\0\0\0\0\
 411 | \0\x26\0\0\0\x10\0\0\0\x15\x01\0\0\x18\0\0\0\0\0\0\0\x3a\x01\0\0\x71\x01\0\0\0\
 412 | \x4c\0\0\x08\0\0\0\x3a\x01\0\0\xab\x01\0\0\x10\x54\0\0\x18\0\0\0\x3a\x01\0\0\
 413 | \xd6\x01\0\0\x14\x58\0\0\x28\0\0\0\x3a\x01\0\0\xd6\x01\0\0\x0b\x58\0\0\x30\0\0\
 414 | \0\x3a\x01\0\0\xf0\x01\0\0\x09\x60\0\0\x58\0\0\0\x3a\x01\0\0\x21\x02\0\0\x09\
 415 | \x64\0\0\x60\0\0\0\x3a\x01\0\0\x2d\x02\0\0\x0d\x74\0\0\x68\0\0\0\x3a\x01\0\0\
 416 | \x3f\x02\0\0\x0c\x70\0\0\x78\0\0\0\x3a\x01\0\0\x51\x02\0\0\x14\x78\0\0\x88\0\0\
 417 | \0\x3a\x01\0\0\x81\x02\0\0\x13\x7c\0\0\x90\0\0\0\x3a\x01\0\0\x51\x02\0\0\x12\
 418 | \x78\0\0\x98\0\0\0\x3a\x01\0\0\xa4\x02\0\0\x1e\x80\0\0\xa8\0\0\0\x3a\x01\0\0\
 419 | \xa4\x02\0\0\x05\x80\0\0\xb8\0\0\0\x3a\x01\0\0\xdf\x02\0\0\x2a\x88\0\0\xc0\0\0\
 420 | \0\x3a\x01\0\0\x16\x03\0\0\x21\x8c\0\0\xd0\0\0\0\x3a\x01\0\0\x16\x03\0\0\x05\
 421 | \x8c\0\0\xe0\0\0\0\x3a\x01\0\0\x60\x03\0\0\x05\x94\0\0\0\x01\0\0\x3a\x01\0\0\
 422 | \x7e\x03\0\0\x13\x9c\0\0\x10\x01\0\0\x3a\x01\0\0\x2d\x02\0\0\x0d\x74\0\0\x18\
 423 | \x01\0\0\x3a\x01\0\0\x99\x03\0\0\x0d\xa0\0\0\x30\x01\0\0\x3a\x01\0\0\xcf\x03\0\
 424 | \0\x09\xa4\0\0\x38\x01\0\0\x3a\x01\0\0\xe0\x03\0\0\x09\xa8\0\0\x50\x01\0\0\x3a\
 425 | \x01\0\0\x08\x04\0\0\x09\xb0\0\0\x88\x01\0\0\x3a\x01\0\0\x49\x04\0\0\x01\xc0\0\
 426 | \0\x57\x04\0\0\x01\0\0\0\0\0\0\0\x3a\x01\0\0\x7b\x04\0\0\x05\xd4\0\0\x10\0\0\0\
 427 | \x15\x01\0\0\x01\0\0\0\xb8\0\0\0\x1a\0\0\0\xd9\x02\0\0\0\0\0\0\0\0\0\0\x0c\0\0\
 428 | \0\xff\xff\xff\xff\x04\0\x08\0\x08\x7c\x0b\0\x14\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 429 | \x98\x01\0\0\0\0\0\0\x14\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x10\0\0\0\0\0\0\0\x0e\
 430 | \x01\0\0\x05\0\x08\0\x7e\0\0\0\x08\x01\x01\xfb\x0e\x0d\0\x01\x01\x01\x01\0\0\0\
 431 | \x01\0\0\x01\x01\x01\x1f\x03\0\0\0\0\x2a\0\0\0\x2c\0\0\0\x03\x01\x1f\x02\x0f\
 432 | \x05\x1e\x04\x3d\0\0\0\0\x59\x90\xa5\x51\x6f\xc0\xe4\x63\x6b\x37\xb9\x91\x69\
 433 | \x6c\xfa\x79\x4a\0\0\0\x01\x79\x9b\xb3\xc3\x17\xdd\xdf\xf5\x3d\x14\xa2\x5c\xc2\
 434 | \xd3\xb2\xff\x55\0\0\0\x01\xfb\0\xf6\x1e\xc3\x6f\xac\x2d\xfb\x09\x8a\xeb\xe8\
 435 | \xc1\x10\x9b\x5f\0\0\0\x02\x09\xcf\xcd\x71\x69\xc2\x4b\xec\x44\x8f\x30\x58\x2e\
 436 | \x8c\x6d\xb9\x04\0\0\x09\x02\0\0\0\0\0\0\0\0\x03\x12\x01\x05\x10\x0a\x22\x05\
 437 | \x14\x2f\x05\x0b\x06\x2e\x05\x09\x06\x22\x59\x05\x0d\x24\x05\x0c\x1f\x05\x14\
 438 | \x30\x06\x03\x62\x20\x05\x13\x06\x03\x1f\x20\x05\x12\x1f\x05\x1e\x22\x05\x05\
 439 | \x06\x2e\x05\x2a\x06\x30\x05\x21\x21\x05\x05\x06\x2e\x06\x30\x06\x03\x5b\x3c\
 440 | \x05\x13\x06\x03\x27\x20\x05\x0d\x03\x76\x2e\x03\x0b\x20\x05\x09\x3d\x21\x06\
 441 | \x03\x56\x2e\x06\x03\x2c\x20\x05\x01\x78\x02\x02\0\x01\x01\x04\0\x05\x05\x0a\0\
 442 | \x09\x02\0\0\0\0\0\0\0\0\x03\x34\x01\x02\x02\0\x01\x01\x2f\x68\x6f\x6d\x65\x2f\
 443 | \x6c\x65\x76\x6e\x64\x61\x79\x73\x2f\x44\x65\x73\x6b\x74\x6f\x70\x2f\x73\x6f\
 444 | \x76\x6e\x64\x2d\x70\x72\x6f\x6a\x65\x63\x74\x2f\x65\x62\x70\x66\0\x2e\0\x2f\
 445 | \x75\x73\x72\x2f\x69\x6e\x63\x6c\x75\x64\x65\x2f\x62\x70\x66\0\x74\x72\x61\x63\
 446 | \x65\x72\x2e\x62\x70\x66\x2e\x63\0\x6d\x61\x70\x73\x2e\x62\x70\x66\x2e\x68\0\
 447 | \x76\x6d\x6c\x69\x6e\x75\x78\x2e\x68\0\x62\x70\x66\x5f\x68\x65\x6c\x70\x65\x72\
 448 | \x5f\x64\x65\x66\x73\x2e\x68\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 449 | \0\0\0\0\0\x52\x01\0\0\x04\0\xf1\xff\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 450 | \x03\0\x03\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x83\x01\0\0\0\0\x03\0\x88\x01\0\0\
 451 | \0\0\0\0\0\0\0\0\0\0\0\0\x8a\x01\0\0\0\0\x03\0\x48\x01\0\0\0\0\0\0\0\0\0\0\0\0\
 452 | \0\0\0\0\0\0\x03\0\x05\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x03\0\x08\0\0\
 453 | \0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x03\0\x09\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 454 | \0\0\0\0\0\0\x03\0\x0c\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x03\0\x0d\0\0\
 455 | \0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x03\0\x0f\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 456 | \0\0\0\0\0\0\x03\0\x10\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x03\0\x16\0\0\
 457 | \0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x03\0\x18\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 458 | \0\0\0\0\0\0\x03\0\x1a\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x4b\0\0\0\x12\0\x03\0\
 459 | \0\0\0\0\0\0\0\0\x98\x01\0\0\0\0\0\0\x5f\x01\0\0\x11\0\x07\0\0\0\0\0\0\0\0\0\
 460 | \x10\0\0\0\0\0\0\0\x95\0\0\0\x11\0\x07\0\x10\0\0\0\0\0\0\0\x20\0\0\0\0\0\0\0\
 461 | \x1d\x01\0\0\x12\0\x05\0\0\0\0\0\0\0\0\0\x10\0\0\0\0\0\0\0\x7b\x01\0\0\x11\0\
 462 | \x06\0\0\0\0\0\0\0\0\0\x04\0\0\0\0\0\0\0\xcd\0\0\0\x11\0\x07\0\x30\0\0\0\0\0\0\
 463 | \0\x20\0\0\0\0\0\0\0\x30\0\0\0\0\0\0\0\x01\0\0\0\x10\0\0\0\x18\x01\0\0\0\0\0\0\
 464 | \x01\0\0\0\x11\0\0\0\x68\x01\0\0\0\0\0\0\x01\0\0\0\x11\0\0\0\x08\0\0\0\0\0\0\0\
 465 | \x03\0\0\0\x07\0\0\0\x11\0\0\0\0\0\0\0\x03\0\0\0\x09\0\0\0\x15\0\0\0\0\0\0\0\
 466 | \x03\0\0\0\x0d\0\0\0\x23\0\0\0\0\0\0\0\x03\0\0\0\x0b\0\0\0\x27\0\0\0\0\0\0\0\
 467 | \x03\0\0\0\x08\0\0\0\x2b\0\0\0\0\0\0\0\x03\0\0\0\x06\0\0\0\x08\0\0\0\0\0\0\0\
 468 | \x03\0\0\0\x0a\0\0\0\x0c\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x10\0\0\0\0\0\0\0\
 469 | \x03\0\0\0\x0a\0\0\0\x14\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x18\0\0\0\0\0\0\0\
 470 | \x03\0\0\0\x0a\0\0\0\x1c\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x20\0\0\0\0\0\0\0\
 471 | \x03\0\0\0\x0a\0\0\0\x24\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x28\0\0\0\0\0\0\0\
 472 | \x03\0\0\0\x0a\0\0\0\x2c\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x30\0\0\0\0\0\0\0\
 473 | \x03\0\0\0\x0a\0\0\0\x34\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x38\0\0\0\0\0\0\0\
 474 | \x03\0\0\0\x0a\0\0\0\x3c\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x40\0\0\0\0\0\0\0\
 475 | \x03\0\0\0\x0a\0\0\0\x44\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x48\0\0\0\0\0\0\0\
 476 | \x03\0\0\0\x0a\0\0\0\x4c\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x50\0\0\0\0\0\0\0\
 477 | \x03\0\0\0\x0a\0\0\0\x54\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x58\0\0\0\0\0\0\0\
 478 | \x03\0\0\0\x0a\0\0\0\x5c\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x60\0\0\0\0\0\0\0\
 479 | \x03\0\0\0\x0a\0\0\0\x64\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x68\0\0\0\0\0\0\0\
 480 | \x03\0\0\0\x0a\0\0\0\x6c\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x70\0\0\0\0\0\0\0\
 481 | \x03\0\0\0\x0a\0\0\0\x74\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x78\0\0\0\0\0\0\0\
 482 | \x03\0\0\0\x0a\0\0\0\x7c\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x80\0\0\0\0\0\0\0\
 483 | \x03\0\0\0\x0a\0\0\0\x84\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x88\0\0\0\0\0\0\0\
 484 | \x03\0\0\0\x0a\0\0\0\x8c\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x90\0\0\0\0\0\0\0\
 485 | \x03\0\0\0\x0a\0\0\0\x94\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x98\0\0\0\0\0\0\0\
 486 | \x03\0\0\0\x0a\0\0\0\x9c\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\xa0\0\0\0\0\0\0\0\
 487 | \x03\0\0\0\x0a\0\0\0\xa4\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\xa8\0\0\0\0\0\0\0\
 488 | \x03\0\0\0\x0a\0\0\0\xac\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\xb0\0\0\0\0\0\0\0\
 489 | \x03\0\0\0\x0a\0\0\0\xb4\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\xb8\0\0\0\0\0\0\0\
 490 | \x03\0\0\0\x0a\0\0\0\xbc\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\xc0\0\0\0\0\0\0\0\
 491 | \x03\0\0\0\x0a\0\0\0\xc4\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\xc8\0\0\0\0\0\0\0\
 492 | \x03\0\0\0\x0a\0\0\0\xcc\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\xd0\0\0\0\0\0\0\0\
 493 | \x03\0\0\0\x0a\0\0\0\xd4\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\xd8\0\0\0\0\0\0\0\
 494 | \x03\0\0\0\x0a\0\0\0\xdc\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\xe0\0\0\0\0\0\0\0\
 495 | \x03\0\0\0\x0a\0\0\0\xe4\0\0\0\0\0\0\0\x03\0\0\0\x0a\0\0\0\x08\0\0\0\0\0\0\0\
 496 | \x02\0\0\0\x13\0\0\0\x10\0\0\0\0\0\0\0\x02\0\0\0\x10\0\0\0\x18\0\0\0\0\0\0\0\
 497 | \x02\0\0\0\x11\0\0\0\x20\0\0\0\0\0\0\0\x02\0\0\0\x14\0\0\0\x28\0\0\0\0\0\0\0\
 498 | \x02\0\0\0\x02\0\0\0\x30\0\0\0\0\0\0\0\x02\0\0\0\x05\0\0\0\x84\x03\0\0\0\0\0\0\
 499 | \x04\0\0\0\x10\0\0\0\x90\x03\0\0\0\0\0\0\x04\0\0\0\x11\0\0\0\x9c\x03\0\0\0\0\0\
 500 | \0\x04\0\0\0\x14\0\0\0\xb4\x03\0\0\0\0\0\0\x04\0\0\0\x13\0\0\0\x2c\0\0\0\0\0\0\
 501 | \0\x04\0\0\0\x02\0\0\0\x3c\0\0\0\0\0\0\0\x04\0\0\0\x05\0\0\0\x50\0\0\0\0\0\0\0\
 502 | \x04\0\0\0\x02\0\0\0\x60\0\0\0\0\0\0\0\x04\0\0\0\x02\0\0\0\x70\0\0\0\0\0\0\0\
 503 | \x04\0\0\0\x02\0\0\0\x80\0\0\0\0\0\0\0\x04\0\0\0\x02\0\0\0\x90\0\0\0\0\0\0\0\
 504 | \x04\0\0\0\x02\0\0\0\xa0\0\0\0\0\0\0\0\x04\0\0\0\x02\0\0\0\xb0\0\0\0\0\0\0\0\
 505 | \x04\0\0\0\x02\0\0\0\xc0\0\0\0\0\0\0\0\x04\0\0\0\x02\0\0\0\xd0\0\0\0\0\0\0\0\
 506 | \x04\0\0\0\x02\0\0\0\xe0\0\0\0\0\0\0\0\x04\0\0\0\x02\0\0\0\xf0\0\0\0\0\0\0\0\
 507 | \x04\0\0\0\x02\0\0\0\0\x01\0\0\0\0\0\0\x04\0\0\0\x02\0\0\0\x10\x01\0\0\0\0\0\0\
 508 | \x04\0\0\0\x02\0\0\0\x20\x01\0\0\0\0\0\0\x04\0\0\0\x02\0\0\0\x30\x01\0\0\0\0\0\
 509 | \0\x04\0\0\0\x02\0\0\0\x40\x01\0\0\0\0\0\0\x04\0\0\0\x02\0\0\0\x50\x01\0\0\0\0\
 510 | \0\0\x04\0\0\0\x02\0\0\0\x60\x01\0\0\0\0\0\0\x04\0\0\0\x02\0\0\0\x70\x01\0\0\0\
 511 | \0\0\0\x04\0\0\0\x02\0\0\0\x80\x01\0\0\0\0\0\0\x04\0\0\0\x02\0\0\0\x90\x01\0\0\
 512 | \0\0\0\0\x04\0\0\0\x02\0\0\0\xa0\x01\0\0\0\0\0\0\x04\0\0\0\x02\0\0\0\xb0\x01\0\
 513 | \0\0\0\0\0\x04\0\0\0\x02\0\0\0\xc0\x01\0\0\0\0\0\0\x04\0\0\0\x02\0\0\0\xd8\x01\
 514 | \0\0\0\0\0\0\x04\0\0\0\x05\0\0\0\xf4\x01\0\0\0\0\0\0\x04\0\0\0\x02\0\0\0\x14\0\
 515 | \0\0\0\0\0\0\x03\0\0\0\x0c\0\0\0\x18\0\0\0\0\0\0\0\x02\0\0\0\x02\0\0\0\x2c\0\0\
 516 | \0\0\0\0\0\x03\0\0\0\x0c\0\0\0\x30\0\0\0\0\0\0\0\x02\0\0\0\x05\0\0\0\x22\0\0\0\
 517 | \0\0\0\0\x03\0\0\0\x0e\0\0\0\x26\0\0\0\0\0\0\0\x03\0\0\0\x0e\0\0\0\x2a\0\0\0\0\
 518 | \0\0\0\x03\0\0\0\x0e\0\0\0\x36\0\0\0\0\0\0\0\x03\0\0\0\x0e\0\0\0\x4b\0\0\0\0\0\
 519 | \0\0\x03\0\0\0\x0e\0\0\0\x60\0\0\0\0\0\0\0\x03\0\0\0\x0e\0\0\0\x75\0\0\0\0\0\0\
 520 | \0\x03\0\0\0\x0e\0\0\0\x8f\0\0\0\0\0\0\0\x02\0\0\0\x02\0\0\0\x02\x01\0\0\0\0\0\
 521 | \0\x02\0\0\0\x05\0\0\0\x0f\x12\x13\x10\x11\x14\0\x2e\x64\x65\x62\x75\x67\x5f\
 522 | \x61\x62\x62\x72\x65\x76\0\x2e\x74\x65\x78\x74\0\x2e\x72\x65\x6c\x2e\x42\x54\
 523 | \x46\x2e\x65\x78\x74\0\x2e\x72\x65\x6c\x74\x72\x61\x63\x65\x70\x6f\x69\x6e\x74\
 524 | \x2f\x73\x79\x73\x63\x61\x6c\x6c\x73\x2f\x73\x79\x73\x5f\x65\x6e\x74\x65\x72\
 525 | \x5f\x6f\x70\x65\x6e\x61\x74\0\x74\x72\x61\x63\x65\x5f\x6f\x70\x65\x6e\x61\x74\
 526 | \0\x2e\x64\x65\x62\x75\x67\x5f\x72\x6e\x67\x6c\x69\x73\x74\x73\0\x2e\x64\x65\
 527 | \x62\x75\x67\x5f\x6c\x6f\x63\x6c\x69\x73\x74\x73\0\x2e\x72\x65\x6c\x2e\x64\x65\
 528 | \x62\x75\x67\x5f\x73\x74\x72\x5f\x6f\x66\x66\x73\x65\x74\x73\0\x2e\x6d\x61\x70\
 529 | \x73\0\x70\x72\x6f\x63\x5f\x6d\x65\x74\x72\x69\x63\x73\0\x2e\x64\x65\x62\x75\
 530 | \x67\x5f\x73\x74\x72\0\x2e\x64\x65\x62\x75\x67\x5f\x6c\x69\x6e\x65\x5f\x73\x74\
 531 | \x72\0\x2e\x72\x65\x6c\x2e\x64\x65\x62\x75\x67\x5f\x61\x64\x64\x72\0\x63\x6f\
 532 | \x6e\x74\x61\x69\x6e\x65\x72\x5f\x6d\x61\x70\0\x2e\x72\x65\x6c\x2e\x64\x65\x62\
 533 | \x75\x67\x5f\x69\x6e\x66\x6f\0\x2e\x6c\x6c\x76\x6d\x5f\x61\x64\x64\x72\x73\x69\
 534 | \x67\0\x74\x72\x61\x63\x65\x70\x6f\x69\x6e\x74\x2f\x73\x79\x73\x63\x61\x6c\x6c\
 535 | \x73\x2f\x73\x79\x73\x5f\x65\x6e\x74\x65\x72\x5f\x63\x6c\x6f\x73\x65\0\x74\x72\
 536 | \x61\x63\x65\x5f\x63\x6c\x6f\x73\x65\0\x6c\x69\x63\x65\x6e\x73\x65\0\x2e\x72\
 537 | \x65\x6c\x2e\x64\x65\x62\x75\x67\x5f\x6c\x69\x6e\x65\0\x2e\x72\x65\x6c\x2e\x64\
 538 | \x65\x62\x75\x67\x5f\x66\x72\x61\x6d\x65\0\x74\x72\x61\x63\x65\x72\x2e\x62\x70\
 539 | \x66\x2e\x63\0\x72\x62\0\x2e\x73\x74\x72\x74\x61\x62\0\x2e\x73\x79\x6d\x74\x61\
 540 | \x62\0\x2e\x72\x65\x6c\x2e\x42\x54\x46\0\x4c\x49\x43\x45\x4e\x53\x45\0\x4c\x42\
 541 | \x42\x30\x5f\x34\0\x4c\x42\x42\x30\x5f\x33\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 542 | \0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 543 | \0\0\0\0\0\0\0\0\0\x62\x01\0\0\x03\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x2e\
 544 | \x21\0\0\0\0\0\0\x91\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\0\
 545 | \0\0\0\0\x0f\0\0\0\x01\0\0\0\x06\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x40\0\0\0\0\0\0\
 546 | \0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x04\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x26\0\0\0\
 547 | \x01\0\0\0\x06\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x40\0\0\0\0\0\0\0\x98\x01\0\0\0\0\
 548 | \0\0\0\0\0\0\0\0\0\0\x08\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x22\0\0\0\x09\0\0\0\x40\
 549 | \0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\xe8\x19\0\0\0\0\0\0\x30\0\0\0\0\0\0\0\x1c\0\0\0\
 550 | \x03\0\0\0\x08\0\0\0\0\0\0\0\x10\0\0\0\0\0\0\0\xf9\0\0\0\x01\0\0\0\x06\0\0\0\0\
 551 | \0\0\0\0\0\0\0\0\0\0\0\xd8\x01\0\0\0\0\0\0\x10\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 552 | \x08\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x29\x01\0\0\x01\0\0\0\x03\0\0\0\0\0\0\0\0\0\
 553 | \0\0\0\0\0\0\xe8\x01\0\0\0\0\0\0\x04\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x01\0\0\0\0\
 554 | \0\0\0\0\0\0\0\0\0\0\0\x8f\0\0\0\x01\0\0\0\x03\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 555 | \xf0\x01\0\0\0\0\0\0\x50\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x08\0\0\0\0\0\0\0\0\0\0\
 556 | \0\0\0\0\0\x68\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x40\x02\0\0\0\0\
 557 | \0\0\x53\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x01\0\
 558 | \0\0\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x93\x02\0\0\0\0\0\0\x91\x01\0\0\
 559 | \0\0\0\0\0\0\0\0\0\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\xdf\0\0\0\x01\0\0\0\
 560 | \0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x24\x04\0\0\0\0\0\0\xc5\x03\0\0\0\0\0\0\0\0\0\
 561 | \0\0\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\xdb\0\0\0\x09\0\0\0\x40\0\0\0\0\0\
 562 | \0\0\0\0\0\0\0\0\0\0\x18\x1a\0\0\0\0\0\0\x60\0\0\0\0\0\0\0\x1c\0\0\0\x0a\0\0\0\
 563 | \x08\0\0\0\0\0\0\0\x10\0\0\0\0\0\0\0\x58\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 564 | \0\0\0\0\0\xe9\x07\0\0\0\0\0\0\x18\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x01\0\0\0\0\0\
 565 | \0\0\0\0\0\0\0\0\0\0\x7c\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x01\
 566 | \x08\0\0\0\0\0\0\xe8\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\0\0\
 567 | \0\0\0\x78\0\0\0\x09\0\0\0\x40\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x78\x1a\0\0\0\0\0\
 568 | \0\x80\x03\0\0\0\0\0\0\x1c\0\0\0\x0d\0\0\0\x08\0\0\0\0\0\0\0\x10\0\0\0\0\0\0\0\
 569 | \xa2\0\0\0\x01\0\0\0\x30\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\xe9\x08\0\0\0\0\0\0\xa1\
 570 | \x02\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x01\0\0\0\0\0\0\0\x01\0\0\0\0\0\0\0\xc1\0\0\0\
 571 | \x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x8a\x0b\0\0\0\0\0\0\x38\0\0\0\0\0\0\
 572 | \0\0\0\0\0\0\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\xbd\0\0\0\x09\0\0\0\x40\0\
 573 | \0\0\0\0\0\0\0\0\0\0\0\0\0\0\xf8\x1d\0\0\0\0\0\0\x60\0\0\0\0\0\0\0\x1c\0\0\0\
 574 | \x10\0\0\0\x08\0\0\0\0\0\0\0\x10\0\0\0\0\0\0\0\x76\x01\0\0\x01\0\0\0\0\0\0\0\0\
 575 | \0\0\0\0\0\0\0\0\0\0\0\xc4\x0b\0\0\0\0\0\0\x5b\x08\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 576 | \x04\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x72\x01\0\0\x09\0\0\0\x40\0\0\0\0\0\0\0\0\0\
 577 | \0\0\0\0\0\0\x58\x1e\0\0\0\0\0\0\x40\0\0\0\0\0\0\0\x1c\0\0\0\x12\0\0\0\x08\0\0\
 578 | \0\0\0\0\0\x10\0\0\0\0\0\0\0\x19\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 579 | \0\x20\x14\0\0\0\0\0\0\x04\x02\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x04\0\0\0\0\0\0\0\0\
 580 | \0\0\0\0\0\0\0\x15\0\0\0\x09\0\0\0\x40\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x98\x1e\0\
 581 | \0\0\0\0\0\xc0\x01\0\0\0\0\0\0\x1c\0\0\0\x14\0\0\0\x08\0\0\0\0\0\0\0\x10\0\0\0\
 582 | \0\0\0\0\x45\x01\0\0\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x28\x16\0\0\0\0\
 583 | \0\0\x40\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x08\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x41\
 584 | \x01\0\0\x09\0\0\0\x40\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x58\x20\0\0\0\0\0\0\x40\0\
 585 | \0\0\0\0\0\0\x1c\0\0\0\x16\0\0\0\x08\0\0\0\0\0\0\0\x10\0\0\0\0\0\0\0\x35\x01\0\
 586 | \0\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x68\x16\0\0\0\0\0\0\x12\x01\0\0\0\
 587 | \0\0\0\0\0\0\0\0\0\0\0\x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x31\x01\0\0\x09\0\0\0\
 588 | \x40\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x98\x20\0\0\0\0\0\0\x90\0\0\0\0\0\0\0\x1c\0\
 589 | \0\0\x18\0\0\0\x08\0\0\0\0\0\0\0\x10\0\0\0\0\0\0\0\xad\0\0\0\x01\0\0\0\x30\0\0\
 590 | \0\0\0\0\0\0\0\0\0\0\0\0\0\x7a\x17\0\0\0\0\0\0\x71\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 591 | \0\x01\0\0\0\0\0\0\0\x01\0\0\0\0\0\0\0\xeb\0\0\0\x03\x4c\xff\x6f\0\0\0\x80\0\0\
 592 | \0\0\0\0\0\0\0\0\0\0\x28\x21\0\0\0\0\0\0\x06\0\0\0\0\0\0\0\x1c\0\0\0\0\0\0\0\
 593 | \x01\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\x6a\x01\0\0\x02\0\0\0\0\0\0\0\0\0\0\0\0\0\0\
 594 | \0\0\0\0\0\xf0\x17\0\0\0\0\0\0\xf8\x01\0\0\0\0\0\0\x01\0\0\0\x0f\0\0\0\x08\0\0\
 595 | \0\0\0\0\0\x18\0\0\0\0\0\0\0";
 596 | 
 597 | 	*sz = sizeof(data) - 1;
 598 | 	return (const void *)data;
 599 | }
 600 | 
 601 | #ifdef __cplusplus
 602 | struct tracer_bpf *tracer_bpf::open(const struct bpf_object_open_opts *opts) { return tracer_bpf__open_opts(opts); }
 603 | struct tracer_bpf *tracer_bpf::open_and_load() { return tracer_bpf__open_and_load(); }
 604 | int tracer_bpf::load(struct tracer_bpf *skel) { return tracer_bpf__load(skel); }
 605 | int tracer_bpf::attach(struct tracer_bpf *skel) { return tracer_bpf__attach(skel); }
 606 | void tracer_bpf::detach(struct tracer_bpf *skel) { tracer_bpf__detach(skel); }
 607 | void tracer_bpf::destroy(struct tracer_bpf *skel) { tracer_bpf__destroy(skel); }
 608 | const void *tracer_bpf::elf_bytes(size_t *sz) { return tracer_bpf__elf_bytes(sz); }
 609 | #endif /* __cplusplus */
 610 | 
 611 | __attribute__((unused)) static void
 612 | tracer_bpf__assert(struct tracer_bpf *s __attribute__((unused)))
 613 | {
 614 | #ifdef __cplusplus
 615 | #define _Static_assert static_assert
 616 | #endif
 617 | #ifdef __cplusplus
 618 | #undef _Static_assert
 619 | #endif
 620 | }
 621 | 
 622 | #endif /* __TRACER_BPF_SKEL_H__ */
```

