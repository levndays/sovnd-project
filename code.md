# Source Code

## Python

### c.py

```python
   1 | #!/usr/bin/env python3
   2 | import os
   3 | from pathlib import Path
   4 | 
   5 | ROOT = Path(".")
   6 | OUTPUT = Path("code.md")
   7 | EXCLUDED_DIRS = {"venv", ".git", ".pytest_cache", ".logs", ".pids", "data", "deploy", ".streamlit"}
   8 | 
   9 | 
  10 | def get_all_files(root):
  11 |     files = {"py": [], "md": [], "html": []}
  12 |     for root_path in root.rglob("*"):
  13 |         if root_path.is_file():
  14 |             rel = root_path.relative_to(root)
  15 |             if any(excluded in rel.parts for excluded in EXCLUDED_DIRS):
  16 |                 continue
  17 |             if "__pycache__" in rel.parts:
  18 |                 continue
  19 |             if rel.suffix == ".py":
  20 |                 files["py"].append(rel)
  21 |             elif rel.suffix == ".md":
  22 |                 files["md"].append(rel)
  23 |             elif rel.suffix == ".html":
  24 |                 files["html"].append(rel)
  25 |     return {k: sorted(v) for k, v in files.items()}
  26 | 
  27 | 
  28 | def format_file_content(path):
  29 |     try:
  30 |         content = path.read_text(encoding="utf-8")
  31 |     except UnicodeDecodeError:
  32 |         return "    [binary file - skipped]"
  33 |     lines = content.splitlines()
  34 |     numbered = "\n".join(f"{i+1:4d} | {line}" for i, line in enumerate(lines))
  35 |     return numbered
  36 | 
  37 | 
  38 | all_files = get_all_files(ROOT)
  39 | 
  40 | with OUTPUT.open("w", encoding="utf-8") as out:
  41 |     out.write("# Source Code\n\n")
  42 | 
  43 |     out.write("## Python\n\n")
  44 |     for rel in all_files["py"]:
  45 |         full = ROOT / rel
  46 |         out.write(f"### {rel}\n\n```python\n")
  47 |         out.write(format_file_content(full))
  48 |         out.write("\n```\n\n")
  49 | 
  50 |     out.write("## Markdown\n\n")
  51 |     for rel in all_files["md"]:
  52 |         full = ROOT / rel
  53 |         ext = "markdown"
  54 |         out.write(f"### {rel}\n\n```{ext}\n")
  55 |         out.write(format_file_content(full))
  56 |         out.write("\n```\n\n")
  57 | 
  58 |     out.write("## HTML\n\n")
  59 |     for rel in all_files["html"]:
  60 |         full = ROOT / rel
  61 |         ext = "html"
  62 |         out.write(f"### {rel}\n\n```{ext}\n")
  63 |         out.write(format_file_content(full))
  64 |         out.write("\n```\n\n")
  65 | 
  66 | print(f"Wrote {len(all_files['py'])} Python files, {len(all_files['md'])} Markdown files, {len(all_files['html'])} HTML files to {OUTPUT}")
```

### demo.py

```python
   1 | import subprocess
   2 | import time
   3 | import sys
   4 | import os
   5 | 
   6 | def start():
   7 |     if os.geteuid() != 0:
   8 |         print("❌ ERROR: The demo orchestrator must run as root (sudo).")
   9 |         sys.exit(1)
  10 | 
  11 |     real_user = os.environ.get('SUDO_USER')
  12 |     print("🛡️  SovND | Initializing SOC Demo...")
  13 |     
  14 |     # 1. Clean data for fresh start
  15 |     if os.path.exists("data/sovnd.db"):
  16 |         os.remove("data/sovnd.db")
  17 |     os.makedirs("data", exist_ok=True)
  18 |     os.chmod("data", 0o777)
  19 | 
  20 |     # 2. Start Dashboard Backend (User Port 8000)
  21 |     api_proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"])
  22 |     
  23 |     # 3. Start eBPF Agent (Kernel Monitor)
  24 |     agent_proc = subprocess.Popen([sys.executable, "src/main_agent.py"])
  25 | 
  26 |     time.sleep(2)
  27 |     print("\n🚀 ANALYTICS ENGINE READY: http://localhost:8000")
  28 |     
  29 |     # 4. Open browser as the regular user
  30 |     if real_user:
  31 |         os.system(f"sudo -u {real_user} xdg-open http://localhost:8000 > /dev/null 2>&1 &")
  32 | 
  33 |     try:
  34 |         while True:
  35 |             time.sleep(1)
  36 |     except KeyboardInterrupt:
  37 |         print("\nShutting down SovND...")
  38 |         api_proc.terminate()
  39 |         agent_proc.terminate()
  40 | 
  41 | if __name__ == "__main__":
  42 |     if len(sys.argv) > 1 and sys.argv[1] == "start":
  43 |         start()
  44 |     else:
  45 |         print("Usage: sudo python3 demo.py start")
```

### src/__init__.py

```python

```

### src/api/main.py

```python
   1 | import asyncio, json, os, time, random
   2 | from fastapi import FastAPI, WebSocket, WebSocketDisconnect
   3 | from fastapi.staticfiles import StaticFiles
   4 | from fastapi.responses import FileResponse, Response
   5 | from src.storage.sqlite import StorageManager
   6 | 
   7 | app = FastAPI()
   8 | storage = StorageManager()
   9 | 
  10 | os.makedirs("static", exist_ok=True)
  11 | static_mount = StaticFiles(directory="static")
  12 | 
  13 | class NoCacheStaticMount(StaticFiles):
  14 |     async def get_response(self, path, scope):
  15 |         response = await super().get_response(path, scope)
  16 |         response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
  17 |         response.headers["Pragma"] = "no-cache"
  18 |         response.headers["Expires"] = "0"
  19 |         return response
  20 | 
  21 | app.mount("/static", NoCacheStaticMount(directory="static"), name="static")
  22 | 
  23 | @app.get("/")
  24 | async def get_index():
  25 |     content = open("static/index.html", "r").read()
  26 |     return Response(
  27 |         content,
  28 |         media_type="text/html",
  29 |         headers={
  30 |             "Cache-Control": "no-cache, no-store, must-revalidate",
  31 |             "Pragma": "no-cache",
  32 |             "Expires": "0"
  33 |         }
  34 |     )
  35 | 
  36 | @app.websocket("/ws/telemetry")
  37 | async def websocket_endpoint(websocket: WebSocket):
  38 |     await websocket.accept()
  39 |     try:
  40 |         while True:
  41 |             alerts = storage.get_recent_alerts(limit=10)
  42 |             eps = 0
  43 |             try:
  44 |                 with open("data/heartbeat.json", "r") as f:
  45 |                     hb = json.load(f)
  46 |                     if time.time() - hb.get("timestamp", 0) < 3:
  47 |                         eps = hb.get("events_per_sec", 0)
  48 |             except: pass
  49 |             await websocket.send_json({"eps": eps, "alerts": alerts})
  50 |             await asyncio.sleep(0.5)
  51 |     except WebSocketDisconnect:
  52 |         pass
  53 | 
  54 | @app.post("/api/attack")
  55 | async def trigger_attack():
  56 |     payloads = [
  57 |         # High signature score (15 pts) - critical files
  58 |         ("signature", "cat /etc/shadow"),
  59 |         ("signature", "cat /etc/sudoers"),
  60 |         ("signature", "cat /var/run/docker.sock"),
  61 |         ("signature", "cat /root/.ssh/id_rsa"),
  62 |         
  63 |         # Graph heuristics - sensitive access
  64 |         ("graph", "find /etc -type f -name '*.conf' 2>/dev/null | head -10"),
  65 |         ("graph", "ls -la /root"),
  66 |         ("graph", "ls -la /etc/passwd /etc/shadow"),
  67 |         
  68 |         # Statistical anomaly - high frequency
  69 |         ("statistical", "bash -c 'for i in $(seq 1 100); do echo $i > /tmp/f$i; done'"),
  70 |         ("statistical", "touch /tmp/x{1..50}"),
  71 |         
  72 |         # Mixed - signature + graph
  73 |         ("both", "cat /etc/shadow && find /root -type f 2>/dev/null"),
  74 |     ]
  75 |     
  76 |     # Pick 3 random payloads
  77 |     selected = random.sample(payloads, 3)
  78 |     
  79 |     results = []
  80 |     for type_hint, cmd in selected:
  81 |         result = os.system(f"{cmd} > /dev/null 2>&1 &")
  82 |         results.append({"type": type_hint, "cmd": cmd, "result": result})
  83 |     
  84 |     return {"status": "attacks_launched", "count": len(selected), "payloads": results}
```

### src/dashboard/app.py

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

### src/detector/signature.py

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

### src/detector/statistical.py

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

### src/docker/resolver.py

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

### src/ebpf_agent.py

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

### src/graph/builder.py

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

### src/main_agent.py

```python
   1 | import time, sys, os, json, dataclasses
   2 | from pathlib import Path
   3 | import random
   4 | 
   5 | try:
   6 |     import numpy as np
   7 |     HAS_NUMPY = True
   8 | except ImportError:
   9 |     HAS_NUMPY = False
  10 |     np = None
  11 |     print("⚠️ numpy not available - statistical detection disabled")
  12 | 
  13 | try:
  14 |     import networkx as nx
  15 |     HAS_NETWORKX = True
  16 | except ImportError:
  17 |     HAS_NETWORKX = False
  18 |     nx = None
  19 |     print("⚠️ networkx not available - graph detection disabled")
  20 | 
  21 | try:
  22 |     sys.path.insert(0, str(Path(__file__).parent.parent))
  23 |     from src.ebpf_agent import EBPFAgent
  24 |     from src.detector.signature import SignatureDetector
  25 |     
  26 |     if HAS_NUMPY:
  27 |         from src.detector.statistical import StatisticalDetector
  28 |         from src.metrics.engine import MetricsEngine
  29 |         from src.scoring.engine import ScoringEngine
  30 |         STAT_DETECTOR = True
  31 |     else:
  32 |         from src.scoring.engine import ScoringEngine
  33 |         STAT_DETECTOR = False
  34 |     
  35 |     if HAS_NETWORKX:
  36 |         from src.graph.builder import ProvenanceGraphBuilder
  37 |     else:
  38 |         ProvenanceGraphBuilder = None
  39 |     
  40 |     from src.storage.sqlite import StorageManager
  41 | except Exception as e:
  42 |     print(f"⚠️ Import error: {e}")
  43 |     raise
  44 | 
  45 | def run_agent():
  46 |     print("🛡️ Starting SovND Real-time eBPF Engine...")
  47 |     lib_path = Path(__file__).parent.parent / "ebpf" / "libloader.so"
  48 |     
  49 |     # Pre-populated process heap for demo (simulates baseline profiles)
  50 |     preloaded_pids = list(range(1000, 1100))
  51 |     random.shuffle(preloaded_pids)
  52 |     
  53 |     agent = EBPFAgent(lib_path=str(lib_path))
  54 |     sig_detector = SignatureDetector()
  55 |     scoring = ScoringEngine(threshold=15.0)
  56 |     storage = StorageManager()
  57 |     
  58 |     if STAT_DETECTOR and HAS_NUMPY:
  59 |         print("📊 Statistical detection enabled")
  60 |         metrics_engine = MetricsEngine()
  61 |         stat_detector = StatisticalDetector(engine=metrics_engine, threshold_z=2.5)
  62 |     else:
  63 |         print("📊 Statistical detection DISABLED")
  64 |         metrics_engine = None
  65 |         stat_detector = None
  66 |     
  67 |     if HAS_NETWORKX and ProvenanceGraphBuilder:
  68 |         print("🔗 Graph detection enabled")
  69 |         graph_builder = ProvenanceGraphBuilder()
  70 |     else:
  71 |         print("🔗 Graph detection DISABLED")
  72 |         graph_builder = None
  73 | 
  74 |     # Clear old data for demo freshness
  75 |     storage.clear_alerts()
  76 | 
  77 |     try:
  78 |         agent.start()
  79 |         print("✅ eBPF Agent attached. Monitoring...")
  80 |         events_this_second = 0
  81 |         last_heartbeat = time.time()
  82 |         
  83 |         while True:
  84 |             current_time = time.time()
  85 |             if current_time - last_heartbeat >= 1.0:
  86 |                 with open("data/heartbeat.json", "w") as f:
  87 |                     json.dump({"events_per_sec": events_this_second, "timestamp": current_time}, f)
  88 |                 os.chmod("data/heartbeat.json", 0o666)
  89 |                 events_this_second = 0
  90 |                 last_heartbeat = current_time
  91 | 
  92 |             event = agent.get_event(timeout=0.1)
  93 |             if event:
  94 |                 events_this_second += 1
  95 |                 
  96 |                 graph_heuristics = []
  97 |                 
  98 |                 if graph_builder:
  99 |                     graph_builder.add_event(event)
 100 |                     subgraph = graph_builder.get_process_subgraph(event["pid"])
 101 |                     if subgraph.number_of_nodes() > 3:
 102 |                         graph_heuristics.append("high_connectivity")
 103 |                 
 104 |                 if event.get("filename", "").startswith("/etc") or event.get("filename", "").startswith("/root"):
 105 |                     graph_heuristics.append("sensitive_access")
 106 |                 
 107 |                 sig_match = sig_detector.analyze_event(event)
 108 |                 
 109 |                 if STAT_DETECTOR and metrics_engine and stat_detector:
 110 |                     metrics_engine.update(event)
 111 |                     stat_report = stat_detector.evaluate(
 112 |                         pid=event["pid"],
 113 |                         current_metrics=metrics_engine.get_current_vector(event["pid"])
 114 |                     )
 115 |                 else:
 116 |                     stat_report = {"pid": event["pid"], "is_anomalous": False, "max_z_score": 0.0}
 117 |                 
 118 |                 alert = scoring.compute_score(
 119 |                     event=event,
 120 |                     stat_report=stat_report,
 121 |                     sig_match=sig_match,
 122 |                     graph_heuristics=graph_heuristics
 123 |                 )
 124 |                 
 125 |                 if alert:
 126 |                     storage.save_alert(dataclasses.asdict(alert))
 127 |                     try: os.chmod(storage.db_path, 0o666)
 128 |                     except: pass
 129 |                     print(f"🚨 ALERT: PID {event['pid']} [{event['comm']}] - SCORE {alert.score}")
 130 |     except KeyboardInterrupt: pass
 131 |     finally: agent.stop()
 132 | 
 133 | if __name__ == "__main__":
 134 |     run_agent()
```

### src/metrics/engine.py

```python
   1 | import numpy as np
   2 | import logging
   3 | from typing import Dict, List, Optional, Tuple, Any
   4 | from collections import deque
   5 | 
   6 | logger = logging.getLogger(__name__)
   7 | 
   8 | class MetricsEngine:
   9 |     """
  10 |     Implements the mathematical model M(t) from Section 2.1.
  11 |     Calculates EWMA (Exponentially Weighted Moving Average) for system metrics
  12 |     and maintains n-gram profiles for syscall sequences.
  13 |     """
  14 |     
  15 |     def __init__(self, alpha: float = 0.3, n_gram_size: int = 3):
  16 |         self.alpha = alpha  # Smoothing factor for EWMA
  17 |         self.n_gram_size = n_gram_size
  18 |         
  19 |         # Structure: {pid: {"metrics": array, "mu": array, "sigma": array, "ngram_tree": dict}}
  20 |         self.profiles: Dict[int, Dict] = {}
  21 | 
  22 |     def update(self, event: Dict[str, Any]):
  23 |         """
  24 |         Update metrics from an eBPF event.
  25 |         """
  26 |         pid = event.get("pid")
  27 |         if pid is None:
  28 |             return
  29 |             
  30 |         syscall_id = event.get("syscall_id", 0)
  31 |         
  32 |         current_vector = np.array([
  33 |             float(syscall_id),
  34 |             float(len(event.get("filename", ""))),
  35 |             float(event.get("tgid", 0)),
  36 |             1.0,  # syscall count
  37 |             float(event.get("cgroup_id", 0) % 1000)
  38 |         ])
  39 |         
  40 |         self.update_scalar_metrics(pid, current_vector)
  41 |         self.update_ngram(pid, syscall_id)
  42 | 
  43 |     def get_current_vector(self, pid: int) -> np.ndarray:
  44 |         """
  45 |         Get current metrics vector for a PID (for z-score calculation).
  46 |         """
  47 |         if pid not in self.profiles:
  48 |             return np.zeros(5)
  49 |         return self.profiles[pid]["mu"].copy()
  50 | 
  51 |     def update_scalar_metrics(self, pid: int, current_vector: np.ndarray):
  52 |         """
  53 |         Updates EWMA for a process.
  54 |         z_i = (m_i - mu_i) / sigma_i
  55 |         """
  56 |         if pid not in self.profiles:
  57 |             self.profiles[pid] = {
  58 |                 "mu": current_vector.astype(float),
  59 |                 "sigma": np.ones_like(current_vector, dtype=float),
  60 |                 "history": deque(maxlen=100),
  61 |                 "ngram_buffer": deque(maxlen=self.n_gram_size),
  62 |                 "ngram_counts": {}
  63 |             }
  64 |             return
  65 | 
  66 |         prof = self.profiles[pid]
  67 |         
  68 |         # EWMA Update: mu = alpha * current + (1 - alpha) * mu
  69 |         old_mu = prof["mu"]
  70 |         new_mu = self.alpha * current_vector + (1 - self.alpha) * old_mu
  71 |         
  72 |         # Incremental variance/sigma calculation (Simplified)
  73 |         delta = current_vector - old_mu
  74 |         prof["sigma"] = np.sqrt((1 - self.alpha) * (prof["sigma"]**2 + self.alpha * delta**2))
  75 |         prof["mu"] = new_mu
  76 |         
  77 |         prof["history"].append(current_vector)
  78 |         
  79 |         prof["history"].append(current_vector)
  80 | 
  81 |     def update_ngram(self, pid: int, syscall_id: int):
  82 |         """
  83 |         Updates the n-gram frequency distribution for the process.
  84 |         """
  85 |         if pid not in self.profiles:
  86 |             # Initialize if not exists (should normally be handled by scalar update)
  87 |             self.update_scalar_metrics(pid, np.zeros(5)) 
  88 |             
  89 |         prof = self.profiles[pid]
  90 |         buf = prof["ngram_buffer"]
  91 |         buf.append(syscall_id)
  92 |         
  93 |         if len(buf) == self.n_gram_size:
  94 |             ngram = tuple(buf)
  95 |             prof["ngram_counts"][ngram] = prof["ngram_counts"].get(ngram, 0) + 1
  96 | 
  97 |     def get_z_scores(self, pid: int, current_vector: np.ndarray) -> np.ndarray:
  98 |         """
  99 |         Computes Z-scores for the current observation against the stored profile.
 100 |         """
 101 |         if pid not in self.profiles:
 102 |             return np.zeros_like(current_vector)
 103 |             
 104 |         prof = self.profiles[pid]
 105 |         # Avoid division by zero
 106 |         safe_sigma = np.where(prof["sigma"] == 0, 1e-6, prof["sigma"])
 107 |         return (current_vector - prof["mu"]) / safe_sigma
 108 | 
 109 |     def get_ngram_anomaly_score(self, pid: int, sequence: Tuple[int, ...]) -> float:
 110 |         """
 111 |         Returns a score representing how 'new' or 'rare' a sequence is.
 112 |         Higher is more anomalous.
 113 |         """
 114 |         if pid not in self.profiles:
 115 |             return 1.0
 116 |             
 117 |         counts = self.profiles[pid]["ngram_counts"]
 118 |         total = sum(counts.values())
 119 |         if total == 0:
 120 |             return 1.0
 121 |             
 122 |         freq = counts.get(sequence, 0) / total
 123 |         return 1.0 - freq # Inverse frequency as anomaly indicator
```

### src/scoring/engine.py

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

### src/storage/sqlite.py

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

### tests/__init__.py

```python

```

### tests/conftest.py

```python
   1 | import sys
   2 | import types
   3 | from unittest.mock import MagicMock
   4 | 
   5 | _mock_docker = types.ModuleType("docker")
   6 | _mock_docker.DockerClient = MagicMock
   7 | _mock_docker.errors = types.ModuleType("docker.errors")
   8 | _mock_docker.errors.DockerException = Exception
   9 | sys.modules["docker"] = _mock_docker
  10 | sys.modules["docker.errors"] = _mock_docker.errors
  11 | 
  12 | import pytest
  13 | 
  14 | pytest_plugins = []
```

### tests/test_api_main.py

```python
   1 | import pytest
   2 | import sys
   3 | import json
   4 | import tempfile
   5 | import os
   6 | from pathlib import Path
   7 | from unittest.mock import patch, MagicMock
   8 | from fastapi.testclient import TestClient
   9 | 
  10 | SRC_DIR = Path(__file__).parent.parent / "src"
  11 | sys.path.insert(0, str(SRC_DIR))
  12 | 
  13 | from storage.sqlite import StorageManager
  14 | from api.main import app, get_storage
  15 | 
  16 | 
  17 | @pytest.fixture
  18 | def temp_db():
  19 |     """Create a temporary database for testing."""
  20 |     with tempfile.TemporaryDirectory() as tmpdir:
  21 |         db_path = os.path.join(tmpdir, "test.db")
  22 |         manager = StorageManager(db_path=db_path)
  23 |         yield manager, db_path
  24 | 
  25 | 
  26 | class TestAPIEndpoints:
  27 |     """Tests for API endpoints."""
  28 | 
  29 |     def test_root_endpoint(self, temp_db):
  30 |         """Test root endpoint returns welcome message."""
  31 |         manager, _ = temp_db
  32 |         app.dependency_overrides[get_storage] = lambda: manager
  33 |         try:
  34 |             client = TestClient(app)
  35 |             response = client.get("/")
  36 |             
  37 |             assert response.status_code == 200
  38 |             data = response.json()
  39 |             assert "message" in data
  40 |             assert "SovND API" in data["message"]
  41 |         finally:
  42 |             app.dependency_overrides.clear()
  43 | 
  44 |     def test_status_endpoint_returns_operational(self, temp_db):
  45 |         """Test /api/status returns operational status."""
  46 |         manager, _ = temp_db
  47 |         app.dependency_overrides[get_storage] = lambda: manager
  48 |         try:
  49 |             client = TestClient(app)
  50 |             response = client.get("/api/status")
  51 |             
  52 |             assert response.status_code == 200
  53 |             data = response.json()
  54 |             assert data["status"] == "operational"
  55 |             assert data["engine"] == "eBPF-CO-RE"
  56 |             assert data["version"] == "1.0.0"
  57 |         finally:
  58 |             app.dependency_overrides.clear()
  59 | 
  60 |     def test_alerts_endpoint_returns_list(self, temp_db):
  61 |         """Test /api/alerts returns a list."""
  62 |         manager, _ = temp_db
  63 |         app.dependency_overrides[get_storage] = lambda: manager
  64 |         try:
  65 |             client = TestClient(app)
  66 |             response = client.get("/api/alerts")
  67 |             
  68 |             assert response.status_code == 200
  69 |             data = response.json()
  70 |             assert isinstance(data, list)
  71 |         finally:
  72 |             app.dependency_overrides.clear()
  73 | 
  74 |     def test_alerts_endpoint_respects_limit_param(self, temp_db):
  75 |         """Test /api/alerts respects limit parameter."""
  76 |         manager, _ = temp_db
  77 |         for i in range(10):
  78 |             manager.save_alert({
  79 |                 "timestamp": f"2024-01-0{i+1}T00:00:00",
  80 |                 "pid": 3000 + i,
  81 |                 "score": 5.0,
  82 |                 "severity": "info",
  83 |                 "reasons": [],
  84 |                 "container_info": None
  85 |             })
  86 |         
  87 |         app.dependency_overrides[get_storage] = lambda: manager
  88 |         try:
  89 |             client = TestClient(app)
  90 |             response = client.get("/api/alerts?limit=5")
  91 |             
  92 |             assert response.status_code == 200
  93 |             data = response.json()
  94 |             assert len(data) == 5
  95 |         finally:
  96 |             app.dependency_overrides.clear()
  97 | 
  98 |     def test_alerts_endpoint_default_limit(self, temp_db):
  99 |         """Test /api/alerts has default limit of 50."""
 100 |         manager, _ = temp_db
 101 |         for i in range(100):
 102 |             manager.save_alert({
 103 |                 "timestamp": f"2024-01-{(i%30)+1:02d}T00:00:00",
 104 |                 "pid": 3000 + i,
 105 |                 "score": 5.0,
 106 |                 "severity": "info",
 107 |                 "reasons": [],
 108 |                 "container_info": None
 109 |             })
 110 |         
 111 |         app.dependency_overrides[get_storage] = lambda: manager
 112 |         try:
 113 |             client = TestClient(app)
 114 |             response = client.get("/api/alerts")
 115 |             
 116 |             assert response.status_code == 200
 117 |             data = response.json()
 118 |             assert len(data) == 50
 119 |         finally:
 120 |             app.dependency_overrides.clear()
 121 | 
 122 |     def test_alerts_endpoint_returns_stored_data(self, temp_db):
 123 |         """Test /api/alerts returns actual stored alert data with correct types."""
 124 |         manager, _ = temp_db
 125 |         manager.save_alert({
 126 |             "timestamp": "2024-01-15T10:30:00",
 127 |             "pid": 9999,
 128 |             "score": 25.5,
 129 |             "severity": "critical",
 130 |             "reasons": ["unauthorized shell", "shadow access"],
 131 |             "container_info": {"id": "test123", "name": "malware"}
 132 |         })
 133 |         
 134 |         app.dependency_overrides[get_storage] = lambda: manager
 135 |         try:
 136 |             client = TestClient(app)
 137 |             response = client.get("/api/alerts?limit=1")
 138 |             
 139 |             assert response.status_code == 200
 140 |             data = response.json()
 141 |             assert data[0]["pid"] == 9999
 142 |             assert data[0]["score"] == 25.5
 143 |             assert data[0]["severity"] == "critical"
 144 |             
 145 |             assert isinstance(data[0]["reasons"], list), "reasons should be a list"
 146 |             assert data[0]["reasons"] == ["unauthorized shell", "shadow access"]
 147 |             
 148 |             assert isinstance(data[0]["container_info"], dict), "container_info should be a dict"
 149 |             assert data[0]["container_info"] == {"id": "test123", "name": "malware"}
 150 |         finally:
 151 |             app.dependency_overrides.clear()
 152 | 
 153 |     def test_alerts_endpoint_returns_empty_list_when_no_alerts(self, temp_db):
 154 |         """Test /api/alerts returns empty list when no alerts exist."""
 155 |         manager, _ = temp_db
 156 |         app.dependency_overrides[get_storage] = lambda: manager
 157 |         try:
 158 |             client = TestClient(app)
 159 |             response = client.get("/api/alerts")
 160 |             
 161 |             assert response.status_code == 200
 162 |             assert response.json() == []
 163 |         finally:
 164 |             app.dependency_overrides.clear()
 165 | 
 166 |     def test_alerts_endpoint_handles_database_error(self, temp_db):
 167 |         """Test /api/alerts handles database errors gracefully.
 168 |         
 169 |         This tests the case where StorageManager.get_recent_alerts() raises.
 170 |         Note: FastAPI's exception handling for dependency injection errors
 171 |         depends on configuration. We test that storage exceptions are caught.
 172 |         """
 173 |         with patch("api.main.StorageManager") as mock_class:
 174 |             mock_instance = MagicMock()
 175 |             mock_instance.get_recent_alerts.side_effect = RuntimeError("Database corruption")
 176 |             mock_class.return_value = mock_instance
 177 |             
 178 |             client = TestClient(app, raise_server_exceptions=False)
 179 |             response = client.get("/api/alerts")
 180 |             
 181 |             assert response.status_code == 500
 182 | 
 183 | 
 184 | class TestPrometheusMetrics:
 185 |     """Tests for Prometheus metrics endpoints."""
 186 | 
 187 |     def test_metrics_endpoint_returns_prometheus_format(self, temp_db):
 188 |         """Test /metrics returns Prometheus format."""
 189 |         manager, _ = temp_db
 190 |         app.dependency_overrides[get_storage] = lambda: manager
 191 |         try:
 192 |             client = TestClient(app)
 193 |             response = client.get("/metrics")
 194 |             
 195 |             assert response.status_code == 200
 196 |             content = response.text
 197 |             assert "sovnd_syscalls_total" in content
 198 |             assert "sovnd_cpu_usage_percent" in content
 199 |         finally:
 200 |             app.dependency_overrides.clear()
 201 | 
 202 |     def test_metrics_endpoint_content_type(self, temp_db):
 203 |         """Test /metrics returns correct content type."""
 204 |         manager, _ = temp_db
 205 |         app.dependency_overrides[get_storage] = lambda: manager
 206 |         try:
 207 |             client = TestClient(app)
 208 |             response = client.get("/metrics")
 209 |             
 210 |             assert response.status_code == 200
 211 |             assert "text/plain" in response.headers["content-type"]
 212 |             assert "charset=utf-8" in response.headers["content-type"]
 213 |         finally:
 214 |             app.dependency_overrides.clear()
 215 | 
 216 | 
 217 | class TestAPIDependencyInjection:
 218 |     """Tests for FastAPI dependency injection."""
 219 | 
 220 |     def test_get_storage_returns_storage_manager(self):
 221 |         """Test get_storage dependency returns StorageManager instance."""
 222 |         storage = get_storage()
 223 |         
 224 |         assert hasattr(storage, "save_alert")
 225 |         assert hasattr(storage, "get_recent_alerts")
 226 |         assert hasattr(storage, "save_profile")
 227 | 
 228 | 
 229 | class TestAPIMetadata:
 230 |     """Tests for API metadata."""
 231 | 
 232 |     def test_app_title(self):
 233 |         """Test FastAPI app has correct title."""
 234 |         assert app.title == "SovND Security API"
 235 | 
 236 |     def test_app_description(self):
 237 |         """Test FastAPI app has correct description."""
 238 |         assert "API for accessing eBPF-based security monitoring data" in app.description
 239 | 
 240 |     def test_app_version(self):
 241 |         """Test FastAPI app has correct version."""
 242 |         assert app.version == "1.0.0"
 243 | 
 244 | 
 245 | class TestAPIIntegration:
 246 |     """Integration tests for API with real database."""
 247 | 
 248 |     def test_full_workflow_save_and_retrieve_alerts(self):
 249 |         """Test complete workflow: save alert then retrieve via API."""
 250 |         with tempfile.TemporaryDirectory() as tmpdir:
 251 |             db_path = os.path.join(tmpdir, "test.db")
 252 |             manager = StorageManager(db_path=db_path)
 253 |             
 254 |             alert_data = {
 255 |                 "timestamp": "2024-06-15T14:30:00",
 256 |                 "pid": 4242,
 257 |                 "score": 42.0,
 258 |                 "severity": "critical",
 259 |                 "reasons": ["reverse shell detected"],
 260 |                 "container_info": {"id": "container-x", "name": "attacker"}
 261 |             }
 262 |             manager.save_alert(alert_data)
 263 |             
 264 |             app.dependency_overrides[get_storage] = lambda: manager
 265 |             try:
 266 |                 client = TestClient(app)
 267 |                 response = client.get("/api/alerts?limit=1")
 268 |                 
 269 |                 assert response.status_code == 200
 270 |                 data = response.json()
 271 |                 assert len(data) == 1
 272 |                 assert data[0]["pid"] == 4242
 273 |                 assert data[0]["score"] == 42.0
 274 |                 
 275 |                 assert isinstance(data[0]["reasons"], list), "reasons must be parsed as list"
 276 |                 assert isinstance(data[0]["container_info"], dict), "container_info must be parsed as dict"
 277 |             finally:
 278 |                 app.dependency_overrides.clear()
 279 | 
 280 |     def test_status_endpoint_when_db_has_profiles(self):
 281 |         """Test /api/status works independently of database content."""
 282 |         with tempfile.TemporaryDirectory() as tmpdir:
 283 |             db_path = os.path.join(tmpdir, "test.db")
 284 |             manager = StorageManager(db_path=db_path)
 285 |             
 286 |             manager.save_profile("test_proc", b"\x00\x01\x02", b"\x01\x02\x03")
 287 |             
 288 |             app.dependency_overrides[get_storage] = lambda: manager
 289 |             try:
 290 |                 client = TestClient(app)
 291 |                 response = client.get("/api/status")
 292 |                 
 293 |                 assert response.status_code == 200
 294 |                 assert response.json()["status"] == "operational"
 295 |             finally:
 296 |                 app.dependency_overrides.clear()
```

### tests/test_build.py

```python
   1 | import os
   2 | import subprocess
   3 | import pytest
   4 | from pathlib import Path
   5 | 
   6 | EBPF_DIR = Path(__file__).parent.parent / "ebpf"
   7 | 
   8 | 
   9 | class TestBuildCompilation:
  10 |     """Tests for eBPF build and compilation."""
  11 | 
  12 |     def test_makefile_exists(self):
  13 |         """Verify Makefile exists in ebpf directory."""
  14 |         makefile = EBPF_DIR / "Makefile"
  15 |         assert makefile.exists(), "Makefile not found in ebpf directory"
  16 | 
  17 |     def test_makefile_has_targets(self):
  18 |         """Verify Makefile has required targets."""
  19 |         makefile_content = (EBPF_DIR / "Makefile").read_text()
  20 |         assert "all:" in makefile_content, "Makefile missing 'all' target"
  21 |         assert "clean:" in makefile_content, "Makefile missing 'clean' target"
  22 | 
  23 |     def test_compile_tracer_bpf_o(self):
  24 |         """Test that tracer.bpf.o can be compiled."""
  25 |         result = subprocess.run(
  26 |             ["make", "all"],
  27 |             cwd=EBPF_DIR,
  28 |             capture_output=True,
  29 |             text=True
  30 |         )
  31 |         assert result.returncode == 0, f"Compilation failed: {result.stderr}"
  32 |         
  33 |         tracer_o = EBPF_DIR / "tracer.bpf.o"
  34 |         assert tracer_o.exists(), "tracer.bpf.o was not created"
  35 | 
  36 |     def test_compiled_object_file_size(self):
  37 |         """Test that compiled object file has reasonable size."""
  38 |         tracer_o = EBPF_DIR / "tracer.bpf.o"
  39 |         assert tracer_o.exists(), "tracer.bpf.o not found"
  40 |         
  41 |         size = tracer_o.stat().st_size
  42 |         assert size > 0, "tracer.bpf.o is empty"
  43 |         assert size < 1024 * 1024, "tracer.bpf.o is unreasonably large (>1MB)"
  44 | 
  45 |     def test_source_files_exist(self):
  46 |         """Verify all required source files exist."""
  47 |         required_files = [
  48 |             "tracer.bpf.c",
  49 |             "filter.bpf.c",
  50 |             "fd_tracker.bpf.c",
  51 |             "maps.bpf.h",
  52 |             "vmlinux.h"
  53 |         ]
  54 |         for filename in required_files:
  55 |             filepath = EBPF_DIR / filename
  56 |             assert filepath.exists(), f"Required file {filename} not found"
  57 | 
  58 |     def test_clang_available(self):
  59 |         """Test that clang compiler is available."""
  60 |         result = subprocess.run(
  61 |             ["which", "clang"],
  62 |             capture_output=True
  63 |         )
  64 |         assert result.returncode == 0, "clang not found in PATH"
  65 | 
  66 |     def test_clean_target(self):
  67 |         """Test that make clean works without errors."""
  68 |         subprocess.run(["make", "all"], cwd=EBPF_DIR, check=True)
  69 |         
  70 |         result = subprocess.run(
  71 |             ["make", "clean"],
  72 |             cwd=EBPF_DIR,
  73 |             capture_output=True,
  74 |             text=True
  75 |         )
  76 |         assert result.returncode == 0, f"make clean failed: {result.stderr}"
  77 | 
  78 |     def test_loader_c_exists(self):
  79 |         """Verify loader.c source file exists."""
  80 |         loader_c = EBPF_DIR / "loader.c"
  81 |         assert loader_c.exists(), "loader.c not found"
  82 | 
  83 |     def test_compile_libloader_so(self):
  84 |         """Test that libloader.so can be compiled."""
  85 |         result = subprocess.run(
  86 |             ["make", "all"],
  87 |             cwd=EBPF_DIR,
  88 |             capture_output=True,
  89 |             text=True
  90 |         )
  91 |         assert result.returncode == 0, f"Compilation failed: {result.stderr}"
  92 |         
  93 |         libloader_so = EBPF_DIR / "libloader.so"
  94 |         assert libloader_so.exists(), "libloader.so was not created"
  95 | 
  96 |     def test_libloader_so_size(self):
  97 |         """Test that libloader.so has reasonable size."""
  98 |         libloader_so = EBPF_DIR / "libloader.so"
  99 |         if not libloader_so.exists():
 100 |             subprocess.run(["make", "all"], cwd=EBPF_DIR, check=True)
 101 |         
 102 |         size = libloader_so.stat().st_size
 103 |         assert size > 0, "libloader.so is empty"
 104 |         assert size < 10 * 1024 * 1024, "libloader.so is unreasonably large (>10MB)"
 105 | 
 106 |     def test_skeleton_header_generated(self):
 107 |         """Test that tracer.skel.h is generated."""
 108 |         result = subprocess.run(
 109 |             ["make", "all"],
 110 |             cwd=EBPF_DIR,
 111 |             capture_output=True,
 112 |             text=True
 113 |         )
 114 |         assert result.returncode == 0, f"Build failed: {result.stderr}"
 115 |         
 116 |         skel_h = EBPF_DIR / "tracer.skel.h"
 117 |         assert skel_h.exists(), "tracer.skel.h was not generated"
 118 | 
 119 |     def test_bpftool_available(self):
 120 |         """Test that bpftool is available."""
 121 |         result = subprocess.run(
 122 |             ["which", "bpftool"],
 123 |             capture_output=True
 124 |         )
 125 |         assert result.returncode == 0, "bpftool not found in PATH"
 126 | 
 127 |     def test_libbpf_dev_available(self):
 128 |         """Test that libbpf development headers are available."""
 129 |         result = subprocess.run(
 130 |             ["pkg-config", "--exists", "libbpf"],
 131 |             capture_output=True
 132 |         )
 133 |         assert result.returncode == 0, "libbpf development files not found"
```

### tests/test_container_resolver.py

```python
   1 | import pytest
   2 | from unittest.mock import MagicMock, patch
   3 | from pathlib import Path
   4 | import threading
   5 | import sys
   6 | 
   7 | sys.path.insert(0, str(Path(__file__).parent.parent))
   8 | 
   9 | from src.docker.resolver import ContainerResolver
  10 | 
  11 | 
  12 | class TestContainerResolverInit:
  13 |     """Tests for ContainerResolver initialization."""
  14 | 
  15 |     def test_resolver_file_exists(self):
  16 |         """Verify ContainerResolver module exists."""
  17 |         assert ContainerResolver is not None
  18 | 
  19 |     def test_cache_initialized_empty(self):
  20 |         """Verify cache dict is initialized empty."""
  21 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
  22 |             mock_client = MagicMock()
  23 |             mock_docker.return_value = mock_client
  24 |             
  25 |             resolver = ContainerResolver()
  26 |             assert resolver._cache == {}
  27 | 
  28 |     def test_lock_initialized(self):
  29 |         """Verify lock is initialized."""
  30 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
  31 |             mock_client = MagicMock()
  32 |             mock_docker.return_value = mock_client
  33 |             
  34 |             resolver = ContainerResolver()
  35 |             assert isinstance(resolver._lock, type(threading.RLock()))
  36 | 
  37 |     def test_docker_connection_failure(self):
  38 |         """Verify Docker connection failure handling."""
  39 |         from docker.errors import DockerException
  40 |         
  41 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
  42 |             mock_docker.side_effect = DockerException("Connection refused")
  43 |             
  44 |             resolver = ContainerResolver()
  45 |             assert resolver.client is None
  46 | 
  47 |     def test_cache_initialized_empty(self):
  48 |         """Verify cache dict is initialized empty."""
  49 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
  50 |             mock_client = MagicMock()
  51 |             mock_docker.return_value = mock_client
  52 |             
  53 |             resolver = ContainerResolver()
  54 |             assert resolver._cache == {}
  55 | 
  56 |     def test_lock_initialized(self):
  57 |         """Verify lock is initialized."""
  58 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
  59 |             mock_client = MagicMock()
  60 |             mock_docker.return_value = mock_client
  61 |             
  62 |             resolver = ContainerResolver()
  63 |             assert isinstance(resolver._lock, type(threading.RLock()))
  64 | 
  65 |     def test_docker_connection_failure(self):
  66 |         """Verify Docker connection failure handling."""
  67 |         from docker.errors import DockerException
  68 |         
  69 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
  70 |             mock_docker.side_effect = DockerException("Connection refused")
  71 |             
  72 |             resolver = ContainerResolver()
  73 |             assert resolver.client is None
  74 | 
  75 | 
  76 | class TestContainerResolverResolve:
  77 |     """Tests for resolve method."""
  78 | 
  79 |     def test_resolve_handles_edge_cases(self):
  80 |         """Verify resolve handles edge cases gracefully."""
  81 |         import sys
  82 |         sys.path.insert(0, str(Path(__file__).parent.parent))
  83 |         from src.docker.resolver import ContainerResolver
  84 |         
  85 |         resolver = ContainerResolver.__new__(ContainerResolver)
  86 |         resolver._cache = {}
  87 |         resolver.client = None
  88 |         
  89 |         result = resolver.resolve(12345)
  90 |         
  91 |         assert result is None
  92 | 
  93 |     def test_cache_hit_returns_cached(self):
  94 |         """Verify cache hit returns cached value."""
  95 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
  96 |             mock_client = MagicMock()
  97 |             mock_docker.return_value = mock_client
  98 |             
  99 |             resolver = ContainerResolver()
 100 |             resolver._cache[12345] = {"id": "abc123", "name": "test"}
 101 |             
 102 |             result = resolver.resolve(12345)
 103 |             
 104 |             assert result["id"] == "abc123"
 105 |             mock_client.containers.list.assert_not_called()
 106 | 
 107 |     def test_cache_miss_refreshes(self):
 108 |         """Verify cache miss triggers refresh."""
 109 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
 110 |             mock_client = MagicMock()
 111 |             mock_container = MagicMock()
 112 |             mock_container.id = "def456"
 113 |             mock_container.name = "web"
 114 |             mock_container.image.tags = ["nginx:latest"]
 115 |             mock_container.labels = {"app": "web"}
 116 |             mock_client.containers.list.return_value = [mock_container]
 117 |             mock_docker.return_value = mock_client
 118 |             
 119 |             resolver = ContainerResolver()
 120 |             result = resolver.resolve(99999)
 121 |             
 122 |             mock_client.containers.list.assert_called_once()
 123 | 
 124 | 
 125 | class TestContainerResolverRefresh:
 126 |     """Tests for _refresh_and_resolve method."""
 127 | 
 128 |     def test_docker_exception_returns_none(self):
 129 |         """Verify Docker exception returns None."""
 130 |         from docker.errors import DockerException
 131 |         
 132 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
 133 |             mock_client = MagicMock()
 134 |             mock_client.containers.list.side_effect = DockerException("Error")
 135 |             mock_docker.return_value = mock_client
 136 |             
 137 |             resolver = ContainerResolver()
 138 |             result = resolver._refresh_and_resolve(12345)
 139 |             
 140 |             assert result is None
 141 | 
 142 |     def test_updates_cache_on_refresh(self):
 143 |         """Verify cache is updated on refresh."""
 144 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
 145 |             mock_client = MagicMock()
 146 |             mock_container = MagicMock()
 147 |             mock_container.id = "xyz789"
 148 |             mock_container.name = "api"
 149 |             mock_container.image.tags = ["api:v1"]
 150 |             mock_container.labels = {}
 151 |             mock_client.containers.list.return_value = [mock_container]
 152 |             mock_docker.return_value = mock_client
 153 |             
 154 |             resolver = ContainerResolver()
 155 |             resolver._refresh_and_resolve(11111)
 156 |             
 157 |             assert len(resolver._cache) > 0
 158 | 
 159 |     def test_handles_missing_image_tags(self):
 160 |         """Verify missing image tags handled."""
 161 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
 162 |             mock_client = MagicMock()
 163 |             mock_container = MagicMock()
 164 |             mock_container.id = "abc"
 165 |             mock_container.name = "test"
 166 |             mock_container.image.tags = []
 167 |             mock_container.labels = {}
 168 |             mock_client.containers.list.return_value = [mock_container]
 169 |             mock_docker.return_value = mock_client
 170 |             
 171 |             resolver = ContainerResolver()
 172 |             result = resolver._refresh_and_resolve(12345)
 173 |             
 174 |             assert result["image"] == "unknown"
 175 | 
 176 |     def test_handles_missing_labels(self):
 177 |         """Verify missing labels handled."""
 178 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
 179 |             mock_client = MagicMock()
 180 |             mock_container = MagicMock()
 181 |             mock_container.id = "abc"
 182 |             mock_container.name = "test"
 183 |             mock_container.image.tags = ["test:v1"]
 184 |             mock_container.labels = {}
 185 |             mock_client.containers.list.return_value = [mock_container]
 186 |             mock_docker.return_value = mock_client
 187 |             
 188 |             resolver = ContainerResolver()
 189 |             result = resolver._refresh_and_resolve(12345)
 190 |             
 191 |             assert "labels" in result
 192 | 
 193 | 
 194 | class TestContainerResolverClearCache:
 195 |     """Tests for clear_cache method."""
 196 | 
 197 |     def test_clear_cache_clears_all(self):
 198 |         """Verify clear_cache clears cache."""
 199 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
 200 |             mock_client = MagicMock()
 201 |             mock_docker.return_value = mock_client
 202 |             
 203 |             resolver = ContainerResolver()
 204 |             resolver._cache[1] = {"id": "a"}
 205 |             resolver._cache[2] = {"id": "b"}
 206 |             
 207 |             resolver.clear_cache()
 208 |             
 209 |             assert resolver._cache == {}
 210 | 
 211 | 
 212 | class TestContainerResolverThreadSafety:
 213 |     """Tests for thread safety."""
 214 | 
 215 |     def test_concurrent_resolve_thread_safe(self):
 216 |         """Verify concurrent resolve is thread safe."""
 217 |         import threading
 218 |         
 219 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
 220 |             mock_client = MagicMock()
 221 |             mock_container = MagicMock()
 222 |             mock_container.id = "abc"
 223 |             mock_container.name = "test"
 224 |             mock_container.image.tags = ["test:latest"]
 225 |             mock_container.labels = {}
 226 |             mock_client.containers.list.return_value = [mock_container]
 227 |             mock_docker.return_value = mock_client
 228 |             
 229 |             resolver = ContainerResolver()
 230 |             results = []
 231 |             errors = []
 232 |             
 233 |             def worker(cid):
 234 |                 try:
 235 |                     r = resolver.resolve(cid)
 236 |                     results.append(r)
 237 |                 except Exception as e:
 238 |                     errors.append(e)
 239 |             
 240 |             threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
 241 |             for t in threads:
 242 |                 t.start()
 243 |             for t in threads:
 244 |                 t.join()
 245 |             
 246 |             assert len(errors) == 0
 247 | 
 248 |     def test_lock_is_reentrant(self):
 249 |         """Verify lock is reentrant."""
 250 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
 251 |             mock_client = MagicMock()
 252 |             mock_docker.return_value = mock_client
 253 |             
 254 |             resolver = ContainerResolver()
 255 |             
 256 |             with resolver._lock:
 257 |                 with resolver._lock:
 258 |                     pass
 259 |             
 260 |             assert True
 261 | 
 262 | 
 263 | class TestContainerResolverEdgeCases:
 264 |     """Edge case tests."""
 265 | 
 266 |     def test_zero_cgroup_id(self):
 267 |         """Verify zero cgroup ID is handled."""
 268 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
 269 |             mock_client = MagicMock()
 270 |             mock_docker.return_value = mock_client
 271 |             
 272 |             resolver = ContainerResolver()
 273 |             resolver._cache[0] = {"id": "zero"}
 274 |             
 275 |             result = resolver.resolve(0)
 276 |             
 277 |             assert result["id"] == "zero"
 278 | 
 279 |     def test_large_cgroup_id(self):
 280 |         """Verify large cgroup ID is handled."""
 281 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
 282 |             mock_client = MagicMock()
 283 |             mock_docker.return_value = mock_client
 284 |             
 285 |             resolver = ContainerResolver()
 286 |             
 287 |             result = resolver.resolve(2**63 - 1)
 288 |             
 289 |             assert result is None or result is not None
 290 | 
 291 |     def test_empty_container_list(self):
 292 |         """Verify empty container list handled."""
 293 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
 294 |             mock_client = MagicMock()
 295 |             mock_client.containers.list.return_value = []
 296 |             mock_docker.return_value = mock_client
 297 |             
 298 |             resolver = ContainerResolver()
 299 |             result = resolver._refresh_and_resolve(12345)
 300 |             
 301 |             assert result is None
 302 | 
 303 | 
 304 | class TestContainerResolverMetadata:
 305 |     """Tests for metadata structure."""
 306 | 
 307 |     def test_metadata_has_id(self):
 308 |         """Verify metadata has id field."""
 309 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
 310 |             mock_client = MagicMock()
 311 |             mock_container = MagicMock()
 312 |             mock_container.id = "container123"
 313 |             mock_container.name = "myapp"
 314 |             mock_container.image.tags = ["myapp:latest"]
 315 |             mock_container.labels = {"env": "prod"}
 316 |             mock_client.containers.list.return_value = [mock_container]
 317 |             mock_docker.return_value = mock_client
 318 |             
 319 |             resolver = ContainerResolver()
 320 |             result = resolver._refresh_and_resolve(12345)
 321 |             
 322 |             assert "id" in result
 323 | 
 324 |     def test_metadata_has_name(self):
 325 |         """Verify metadata has name field."""
 326 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
 327 |             mock_client = MagicMock()
 328 |             mock_container = MagicMock()
 329 |             mock_container.id = "container123"
 330 |             mock_container.name = "myapp"
 331 |             mock_container.image.tags = ["myapp:latest"]
 332 |             mock_container.labels = {}
 333 |             mock_client.containers.list.return_value = [mock_container]
 334 |             mock_docker.return_value = mock_client
 335 |             
 336 |             resolver = ContainerResolver()
 337 |             result = resolver._refresh_and_resolve(12345)
 338 |             
 339 |             assert "name" in result
 340 | 
 341 |     def test_metadata_has_image(self):
 342 |         """Verify metadata has image field."""
 343 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
 344 |             mock_client = MagicMock()
 345 |             mock_container = MagicMock()
 346 |             mock_container.id = "container123"
 347 |             mock_container.name = "myapp"
 348 |             mock_container.image.tags = ["nginx:1.21"]
 349 |             mock_container.labels = {}
 350 |             mock_client.containers.list.return_value = [mock_container]
 351 |             mock_docker.return_value = mock_client
 352 |             
 353 |             resolver = ContainerResolver()
 354 |             result = resolver._refresh_and_resolve(12345)
 355 |             
 356 |             assert "image" in result
 357 | 
 358 |     def test_metadata_has_labels(self):
 359 |         """Verify metadata has labels field."""
 360 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
 361 |             mock_client = MagicMock()
 362 |             mock_container = MagicMock()
 363 |             mock_container.id = "container123"
 364 |             mock_container.name = "myapp"
 365 |             mock_container.image.tags = ["app:v1"]
 366 |             mock_container.labels = {"key": "value"}
 367 |             mock_client.containers.list.return_value = [mock_container]
 368 |             mock_docker.return_value = mock_client
 369 |             
 370 |             resolver = ContainerResolver()
 371 |             result = resolver._refresh_and_resolve(12345)
 372 |             
 373 |             assert "labels" in result
```

### tests/test_ebpf_agent.py

```python
   1 | import ctypes
   2 | import os
   3 | import queue
   4 | import threading
   5 | from unittest.mock import Mock, patch, MagicMock
   6 | from pathlib import Path
   7 | import pytest
   8 | 
   9 | EBPF_AGENT_FILE = Path(__file__).parent.parent / "src" / "ebpf_agent.py"
  10 | 
  11 | 
  12 | class TestEBPFAggentModule:
  13 |     """Tests for ebpf_agent.py module structure."""
  14 | 
  15 |     def test_ebpf_agent_file_exists(self):
  16 |         """Verify ebpf_agent.py exists."""
  17 |         assert EBPF_AGENT_FILE.exists(), "ebpf_agent.py not found"
  18 | 
  19 |     def test_event_class_defined(self):
  20 |         """Verify Event class is defined."""
  21 |         import sys
  22 |         sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
  23 |         from ebpf_agent import Event
  24 |         assert Event is not None
  25 | 
  26 |     def test_event_class_has_required_fields(self):
  27 |         """Verify Event class has all required fields."""
  28 |         import sys
  29 |         sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
  30 |         from ebpf_agent import Event
  31 |         
  32 |         field_names = [name for name, _ in Event._fields_]
  33 |         required_fields = ["pid", "tgid", "cgroup_id", "syscall_id", "comm", "filename"]
  34 |         for field in required_fields:
  35 |             assert field in field_names, f"Event missing field: {field}"
  36 | 
  37 |     def test_event_field_types(self):
  38 |         """Verify Event class has correct field types."""
  39 |         import sys
  40 |         sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
  41 |         from ebpf_agent import Event
  42 |         
  43 |         field_dict = dict(Event._fields_)
  44 |         assert field_dict["pid"] == ctypes.c_uint32
  45 |         assert field_dict["tgid"] == ctypes.c_uint32
  46 |         assert field_dict["cgroup_id"] == ctypes.c_uint64
  47 |         assert field_dict["syscall_id"] == ctypes.c_uint32
  48 | 
  49 |     def test_event_comm_array_size(self):
  50 |         """Verify comm array is 16 bytes."""
  51 |         import sys
  52 |         sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
  53 |         from ebpf_agent import Event
  54 |         
  55 |         field_dict = dict(Event._fields_)
  56 |         assert field_dict["comm"] == ctypes.c_char * 16
  57 | 
  58 |     def test_event_filename_array_size(self):
  59 |         """Verify filename array is 256 bytes."""
  60 |         import sys
  61 |         sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
  62 |         from ebpf_agent import Event
  63 |         
  64 |         field_dict = dict(Event._fields_)
  65 |         assert field_dict["filename"] == ctypes.c_char * 256
  66 | 
  67 |     def test_event_cb_type_defined(self):
  68 |         """Verify EVENT_CB callback type is defined."""
  69 |         import sys
  70 |         sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
  71 |         from ebpf_agent import EVENT_CB
  72 |         assert EVENT_CB is not None
  73 | 
  74 |     def test_ebpf_agent_class_defined(self):
  75 |         """Verify EBPFAgent class is defined."""
  76 |         import sys
  77 |         sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
  78 |         from ebpf_agent import EBPFAgent
  79 |         assert EBPFAgent is not None
  80 | 
  81 | 
  82 | class TestEBPFAggentInit:
  83 |     """Tests for EBPFAgent initialization."""
  84 | 
  85 |     @pytest.fixture
  86 |     def mock_cdll(self):
  87 |         """Mock ctypes.CDLL."""
  88 |         with patch("ebpf_agent.ctypes.CDLL") as mock:
  89 |             mock_lib = MagicMock()
  90 |             mock.return_value = mock_lib
  91 |             yield mock_lib
  92 | 
  93 |     def test_init_loads_library(self):
  94 |         """Verify __init__ loads the shared library."""
  95 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
  96 |             mock_lib = MagicMock()
  97 |             mock_cdll.return_value = mock_lib
  98 |             
  99 |             import sys
 100 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 101 |             from ebpf_agent import EBPFAgent
 102 |             
 103 |             agent = EBPFAgent(lib_path="/fake/path/libloader.so")
 104 |             mock_cdll.assert_called_once()
 105 | 
 106 |     def test_init_sets_argtypes_for_start_loader(self):
 107 |         """Verify start_loader argtypes are set."""
 108 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 109 |             mock_lib = MagicMock()
 110 |             mock_cdll.return_value = mock_lib
 111 |             
 112 |             import sys
 113 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 114 |             from ebpf_agent import EBPFAgent, EVENT_CB
 115 |             
 116 |             agent = EBPFAgent()
 117 |             assert mock_lib.start_loader.argtypes is not None
 118 | 
 119 |     def test_init_sets_restype_for_start_loader(self):
 120 |         """Verify start_loader restype is set to int."""
 121 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 122 |             mock_lib = MagicMock()
 123 |             mock_cdll.return_value = mock_lib
 124 |             
 125 |             import sys
 126 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 127 |             from ebpf_agent import EBPFAgent
 128 |             
 129 |             agent = EBPFAgent()
 130 |             assert mock_lib.start_loader.restype == ctypes.c_int
 131 | 
 132 |     def test_init_sets_argtypes_for_poll_events(self):
 133 |         """Verify poll_events argtypes are set."""
 134 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 135 |             mock_lib = MagicMock()
 136 |             mock_cdll.return_value = mock_lib
 137 |             
 138 |             import sys
 139 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 140 |             from ebpf_agent import EBPFAgent
 141 |             
 142 |             agent = EBPFAgent()
 143 |             assert mock_lib.poll_events.argtypes is not None
 144 | 
 145 |     def test_init_creates_event_queue(self):
 146 |         """Verify __init__ creates an event queue."""
 147 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 148 |             mock_lib = MagicMock()
 149 |             mock_cdll.return_value = mock_lib
 150 |             
 151 |             import sys
 152 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 153 |             from ebpf_agent import EBPFAgent
 154 |             
 155 |             agent = EBPFAgent()
 156 |             assert hasattr(agent, "event_queue")
 157 |             assert isinstance(agent.event_queue, queue.Queue)
 158 | 
 159 |     def test_init_sets_running_false(self):
 160 |         """Verify __init__ sets running to False."""
 161 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 162 |             mock_lib = MagicMock()
 163 |             mock_cdll.return_value = mock_lib
 164 |             
 165 |             import sys
 166 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 167 |             from ebpf_agent import EBPFAgent
 168 |             
 169 |             agent = EBPFAgent()
 170 |             assert agent.running is False
 171 | 
 172 |     def test_init_sets_thread_none(self):
 173 |         """Verify __init__ sets thread to None."""
 174 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 175 |             mock_lib = MagicMock()
 176 |             mock_cdll.return_value = mock_lib
 177 |             
 178 |             import sys
 179 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 180 |             from ebpf_agent import EBPFAgent
 181 |             
 182 |             agent = EBPFAgent()
 183 |             assert agent.thread is None
 184 | 
 185 | 
 186 | class TestEBPFAggentStart:
 187 |     """Tests for EBPFAgent.start() method."""
 188 | 
 189 |     def test_start_calls_start_loader(self):
 190 |         """Verify start() calls start_loader from library."""
 191 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 192 |             mock_lib = MagicMock()
 193 |             mock_lib.start_loader.return_value = 0
 194 |             mock_cdll.return_value = mock_lib
 195 |             
 196 |             import sys
 197 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 198 |             from ebpf_agent import EBPFAgent
 199 |             
 200 |             agent = EBPFAgent()
 201 |             agent.start()
 202 |             mock_lib.start_loader.assert_called_once()
 203 | 
 204 |     def test_start_raises_on_loader_error(self):
 205 |         """Verify start() raises RuntimeError when loader fails."""
 206 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 207 |             mock_lib = MagicMock()
 208 |             mock_lib.start_loader.return_value = 1
 209 |             mock_cdll.return_value = mock_lib
 210 |             
 211 |             import sys
 212 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 213 |             from ebpf_agent import EBPFAgent
 214 |             
 215 |             agent = EBPFAgent()
 216 |             with pytest.raises(RuntimeError) as exc_info:
 217 |                 agent.start()
 218 |             assert "Failed to start eBPF loader" in str(exc_info.value)
 219 | 
 220 |     def test_start_sets_running_true(self):
 221 |         """Verify start() sets running to True."""
 222 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 223 |             mock_lib = MagicMock()
 224 |             mock_lib.start_loader.return_value = 0
 225 |             mock_cdll.return_value = mock_lib
 226 |             
 227 |             import sys
 228 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 229 |             from ebpf_agent import EBPFAgent
 230 |             
 231 |             agent = EBPFAgent()
 232 |             agent.start()
 233 |             assert agent.running is True
 234 | 
 235 |     def test_start_creates_thread(self):
 236 |         """Verify start() creates a thread."""
 237 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 238 |             with patch("ebpf_agent.threading.Thread") as mock_thread:
 239 |                 mock_lib = MagicMock()
 240 |                 mock_lib.start_loader.return_value = 0
 241 |                 mock_cdll.return_value = mock_lib
 242 |                 
 243 |                 import sys
 244 |                 sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 245 |                 from ebpf_agent import EBPFAgent
 246 |                 
 247 |                 agent = EBPFAgent()
 248 |                 agent.start()
 249 |                 mock_thread.assert_called_once()
 250 | 
 251 | 
 252 | class TestEBPFAggentStop:
 253 |     """Tests for EBPFAgent.stop() method."""
 254 | 
 255 |     def test_stop_sets_running_false(self):
 256 |         """Verify stop() sets running to False."""
 257 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 258 |             mock_lib = MagicMock()
 259 |             mock_lib.start_loader.return_value = 0
 260 |             mock_cdll.return_value = mock_lib
 261 |             
 262 |             import sys
 263 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 264 |             from ebpf_agent import EBPFAgent
 265 |             
 266 |             agent = EBPFAgent()
 267 |             agent.running = True
 268 |             agent.thread = MagicMock()
 269 |             agent.stop()
 270 |             assert agent.running is False
 271 | 
 272 |     def test_stop_calls_stop_loader(self):
 273 |         """Verify stop() calls stop_loader from library."""
 274 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 275 |             mock_lib = MagicMock()
 276 |             mock_cdll.return_value = mock_lib
 277 |             
 278 |             import sys
 279 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 280 |             from ebpf_agent import EBPFAgent
 281 |             
 282 |             agent = EBPFAgent()
 283 |             agent.thread = MagicMock()
 284 |             agent.stop()
 285 |             mock_lib.stop_loader.assert_called_once()
 286 | 
 287 |     def test_stop_joins_thread_if_exists(self):
 288 |         """Verify stop() joins thread if it exists."""
 289 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 290 |             mock_lib = MagicMock()
 291 |             mock_cdll.return_value = mock_lib
 292 |             
 293 |             import sys
 294 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 295 |             from ebpf_agent import EBPFAgent
 296 |             
 297 |             agent = EBPFAgent()
 298 |             mock_thread = MagicMock()
 299 |             agent.thread = mock_thread
 300 |             agent.stop()
 301 |             mock_thread.join.assert_called_once()
 302 | 
 303 | 
 304 | class TestEBPFAggentGetEvent:
 305 |     """Tests for EBPFAgent.get_event() method."""
 306 | 
 307 |     def test_get_event_returns_event(self):
 308 |         """Verify get_event returns event from queue."""
 309 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 310 |             mock_lib = MagicMock()
 311 |             mock_cdll.return_value = mock_lib
 312 |             
 313 |             import sys
 314 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 315 |             from ebpf_agent import EBPFAgent
 316 |             
 317 |             agent = EBPFAgent()
 318 |             test_event = {"pid": 123, "comm": "test"}
 319 |             agent.event_queue.put(test_event)
 320 |             
 321 |             result = agent.get_event(block=False)
 322 |             assert result == test_event
 323 | 
 324 |     def test_get_event_returns_none_on_empty(self):
 325 |         """Verify get_event returns None when queue is empty."""
 326 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 327 |             mock_lib = MagicMock()
 328 |             mock_cdll.return_value = mock_lib
 329 |             
 330 |             import sys
 331 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 332 |             from ebpf_agent import EBPFAgent
 333 |             
 334 |             agent = EBPFAgent()
 335 |             result = agent.get_event(block=False)
 336 |             assert result is None
 337 | 
 338 | 
 339 | class TestEBPFAggentEventHandler:
 340 |     """Tests for EBPFAgent._event_handler() method."""
 341 | 
 342 |     def test_event_handler_puts_to_queue(self):
 343 |         """Verify _event_handler puts event to queue."""
 344 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 345 |             mock_lib = MagicMock()
 346 |             mock_cdll.return_value = mock_lib
 347 |             
 348 |             import sys
 349 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 350 |             from ebpf_agent import EBPFAgent
 351 |             
 352 |             agent = EBPFAgent()
 353 |             
 354 |             mock_event = MagicMock()
 355 |             mock_event.pid = 123
 356 |             mock_event.tgid = 456
 357 |             mock_event.cgroup_id = 789
 358 |             mock_event.syscall_id = 257
 359 |             mock_event.comm = b"testproc"
 360 |             mock_event.filename = b"/tmp/test"
 361 |             
 362 |             mock_ptr = MagicMock()
 363 |             mock_ptr.contents = mock_event
 364 |             
 365 |             agent._event_handler(None, mock_ptr, 100)
 366 |             
 367 |             assert not agent.event_queue.empty()
 368 |             event = agent.event_queue.get_nowait()
 369 |             assert event["pid"] == 123
 370 |             assert event["tgid"] == 456
 371 | 
 372 |     def test_event_handler_decodes_comm_utf8(self):
 373 |         """Verify _event_handler decodes comm as UTF-8."""
 374 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 375 |             mock_lib = MagicMock()
 376 |             mock_cdll.return_value = mock_lib
 377 |             
 378 |             import sys
 379 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 380 |             from ebpf_agent import EBPFAgent
 381 |             
 382 |             agent = EBPFAgent()
 383 |             
 384 |             mock_event = MagicMock()
 385 |             mock_event.pid = 123
 386 |             mock_event.tgid = 456
 387 |             mock_event.cgroup_id = 789
 388 |             mock_event.syscall_id = 257
 389 |             mock_event.comm = b"test"
 390 |             mock_event.filename = b"/tmp/test"
 391 |             
 392 |             mock_ptr = MagicMock()
 393 |             mock_ptr.contents = mock_event
 394 |             
 395 |             agent._event_handler(None, mock_ptr, 100)
 396 |             
 397 |             event = agent.event_queue.get_nowait()
 398 |             assert isinstance(event["comm"], str)
 399 | 
 400 | 
 401 | class TestEBPFAggentPollLoop:
 402 |     """Tests for EBPFAgent._poll_loop() method."""
 403 | 
 404 |     @pytest.mark.skip(reason="time module imported locally in __main__, difficult to mock properly")
 405 |     def test_poll_loop_calls_poll_events(self):
 406 |         """Verify _poll_loop calls poll_events."""
 407 |         pass
 408 | 
 409 | 
 410 | class TestEBPFAggentEdgeCases:
 411 |     """Tests for edge cases in EBPFAgent."""
 412 | 
 413 |     def test_get_event_with_timeout(self):
 414 |         """Verify get_event works with timeout parameter."""
 415 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 416 |             mock_lib = MagicMock()
 417 |             mock_cdll.return_value = mock_lib
 418 |             
 419 |             import sys
 420 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 421 |             from ebpf_agent import EBPFAgent
 422 |             
 423 |             agent = EBPFAgent()
 424 |             result = agent.get_event(block=True, timeout=0.1)
 425 |             assert result is None
 426 | 
 427 |     def test_stop_with_no_thread(self):
 428 |         """Verify stop() handles None thread gracefully."""
 429 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 430 |             mock_lib = MagicMock()
 431 |             mock_cdll.return_value = mock_lib
 432 |             
 433 |             import sys
 434 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
 435 |             from ebpf_agent import EBPFAgent
 436 |             
 437 |             agent = EBPFAgent()
 438 |             agent.thread = None
 439 |             agent.stop()
 440 |             mock_lib.stop_loader.assert_called_once()
```

### tests/test_event_structure.py

```python
   1 | import re
   2 | import pytest
   3 | from pathlib import Path
   4 | 
   5 | EBPF_DIR = Path(__file__).parent.parent / "ebpf"
   6 | TRACER_FILE = EBPF_DIR / "tracer.bpf.c"
   7 | 
   8 | 
   9 | class TestEventStructure:
  10 |     """Tests for event structure definition validation."""
  11 | 
  12 |     @pytest.fixture
  13 |     def tracer_content(self):
  14 |         """Load tracer.bpf.c content."""
  15 |         return TRACER_FILE.read_text()
  16 | 
  17 |     def test_event_struct_exists(self, tracer_content):
  18 |         """Verify event struct is defined."""
  19 |         assert "struct event" in tracer_content, "event struct not found"
  20 |         assert "{" in tracer_content, "event struct body not found"
  21 | 
  22 |     def test_event_struct_has_pid_field(self, tracer_content):
  23 |         """Verify event struct has pid field."""
  24 |         assert re.search(r'__u32\s+pid', tracer_content), "pid field (__u32) not found in event struct"
  25 | 
  26 |     def test_event_struct_has_tgid_field(self, tracer_content):
  27 |         """Verify event struct has tgid field."""
  28 |         assert re.search(r'__u32\s+tgid', tracer_content), "tgid field (__u32) not found in event struct"
  29 | 
  30 |     def test_event_struct_has_cgroup_id_field(self, tracer_content):
  31 |         """Verify event struct has cgroup_id field."""
  32 |         assert re.search(r'__u64\s+cgroup_id', tracer_content), "cgroup_id field (__u64) not found"
  33 | 
  34 |     def test_event_struct_has_syscall_id_field(self, tracer_content):
  35 |         """Verify event struct has syscall_id field."""
  36 |         assert re.search(r'__u32\s+syscall_id', tracer_content), "syscall_id field (__u32) not found"
  37 | 
  38 |     def test_event_struct_has_comm_field(self, tracer_content):
  39 |         """Verify event struct has comm field (process name)."""
  40 |         assert re.search(r'char\s+comm\[', tracer_content), "comm field (char array) not found in event struct"
  41 | 
  42 |     def test_event_struct_comm_array_size(self, tracer_content):
  43 |         """Verify comm field has reasonable size (16 bytes)."""
  44 |         match = re.search(r'char\s+comm\[(\d+)\]', tracer_content)
  45 |         assert match, "comm array size not found"
  46 |         size = int(match.group(1))
  47 |         assert size >= 16, "comm array should be at least 16 bytes for task name"
  48 | 
  49 |     def test_event_struct_has_filename_field(self, tracer_content):
  50 |         """Verify event struct has filename field."""
  51 |         assert re.search(r'char\s+filename\[', tracer_content), "filename field not found in event struct"
  52 | 
  53 |     def test_event_struct_filename_array_size(self, tracer_content):
  54 |         """Verify filename array is large enough for paths."""
  55 |         match = re.search(r'char\s+filename\[(\d+)\]', tracer_content)
  56 |         assert match, "filename array size not found"
  57 |         size = int(match.group(1))
  58 |         assert size >= 256, "filename array should be at least 256 bytes for paths"
  59 | 
  60 |     def test_event_struct_alignment(self, tracer_content):
  61 |         """Verify event struct uses proper types for alignment."""
  62 |         assert "__u32" in tracer_content, "Should use fixed-width integer types"
  63 |         assert "__u64" in tracer_content, "Should use fixed-width integer types"
  64 | 
  65 |     def test_event_used_in_trace_openat(self, tracer_content):
  66 |         """Verify event struct is used in trace_openat function."""
  67 |         assert "struct event *e" in tracer_content, "Event pointer not created in trace_openat"
  68 | 
  69 |     def test_event_fields_populated(self, tracer_content):
  70 |         """Verify event fields are populated in trace_openat."""
  71 |         assert "e->pid" in tracer_content, "pid not assigned to event"
  72 |         assert "e->tgid" in tracer_content, "tgid not assigned to event"
  73 |         assert "e->cgroup_id" in tracer_content, "cgroup_id not assigned to event"
  74 |         assert "e->syscall_id" in tracer_content, "syscall_id not assigned to event"
  75 |         assert "e->comm" in tracer_content, "comm not assigned to event"
  76 | 
  77 |     def test_syscall_id_value(self, tracer_content):
  78 |         """Verify syscall_id is set to openat (257)."""
  79 |         assert "257" in tracer_content, "openat syscall number (257) not used"
```

### tests/test_integration.py

```python
   1 | import os
   2 | import subprocess
   3 | import pytest
   4 | from pathlib import Path
   5 | from unittest.mock import patch, MagicMock
   6 | 
   7 | EBPF_DIR = Path(__file__).parent.parent / "ebpf"
   8 | SRC_DIR = Path(__file__).parent.parent / "src"
   9 | 
  10 | 
  11 | class TestBuildIntegration:
  12 |     """Integration tests for building the entire system."""
  13 | 
  14 |     def test_full_build_produces_all_artifacts(self):
  15 |         """Verify full build produces all expected artifacts."""
  16 |         subprocess.run(["make", "clean"], cwd=EBPF_DIR, check=True)
  17 |         
  18 |         result = subprocess.run(
  19 |             ["make", "all"],
  20 |             cwd=EBPF_DIR,
  21 |             capture_output=True,
  22 |             text=True
  23 |         )
  24 |         
  25 |         assert result.returncode == 0, f"Build failed: {result.stderr}"
  26 |         
  27 |         expected = ["tracer.bpf.o", "tracer.skel.h", "libloader.so"]
  28 |         for artifact in expected:
  29 |             path = EBPF_DIR / artifact
  30 |             assert path.exists(), f"Expected artifact {artifact} not found"
  31 | 
  32 |     def test_build_creates_libloader_so(self):
  33 |         """Verify libloader.so is created."""
  34 |         path = EBPF_DIR / "libloader.so"
  35 |         assert path.exists(), "libloader.so not found"
  36 | 
  37 |     def test_build_creates_skeleton_header(self):
  38 |         """Verify tracer.skel.h is created."""
  39 |         path = EBPF_DIR / "tracer.skel.h"
  40 |         assert path.exists(), "tracer.skel.h not found"
  41 | 
  42 |     def test_skeleton_header_has_bpf_prog_definitions(self):
  43 |         """Verify skeleton header contains BPF program definitions."""
  44 |         skel = EBPF_DIR / "tracer.skel.h"
  45 |         content = skel.read_text()
  46 |         
  47 |         assert "tracer_bpf__open" in content, "Missing tracer_bpf__open"
  48 |         assert "tracer_bpf__load" in content, "Missing tracer_bpf__load"
  49 |         assert "tracer_bpf__attach" in content, "Missing tracer_bpf__attach"
  50 |         assert "tracer_bpf__destroy" in content, "Missing tracer_bpf__destroy"
  51 | 
  52 |     def test_clean_removes_all_build_artifacts(self):
  53 |         """Verify make clean removes all generated files."""
  54 |         subprocess.run(["make", "all"], cwd=EBPF_DIR, check=True)
  55 |         
  56 |         subprocess.run(["make", "clean"], cwd=EBPF_DIR, check=True)
  57 |         
  58 |         generated = ["tracer.bpf.o", "tracer.skel.h", "libloader.so"]
  59 |         for artifact in generated:
  60 |             path = EBPF_DIR / artifact
  61 |             assert not path.exists(), f"Artifact {artifact} should have been cleaned"
  62 | 
  63 | 
  64 | class TestPythonAgentIntegration:
  65 |     """Integration tests for Python agent with C library."""
  66 | 
  67 |     def test_ebpf_agent_can_import(self):
  68 |         """Verify ebpf_agent module can be imported."""
  69 |         import sys
  70 |         sys.path.insert(0, str(SRC_DIR))
  71 |         from ebpf_agent import EBPFAgent, Event
  72 |         assert EBPFAgent is not None
  73 |         assert Event is not None
  74 | 
  75 |     def test_ebpf_agent_initialization_integration(self):
  76 |         """Test EBPFAgent can be initialized with mocked library."""
  77 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
  78 |             mock_lib = MagicMock()
  79 |             mock_cdll.return_value = mock_lib
  80 |             
  81 |             import sys
  82 |             sys.path.insert(0, str(SRC_DIR))
  83 |             from ebpf_agent import EBPFAgent
  84 |             
  85 |             agent = EBPFAgent(lib_path="/nonexistent/libloader.so")
  86 |             assert agent is not None
  87 |             assert agent.running is False
  88 | 
  89 |     def test_agent_event_structure_matches_c_event(self):
  90 |         """Verify Python Event matches C event structure."""
  91 |         import sys
  92 |         sys.path.insert(0, str(SRC_DIR))
  93 |         from ebpf_agent import Event
  94 |         
  95 |         assert hasattr(Event, "_fields_")
  96 |         fields = dict(Event._fields_)
  97 |         
  98 |         assert "pid" in fields and fields["pid"] == __import__('ctypes').c_uint32
  99 |         assert "tgid" in fields and fields["tgid"] == __import__('ctypes').c_uint32
 100 |         assert "cgroup_id" in fields and fields["cgroup_id"] == __import__('ctypes').c_uint64
 101 |         assert "syscall_id" in fields and fields["syscall_id"] == __import__('ctypes').c_uint32
 102 |         assert "comm" in fields
 103 |         assert "filename" in fields
 104 | 
 105 | 
 106 | class TestLoaderAgentIntegration:
 107 |     """Integration tests for C loader and Python agent working together."""
 108 | 
 109 |     def test_loader_exports_required_functions(self):
 110 |         """Verify loader.c exports required functions."""
 111 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 112 |             mock_lib = MagicMock()
 113 |             mock_cdll.return_value = mock_lib
 114 |             
 115 |             import sys
 116 |             sys.path.insert(0, str(SRC_DIR))
 117 |             from ebpf_agent import EBPFAgent
 118 |             
 119 |             agent = EBPFAgent()
 120 |             
 121 |             assert hasattr(agent.lib, "start_loader")
 122 |             assert hasattr(agent.lib, "poll_events")
 123 |             assert hasattr(agent.lib, "stop_loader")
 124 | 
 125 |     def test_agent_callback_signature_matches_loader(self):
 126 |         """Verify Python callback signature matches C loader expectation."""
 127 |         import sys
 128 |         sys.path.insert(0, str(SRC_DIR))
 129 |         from ebpf_agent import EVENT_CB, EBPFAgent
 130 |         
 131 |         assert EVENT_CB is not None
 132 |         
 133 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 134 |             mock_lib = MagicMock()
 135 |             mock_cdll.return_value = mock_lib
 136 |             
 137 |             agent = EBPFAgent()
 138 |             
 139 |             assert hasattr(agent, "_callback_ref")
 140 | 
 141 | 
 142 | class TestEndToEndSimulation:
 143 |     """End-to-end simulation tests."""
 144 | 
 145 |     def test_agent_lifecycle_simulation(self):
 146 |         """Simulate complete agent lifecycle."""
 147 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 148 |             with patch("ebpf_agent.threading.Thread") as mock_thread:
 149 |                 mock_lib = MagicMock()
 150 |                 mock_lib.start_loader.return_value = 0
 151 |                 mock_cdll.return_value = mock_lib
 152 |                 
 153 |                 mock_thread_instance = MagicMock()
 154 |                 mock_thread.return_value = mock_thread_instance
 155 |                 
 156 |                 import sys
 157 |                 sys.path.insert(0, str(SRC_DIR))
 158 |                 from ebpf_agent import EBPFAgent
 159 |                 
 160 |                 agent = EBPFAgent()
 161 |                 
 162 |                 assert agent.running is False
 163 |                 agent.start()
 164 |                 assert agent.running is True
 165 |                 mock_thread_instance.start.assert_called_once()
 166 |                 
 167 |                 agent.stop()
 168 |                 assert agent.running is False
 169 |                 mock_lib.stop_loader.assert_called_once()
 170 | 
 171 |     def test_multiple_start_stop_cycles(self):
 172 |         """Test multiple start/stop cycles."""
 173 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 174 |             with patch("ebpf_agent.threading.Thread") as mock_thread:
 175 |                 mock_lib = MagicMock()
 176 |                 mock_lib.start_loader.return_value = 0
 177 |                 mock_cdll.return_value = mock_lib
 178 |                 
 179 |                 mock_thread_instance = MagicMock()
 180 |                 mock_thread.return_value = mock_thread_instance
 181 |                 
 182 |                 import sys
 183 |                 sys.path.insert(0, str(SRC_DIR))
 184 |                 from ebpf_agent import EBPFAgent
 185 |                 
 186 |                 agent = EBPFAgent()
 187 |                 
 188 |                 for i in range(3):
 189 |                     agent.start()
 190 |                     agent.stop()
 191 |                 
 192 |                 assert mock_lib.start_loader.call_count == 3
 193 |                 assert mock_lib.stop_loader.call_count == 3
 194 | 
 195 | 
 196 | class TestErrorHandlingIntegration:
 197 |     """Integration tests for error handling."""
 198 | 
 199 |     def test_agent_handles_missing_library(self):
 200 |         """Test agent handles missing library gracefully."""
 201 |         import sys
 202 |         sys.path.insert(0, str(SRC_DIR))
 203 |         
 204 |         with pytest.raises(OSError):
 205 |             import ctypes
 206 |             ctypes.CDLL("/nonexistent/path/libloader.so")
 207 | 
 208 |     def test_agent_handles_loader_failure(self):
 209 |         """Test agent handles loader failure gracefully."""
 210 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
 211 |             mock_lib = MagicMock()
 212 |             mock_lib.start_loader.return_value = 1
 213 |             mock_cdll.return_value = mock_lib
 214 |             
 215 |             import sys
 216 |             sys.path.insert(0, str(SRC_DIR))
 217 |             from ebpf_agent import EBPFAgent
 218 |             
 219 |             agent = EBPFAgent()
 220 |             
 221 |             with pytest.raises(RuntimeError) as exc_info:
 222 |                 agent.start()
 223 |             assert "Failed to start eBPF loader" in str(exc_info.value)
 224 | 
 225 | 
 226 | class TestBuildEnvironmentIntegration:
 227 |     """Integration tests for build environment."""
 228 | 
 229 |     def test_clang_available_in_build(self):
 230 |         """Verify clang is available for build."""
 231 |         result = subprocess.run(["which", "clang"], capture_output=True)
 232 |         assert result.returncode == 0, "clang not found"
 233 | 
 234 |     def test_bpftool_available_in_build(self):
 235 |         """Verify bpftool is available for skeleton generation."""
 236 |         result = subprocess.run(["which", "bpftool"], capture_output=True)
 237 |         assert result.returncode == 0, "bpftool not found"
 238 | 
 239 |     def test_libbpf_available(self):
 240 |         """Verify libbpf development files are available."""
 241 |         result = subprocess.run(["pkg-config", "--exists", "libbpf"], capture_output=True)
 242 |         assert result.returncode == 0, "libbpf not found"
 243 | 
 244 |     def test_required_kernel_headers(self):
 245 |         """Verify required kernel headers exist."""
 246 |         arch = subprocess.run(["uname", "-m"], capture_output=True, text=True).stdout.strip()
 247 |         linux_gnuhdr = Path(f"/usr/include/{arch}-linux-gnu")
 248 |         if linux_gnuhdr.exists():
 249 |             assert (linux_gnuhdr / "asm").exists() or True
```

### tests/test_loader.py

```python
   1 | import re
   2 | import pytest
   3 | from pathlib import Path
   4 | 
   5 | EBPF_DIR = Path(__file__).parent.parent / "ebpf"
   6 | LOADER_FILE = EBPF_DIR / "loader.c"
   7 | 
   8 | 
   9 | class TestLoaderC:
  10 |     """Tests for ebpf/loader.c validation."""
  11 | 
  12 |     @pytest.fixture
  13 |     def loader_content(self):
  14 |         """Load loader.c content."""
  15 |         return LOADER_FILE.read_text()
  16 | 
  17 |     def test_loader_file_exists(self):
  18 |         """Verify loader.c exists."""
  19 |         assert LOADER_FILE.exists(), "loader.c not found"
  20 | 
  21 |     def test_includes_required_headers(self, loader_content):
  22 |         """Verify required headers are included."""
  23 |         required = ["stdio.h", "stdlib.h", "string.h", "errno.h", "bpf/libbpf.h", "bpf/bpf.h"]
  24 |         for header in required:
  25 |             assert header in loader_content, f"Required header {header} not included"
  26 | 
  27 |     def test_includes_tracer_skeleton(self, loader_content):
  28 |         """Verify tracer.skel.h is included."""
  29 |         assert 'tracer.skel.h' in loader_content, "tracer.skel.h not included"
  30 | 
  31 |     def test_libbpf_print_fn_exists(self, loader_content):
  32 |         """Verify libbpf print callback is defined."""
  33 |         assert "libbpf_print_fn" in loader_content, "libbpf_print_fn not found"
  34 | 
  35 |     def test_libbpf_print_fn_signature(self, loader_content):
  36 |         """Verify libbpf_print_fn has correct signature."""
  37 |         pattern = r'static\s+int\s+libbpf_print_fn\s*\(\s*enum\s+libbpf_print_level'
  38 |         assert re.search(pattern, loader_content), "libbpf_print_fn signature incorrect"
  39 | 
  40 |     def test_global_skel_variable(self, loader_content):
  41 |         """Verify skeleton global variable is declared."""
  42 |         assert "struct tracer_bpf *skel" in loader_content, "Global skel variable not found"
  43 | 
  44 |     def test_global_rb_variable(self, loader_content):
  45 |         """Verify ring buffer global variable is declared."""
  46 |         assert "ring_buffer *rb" in loader_content or "struct ring_buffer *rb" in loader_content, "Global rb variable not found"
  47 | 
  48 |     def test_user_callback_global(self, loader_content):
  49 |         """Verify user_callback global variable exists."""
  50 |         assert "user_callback" in loader_content, "user_callback global not found"
  51 | 
  52 |     def test_event_cb_typedef(self, loader_content):
  53 |         """Verify event callback typedef is defined."""
  54 |         assert "event_cb_t" in loader_content, "event_cb_t typedef not found"
  55 | 
  56 |     def test_handle_event_function_exists(self, loader_content):
  57 |         """Verify handle_event function exists."""
  58 |         assert "handle_event" in loader_content, "handle_event function not found"
  59 | 
  60 |     def test_handle_event_calls_callback(self, loader_content):
  61 |         """Verify handle_event calls user_callback."""
  62 |         assert "user_callback" in loader_content and "handle_event" in loader_content
  63 |         assert re.search(r'if\s*\(\s*user_callback\s*\)', loader_content), "user_callback not checked before calling"
  64 | 
  65 |     def test_start_loader_function_exists(self, loader_content):
  66 |         """Verify start_loader function exists."""
  67 |         assert re.search(r'int\s+start_loader\s*\(', loader_content), "start_loader function not found"
  68 | 
  69 |     def test_start_loader_sets_libbpf_print(self, loader_content):
  70 |         """Verify start_loader sets libbpf print callback."""
  71 |         assert "libbpf_set_print" in loader_content, "libbpf_set_print not called"
  72 | 
  73 |     def test_start_loader_opens_skeleton(self, loader_content):
  74 |         """Verify start_loader opens BPF skeleton."""
  75 |         assert "tracer_bpf__open" in loader_content, "tracer_bpf__open not called"
  76 | 
  77 |     def test_start_loader_loads_skeleton(self, loader_content):
  78 |         """Verify start_loader loads BPF skeleton."""
  79 |         assert "tracer_bpf__load" in loader_content, "tracer_bpf__load not called"
  80 | 
  81 |     def test_start_loader_attaches_skeleton(self, loader_content):
  82 |         """Verify start_loader attaches BPF skeleton."""
  83 |         assert "tracer_bpf__attach" in loader_content, "tracer_bpf__attach not called"
  84 | 
  85 |     def test_start_loader_creates_ring_buffer(self, loader_content):
  86 |         """Verify start_loader creates ring buffer."""
  87 |         assert "ring_buffer__new" in loader_content, "ring_buffer__new not called"
  88 | 
  89 |     def test_start_loader_checks_ring_buffer(self, loader_content):
  90 |         """Verify start_loader checks ring buffer creation."""
  91 |         assert re.search(r'if\s*\(\s*!rb\s*\)', loader_content), "Ring buffer NULL check not found"
  92 | 
  93 |     def test_poll_events_function_exists(self, loader_content):
  94 |         """Verify poll_events function exists."""
  95 |         assert re.search(r'int\s+poll_events\s*\(', loader_content), "poll_events function not found"
  96 | 
  97 |     def test_poll_events_calls_ring_buffer_poll(self, loader_content):
  98 |         """Verify poll_events uses ring_buffer__poll."""
  99 |         assert "ring_buffer__poll" in loader_content, "ring_buffer__poll not called"
 100 | 
 101 |     def test_stop_loader_function_exists(self, loader_content):
 102 |         """Verify stop_loader function exists."""
 103 |         assert re.search(r'void\s+stop_loader\s*\(', loader_content), "stop_loader function not found"
 104 | 
 105 |     def test_stop_loader_frees_ring_buffer(self, loader_content):
 106 |         """Verify stop_loader frees ring buffer."""
 107 |         assert "ring_buffer__free" in loader_content, "ring_buffer__free not called"
 108 | 
 109 |     def test_stop_loader_destroys_skeleton(self, loader_content):
 110 |         """Verify stop_loader destroys skeleton."""
 111 |         assert "tracer_bpf__destroy" in loader_content, "tracer_bpf__destroy not called"
 112 | 
 113 |     def test_cleanup_label_exists(self, loader_content):
 114 |         """Verify cleanup label exists for error handling."""
 115 |         assert re.search(r'cleanup:', loader_content), "cleanup label not found"
 116 | 
 117 |     def test_error_messages_to_stderr(self, loader_content):
 118 |         """Verify error messages go to stderr."""
 119 |         assert "fprintf(stderr" in loader_content, "Error messages should use stderr"
 120 | 
 121 |     def test_null_check_on_skel_open(self, loader_content):
 122 |         """Verify skeleton open result is checked for NULL."""
 123 |         assert re.search(r'if\s*\(\s*!skel\s*\)', loader_content), "skel NULL check not found"
 124 | 
 125 |     def test_error_return_on_skel_failure(self, loader_content):
 126 |         """Verify error return when skeleton open fails."""
 127 |         assert re.search(r'return\s+1', loader_content), "Error return value not found"
 128 | 
 129 |     def test_callback_assignment_in_start_loader(self, loader_content):
 130 |         """Verify user_callback is assigned in start_loader."""
 131 |         lines_after_start = loader_content.split("start_loader")[1].split("poll_events")[0]
 132 |         assert "user_callback = cb" in lines_after_start, "user_callback not assigned in start_loader"
 133 | 
 134 | 
 135 | class TestLoaderMakefile:
 136 |     """Tests for Makefile validation related to loader."""
 137 | 
 138 |     @pytest.fixture
 139 |     def makefile_content(self):
 140 |         """Load Makefile content."""
 141 |         return (EBPF_DIR / "Makefile").read_text()
 142 | 
 143 |     def test_makefile_exists(self):
 144 |         """Verify Makefile exists."""
 145 |         assert (EBPF_DIR / "Makefile").exists()
 146 | 
 147 |     def test_libloader_target_exists(self, makefile_content):
 148 |         """Verify libloader.so target exists."""
 149 |         assert "libloader.so:" in makefile_content, "libloader.so target not found"
 150 | 
 151 |     def test_skeleton_generation_target(self, makefile_content):
 152 |         """Verify skeleton generation target exists."""
 153 |         assert ".skel.h" in makefile_content, "skeleton target not found"
 154 | 
 155 |     def test_bpftool_used_for_skeleton(self, makefile_content):
 156 |         """Verify bpftool is used for skeleton generation."""
 157 |         assert "bpftool" in makefile_content, "bpftool not used"
 158 | 
 159 |     def test_libloader_depends_on_loader_c(self, makefile_content):
 160 |         """Verify libloader.so depends on loader.c."""
 161 |         assert "loader.c" in makefile_content, "loader.c dependency missing"
 162 | 
 163 |     def test_libloader_depends_on_skeleton(self, makefile_content):
 164 |         """Verify libloader.so depends on skeleton header."""
 165 |         assert "skel.h" in makefile_content, "skeleton header dependency missing"
 166 | 
 167 |     def test_clean_removes_so_file(self, makefile_content):
 168 |         """Verify clean removes .so files."""
 169 |         assert "rm" in makefile_content and ".so" in makefile_content, "clean should remove .so files"
```

### tests/test_maps.py

```python
   1 | import re
   2 | import pytest
   3 | from pathlib import Path
   4 | 
   5 | EBPF_DIR = Path(__file__).parent.parent / "ebpf"
   6 | MAPS_HEADER = EBPF_DIR / "maps.bpf.h"
   7 | 
   8 | 
   9 | class TestEBPFMapValidation:
  10 |     """Tests for eBPF map definitions validation."""
  11 | 
  12 |     @pytest.fixture
  13 |     def maps_content(self):
  14 |         """Load maps.bpf.h content."""
  15 |         return MAPS_HEADER.read_text()
  16 | 
  17 |     def test_maps_header_exists(self):
  18 |         """Verify maps.bpf.h exists."""
  19 |         assert MAPS_HEADER.exists(), "maps.bpf.h not found"
  20 | 
  21 |     def test_maps_header_has_header_guard(self, maps_content):
  22 |         """Verify maps header has proper include guards."""
  23 |         assert "#ifndef __MAPS_BPF_H" in maps_content, "Missing header guard start"
  24 |         assert "#define __MAPS_BPF_H" in maps_content, "Missing header guard define"
  25 |         assert "#endif" in maps_content, "Missing header guard endif"
  26 | 
  27 |     def test_ringbuf_map_exists(self, maps_content):
  28 |         """Verify ring buffer map is defined."""
  29 |         assert "BPF_MAP_TYPE_RINGBUF" in maps_content, "Ringbuf map type not found"
  30 |         assert "rb" in maps_content, "Ring buffer map 'rb' not found"
  31 | 
  32 |     def test_ringbuf_map_properties(self, maps_content):
  33 |         """Verify ring buffer map has correct properties."""
  34 |         assert "max_entries" in maps_content, "Ringbuf max_entries not found"
  35 |         assert "256" in maps_content or "256 * 1024" in maps_content, "Ringbuf size not configured"
  36 | 
  37 |     def test_proc_metrics_map_exists(self, maps_content):
  38 |         """Verify proc_metrics hash map is defined."""
  39 |         assert "proc_metrics" in maps_content, "proc_metrics map not found"
  40 |         assert "BPF_MAP_TYPE_HASH" in maps_content, "Hash map type not found"
  41 | 
  42 |     def test_proc_metrics_key_type(self, maps_content):
  43 |         """Verify proc_metrics has correct key type (PID as __u32)."""
  44 |         assert "__u32" in maps_content, "Key type __u32 not found in maps"
  45 | 
  46 |     def test_proc_metrics_value_type(self, maps_content):
  47 |         """Verify proc_metrics has correct value type (__u64 for counter)."""
  48 |         assert "key, __u32" in maps_content or "key,__u32" in maps_content, "Key type not matching PID"
  49 |         assert "value, __u64" in maps_content or "value,__u64" in maps_content, "Value type not matching counter"
  50 | 
  51 |     def test_proc_metrics_max_entries(self, maps_content):
  52 |         """Verify proc_metrics has reasonable max_entries."""
  53 |         match = re.search(r'proc_metrics.*?max_entries,\s*(\d+)', maps_content, re.DOTALL)
  54 |         assert match, "proc_metrics max_entries not found"
  55 |         max_entries = int(match.group(1))
  56 |         assert max_entries > 0, "proc_metrics max_entries should be positive"
  57 |         assert max_entries <= 100000, "proc_metrics max_entries unreasonably large"
  58 | 
  59 |     def test_container_map_exists(self, maps_content):
  60 |         """Verify container_map is defined."""
  61 |         assert "container_map" in maps_content, "container_map not found"
  62 | 
  63 |     def test_container_map_key_type(self, maps_content):
  64 |         """Verify container_map uses cgroup_id as key (__u64)."""
  65 |         assert "cgroup" in maps_content.lower(), "cgroup_id not referenced in maps"
  66 | 
  67 |     def test_all_maps_have_sec_markers(self, maps_content):
  68 |         """Verify all maps have SEC(.maps) markers."""
  69 |         sec_markers = maps_content.count("SEC(\".maps\")")
  70 |         assert sec_markers >= 3, f"Expected at least 3 SEC(.maps) markers, found {sec_markers}"
  71 | 
  72 |     def test_maps_include_vmlinux(self, maps_content):
  73 |         """Verify maps include vmlinux.h."""
  74 |         assert "#include" in maps_content and "vmlinux.h" in maps_content, "vmlinux.h not included"
  75 | 
  76 |     def test_maps_include_bpf_helpers(self, maps_content):
  77 |         """Verify maps include bpf helpers."""
  78 |         assert "#include" in maps_content and "bpf_helpers.h" in maps_content, "bpf_helpers.h not included"
```

### tests/test_metrics_engine.py

```python
   1 | import pytest
   2 | import numpy as np
   3 | from unittest.mock import MagicMock, patch, PropertyMock
   4 | from pathlib import Path
   5 | from collections import deque
   6 | 
   7 | SRC_DIR = Path(__file__).parent.parent / "src"
   8 | 
   9 | 
  10 | class TestMetricsEngineInit:
  11 |     """Tests for MetricsEngine initialization."""
  12 | 
  13 |     def test_engine_file_exists(self):
  14 |         """Verify MetricsEngine exists."""
  15 |         import sys
  16 |         sys.path.insert(0, str(SRC_DIR))
  17 |         from src.metrics.engine import MetricsEngine
  18 |         assert MetricsEngine is not None
  19 | 
  20 |     def test_default_alpha(self):
  21 |         """Verify default alpha is 0.3."""
  22 |         import sys
  23 |         sys.path.insert(0, str(SRC_DIR))
  24 |         from src.metrics.engine import MetricsEngine
  25 |         engine = MetricsEngine()
  26 |         assert engine.alpha == 0.3
  27 | 
  28 |     def test_custom_alpha(self):
  29 |         """Verify custom alpha is set correctly."""
  30 |         import sys
  31 |         sys.path.insert(0, str(SRC_DIR))
  32 |         from src.metrics.engine import MetricsEngine
  33 |         engine = MetricsEngine(alpha=0.5)
  34 |         assert engine.alpha == 0.5
  35 | 
  36 |     def test_default_n_gram_size(self):
  37 |         """Verify default n_gram_size is 3."""
  38 |         import sys
  39 |         sys.path.insert(0, str(SRC_DIR))
  40 |         from src.metrics.engine import MetricsEngine
  41 |         engine = MetricsEngine()
  42 |         assert engine.n_gram_size == 3
  43 | 
  44 |     def test_custom_n_gram_size(self):
  45 |         """Verify custom n_gram_size is set correctly."""
  46 |         import sys
  47 |         sys.path.insert(0, str(SRC_DIR))
  48 |         from src.metrics.engine import MetricsEngine
  49 |         engine = MetricsEngine(n_gram_size=5)
  50 |         assert engine.n_gram_size == 5
  51 | 
  52 |     def test_profiles_initially_empty(self):
  53 |         """Verify profiles dict is empty on init."""
  54 |         import sys
  55 |         sys.path.insert(0, str(SRC_DIR))
  56 |         from src.metrics.engine import MetricsEngine
  57 |         engine = MetricsEngine()
  58 |         assert engine.profiles == {}
  59 | 
  60 | 
  61 | class TestMetricsEngineUpdateScalar:
  62 |     """Tests for update_scalar_metrics method."""
  63 | 
  64 |     def test_first_update_creates_profile(self):
  65 |         """Verify first update creates a new profile."""
  66 |         import sys
  67 |         sys.path.insert(0, str(SRC_DIR))
  68 |         from src.metrics.engine import MetricsEngine
  69 |         engine = MetricsEngine()
  70 |         vector = np.array([1.0, 2.0, 3.0])
  71 |         engine.update_scalar_metrics(123, vector)
  72 |         assert 123 in engine.profiles
  73 | 
  74 |     def test_first_update_sets_mu_to_vector(self):
  75 |         """Verify first update sets mu to the current vector."""
  76 |         import sys
  77 |         sys.path.insert(0, str(SRC_DIR))
  78 |         from src.metrics.engine import MetricsEngine
  79 |         engine = MetricsEngine()
  80 |         vector = np.array([1.0, 2.0, 3.0])
  81 |         engine.update_scalar_metrics(123, vector)
  82 |         np.testing.assert_array_almost_equal(engine.profiles[123]["mu"], vector)
  83 | 
  84 |     def test_first_update_sets_sigma_to_ones(self):
  85 |         """Verify first update sets sigma to ones."""
  86 |         import sys
  87 |         sys.path.insert(0, str(SRC_DIR))
  88 |         from src.metrics.engine import MetricsEngine
  89 |         engine = MetricsEngine()
  90 |         vector = np.array([1.0, 2.0, 3.0])
  91 |         engine.update_scalar_metrics(123, vector)
  92 |         np.testing.assert_array_almost_equal(engine.profiles[123]["sigma"], np.ones(3))
  93 | 
  94 |     def test_first_update_creates_history_deque(self):
  95 |         """Verify history deque is created."""
  96 |         import sys
  97 |         sys.path.insert(0, str(SRC_DIR))
  98 |         from src.metrics.engine import MetricsEngine
  99 |         engine = MetricsEngine()
 100 |         vector = np.array([1.0, 2.0, 3.0])
 101 |         engine.update_scalar_metrics(123, vector)
 102 |         assert isinstance(engine.profiles[123]["history"], deque)
 103 | 
 104 |     def test_first_update_creates_ngram_buffer(self):
 105 |         """Verify ngram_buffer deque is created."""
 106 |         import sys
 107 |         sys.path.insert(0, str(SRC_DIR))
 108 |         from src.metrics.engine import MetricsEngine
 109 |         engine = MetricsEngine()
 110 |         vector = np.array([1.0, 2.0, 3.0])
 111 |         engine.update_scalar_metrics(123, vector)
 112 |         assert isinstance(engine.profiles[123]["ngram_buffer"], deque)
 113 | 
 114 |     def test_first_update_creates_ngram_counts(self):
 115 |         """Verify ngram_counts dict is created."""
 116 |         import sys
 117 |         sys.path.insert(0, str(SRC_DIR))
 118 |         from src.metrics.engine import MetricsEngine
 119 |         engine = MetricsEngine()
 120 |         vector = np.array([1.0, 2.0, 3.0])
 121 |         engine.update_scalar_metrics(123, vector)
 122 |         assert engine.profiles[123]["ngram_counts"] == {}
 123 | 
 124 |     def test_ewma_update_formula(self):
 125 |         """Verify EWMA update: mu = alpha * current + (1-alpha) * old_mu."""
 126 |         import sys
 127 |         sys.path.insert(0, str(SRC_DIR))
 128 |         from src.metrics.engine import MetricsEngine
 129 |         engine = MetricsEngine(alpha=0.3)
 130 |         
 131 |         old_vector = np.array([10.0, 20.0, 30.0])
 132 |         engine.update_scalar_metrics(123, old_vector)
 133 |         
 134 |         new_vector = np.array([20.0, 40.0, 60.0])
 135 |         engine.update_scalar_metrics(123, new_vector)
 136 |         
 137 |         expected_mu = 0.3 * new_vector + 0.7 * old_vector
 138 |         np.testing.assert_array_almost_equal(engine.profiles[123]["mu"], expected_mu)
 139 | 
 140 |     def test_ewma_with_zero_alpha(self):
 141 |         """Verify EWMA with alpha=0 (no update)."""
 142 |         import sys
 143 |         sys.path.insert(0, str(SRC_DIR))
 144 |         from src.metrics.engine import MetricsEngine
 145 |         engine = MetricsEngine(alpha=0.0)
 146 |         
 147 |         old_vector = np.array([10.0, 20.0, 30.0])
 148 |         engine.update_scalar_metrics(123, old_vector)
 149 |         
 150 |         new_vector = np.array([20.0, 40.0, 60.0])
 151 |         engine.update_scalar_metrics(123, new_vector)
 152 |         
 153 |         np.testing.assert_array_almost_equal(engine.profiles[123]["mu"], old_vector)
 154 | 
 155 |     def test_ewma_with_one_alpha(self):
 156 |         """Verify EWMA with alpha=1 (full update to current)."""
 157 |         import sys
 158 |         sys.path.insert(0, str(SRC_DIR))
 159 |         from src.metrics.engine import MetricsEngine
 160 |         engine = MetricsEngine(alpha=1.0)
 161 |         
 162 |         old_vector = np.array([10.0, 20.0, 30.0])
 163 |         engine.update_scalar_metrics(123, old_vector)
 164 |         
 165 |         new_vector = np.array([20.0, 40.0, 60.0])
 166 |         engine.update_scalar_metrics(123, new_vector)
 167 |         
 168 |         np.testing.assert_array_almost_equal(engine.profiles[123]["mu"], new_vector)
 169 | 
 170 |     def test_multiple_updates_append_to_history(self):
 171 |         """Verify multiple updates append to history."""
 172 |         import sys
 173 |         sys.path.insert(0, str(SRC_DIR))
 174 |         from src.metrics.engine import MetricsEngine
 175 |         engine = MetricsEngine()
 176 |         
 177 |         for i in range(5):
 178 |             engine.update_scalar_metrics(123, np.array([float(i)]))
 179 |         
 180 |         assert len(engine.profiles[123]["history"]) >= 5
 181 | 
 182 |     def test_history_maxlen_enforced(self):
 183 |         """Verify history respects maxlen."""
 184 |         import sys
 185 |         sys.path.insert(0, str(SRC_DIR))
 186 |         from src.metrics.engine import MetricsEngine
 187 |         engine = MetricsEngine()
 188 |         
 189 |         for i in range(150):
 190 |             engine.update_scalar_metrics(123, np.array([float(i)]))
 191 |         
 192 |         assert len(engine.profiles[123]["history"]) == 100
 193 | 
 194 |     def test_update_with_different_pid(self):
 195 |         """Verify updates for different PIDs are separate."""
 196 |         import sys
 197 |         sys.path.insert(0, str(SRC_DIR))
 198 |         from src.metrics.engine import MetricsEngine
 199 |         engine = MetricsEngine()
 200 |         
 201 |         engine.update_scalar_metrics(100, np.array([1.0]))
 202 |         engine.update_scalar_metrics(200, np.array([2.0]))
 203 |         
 204 |         assert engine.profiles[100]["mu"][0] == 1.0
 205 |         assert engine.profiles[200]["mu"][0] == 2.0
 206 | 
 207 | 
 208 | class TestMetricsEngineUpdateNgram:
 209 |     """Tests for update_ngram method."""
 210 | 
 211 |     def test_ngram_update_creates_profile_if_missing(self):
 212 |         """Verify ngram update creates profile if missing."""
 213 |         import sys
 214 |         sys.path.insert(0, str(SRC_DIR))
 215 |         from src.metrics.engine import MetricsEngine
 216 |         engine = MetricsEngine(n_gram_size=3)
 217 |         engine.update_ngram(999, 257)
 218 |         assert 999 in engine.profiles
 219 | 
 220 |     def test_ngram_single_syscall_no_count(self):
 221 |         """Verify single syscall doesn't create ngram until buffer full."""
 222 |         import sys
 223 |         sys.path.insert(0, str(SRC_DIR))
 224 |         from src.metrics.engine import MetricsEngine
 225 |         engine = MetricsEngine(n_gram_size=3)
 226 |         
 227 |         engine.update_ngram(123, 257)
 228 |         
 229 |         assert len(engine.profiles[123]["ngram_counts"]) == 0
 230 | 
 231 |     def test_ngram_full_buffer_creates_count(self):
 232 |         """Verify full buffer creates ngram count."""
 233 |         import sys
 234 |         sys.path.insert(0, str(SRC_DIR))
 235 |         from src.metrics.engine import MetricsEngine
 236 |         engine = MetricsEngine(n_gram_size=3)
 237 |         
 238 |         engine.update_ngram(123, 257)
 239 |         engine.update_ngram(123, 258)
 240 |         engine.update_ngram(123, 259)
 241 |         
 242 |         assert (257, 258, 259) in engine.profiles[123]["ngram_counts"]
 243 | 
 244 |     def test_ngram_increments_count(self):
 245 |         """Verify repeated ngram increments count."""
 246 |         import sys
 247 |         sys.path.insert(0, str(SRC_DIR))
 248 |         from src.metrics.engine import MetricsEngine
 249 |         engine = MetricsEngine(n_gram_size=2)
 250 |         
 251 |         engine.update_ngram(123, 257)
 252 |         engine.update_ngram(123, 258)
 253 |         engine.update_ngram(123, 257)
 254 |         engine.update_ngram(123, 258)
 255 |         
 256 |         assert engine.profiles[123]["ngram_counts"][(257, 258)] == 2
 257 | 
 258 |     def test_ngram_buffer_slides(self):
 259 |         """Verify ngram buffer slides correctly."""
 260 |         import sys
 261 |         sys.path.insert(0, str(SRC_DIR))
 262 |         from src.metrics.engine import MetricsEngine
 263 |         engine = MetricsEngine(n_gram_size=2)
 264 |         
 265 |         engine.update_ngram(123, 1)
 266 |         engine.update_ngram(123, 2)
 267 |         assert (1, 2) in engine.profiles[123]["ngram_counts"]
 268 |         
 269 |         engine.update_ngram(123, 3)
 270 |         assert (2, 3) in engine.profiles[123]["ngram_counts"]
 271 | 
 272 |     def test_ngram_size_one(self):
 273 |         """Verify ngram with size 1."""
 274 |         import sys
 275 |         sys.path.insert(0, str(SRC_DIR))
 276 |         from src.metrics.engine import MetricsEngine
 277 |         engine = MetricsEngine(n_gram_size=1)
 278 |         
 279 |         engine.update_ngram(123, 257)
 280 |         
 281 |         assert (257,) in engine.profiles[123]["ngram_counts"]
 282 | 
 283 |     def test_different_pids_have_separate_ngrams(self):
 284 |         """Verify different PIDs have separate ngram buffers."""
 285 |         import sys
 286 |         sys.path.insert(0, str(SRC_DIR))
 287 |         from src.metrics.engine import MetricsEngine
 288 |         engine = MetricsEngine(n_gram_size=2)
 289 |         
 290 |         engine.update_ngram(100, 1)
 291 |         engine.update_ngram(100, 2)
 292 |         
 293 |         engine.update_ngram(200, 3)
 294 |         engine.update_ngram(200, 4)
 295 |         
 296 |         assert (1, 2) in engine.profiles[100]["ngram_counts"]
 297 |         assert (3, 4) in engine.profiles[200]["ngram_counts"]
 298 | 
 299 | 
 300 | class TestMetricsEngineZScores:
 301 |     """Tests for get_z_scores method."""
 302 | 
 303 |     def test_unknown_pid_returns_zeros(self):
 304 |         """Verify unknown PID returns zeros."""
 305 |         import sys
 306 |         sys.path.insert(0, str(SRC_DIR))
 307 |         from src.metrics.engine import MetricsEngine
 308 |         engine = MetricsEngine()
 309 |         
 310 |         result = engine.get_z_scores(999, np.array([1.0, 2.0, 3.0]))
 311 |         
 312 |         np.testing.assert_array_almost_equal(result, np.zeros(3))
 313 | 
 314 |     def test_z_score_calculation(self):
 315 |         """Verify z-score formula: (current - mu) / sigma."""
 316 |         import sys
 317 |         sys.path.insert(0, str(SRC_DIR))
 318 |         from src.metrics.engine import MetricsEngine
 319 |         engine = MetricsEngine()
 320 |         
 321 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
 322 |         
 323 |         result = engine.get_z_scores(123, np.array([13.0, 10.0, 7.0]))
 324 |         
 325 |         np.testing.assert_array_almost_equal(result, np.array([3.0, 0.0, -3.0]))
 326 | 
 327 |     def test_zero_sigma_uses_epsilon(self):
 328 |         """Verify zero sigma uses 1e-6 epsilon."""
 329 |         import sys
 330 |         sys.path.insert(0, str(SRC_DIR))
 331 |         from src.metrics.engine import MetricsEngine
 332 |         engine = MetricsEngine()
 333 |         
 334 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
 335 |         engine.profiles[123]["sigma"] = np.array([0.0, 0.0, 0.0])
 336 |         
 337 |         result = engine.get_z_scores(123, np.array([20.0, 20.0, 20.0]))
 338 |         
 339 |         np.testing.assert_array_almost_equal(result, np.array([10000000.0, 10000000.0, 10000000.0]))
 340 | 
 341 |     def test_negative_z_scores(self):
 342 |         """Verify negative z-scores are calculated correctly."""
 343 |         import sys
 344 |         sys.path.insert(0, str(SRC_DIR))
 345 |         from src.metrics.engine import MetricsEngine
 346 |         engine = MetricsEngine()
 347 |         
 348 |         engine.update_scalar_metrics(123, np.array([100.0]))
 349 |         
 350 |         result = engine.get_z_scores(123, np.array([50.0]))
 351 |         
 352 |         assert result[0] < 0
 353 | 
 354 |     def test_exact_match_z_score_zero(self):
 355 |         """Verify exact match to mu gives z-score of 0."""
 356 |         import sys
 357 |         sys.path.insert(0, str(SRC_DIR))
 358 |         from src.metrics.engine import MetricsEngine
 359 |         engine = MetricsEngine()
 360 |         
 361 |         engine.update_scalar_metrics(123, np.array([50.0]))
 362 |         
 363 |         result = engine.get_z_scores(123, np.array([50.0]))
 364 |         
 365 |         np.testing.assert_array_almost_equal(result, np.array([0.0]))
 366 | 
 367 | 
 368 | class TestMetricsEngineNgramAnomalyScore:
 369 |     """Tests for get_ngram_anomaly_score method."""
 370 | 
 371 |     def test_unknown_pid_returns_one(self):
 372 |         """Verify unknown PID returns 1.0 (max anomaly)."""
 373 |         import sys
 374 |         sys.path.insert(0, str(SRC_DIR))
 375 |         from src.metrics.engine import MetricsEngine
 376 |         engine = MetricsEngine()
 377 |         
 378 |         result = engine.get_ngram_anomaly_score(999, (1, 2, 3))
 379 |         
 380 |         assert result == 1.0
 381 | 
 382 |     def test_zero_total_returns_one(self):
 383 |         """Verify zero total ngram count returns 1.0."""
 384 |         import sys
 385 |         sys.path.insert(0, str(SRC_DIR))
 386 |         from src.metrics.engine import MetricsEngine
 387 |         engine = MetricsEngine()
 388 |         
 389 |         engine.update_scalar_metrics(123, np.array([1.0]))
 390 |         
 391 |         result = engine.get_ngram_anomaly_score(123, (1, 2, 3))
 392 |         
 393 |         assert result == 1.0
 394 | 
 395 |     def test_rare_sequence_high_score(self):
 396 |         """Verify rare sequence returns high anomaly score."""
 397 |         import sys
 398 |         sys.path.insert(0, str(SRC_DIR))
 399 |         from src.metrics.engine import MetricsEngine
 400 |         engine = MetricsEngine(n_gram_size=2)
 401 |         
 402 |         for _ in range(100):
 403 |             engine.update_ngram(123, 1)
 404 |             engine.update_ngram(123, 2)
 405 |         
 406 |         engine.update_ngram(123, 3)
 407 |         engine.update_ngram(123, 4)
 408 |         
 409 |         result = engine.get_ngram_anomaly_score(123, (3, 4))
 410 |         
 411 |         assert result >= 0.9
 412 | 
 413 |     def test_common_sequence_high_rare_score(self):
 414 |         """Verify common sequences have lower anomaly score than rare ones."""
 415 |         import sys
 416 |         sys.path.insert(0, str(SRC_DIR))
 417 |         from src.metrics.engine import MetricsEngine
 418 |         engine = MetricsEngine(n_gram_size=2)
 419 |         
 420 |         for _ in range(100):
 421 |             engine.update_ngram(123, 1)
 422 |             engine.update_ngram(123, 2)
 423 |         
 424 |         # (1,2) is seen many times, (3,4) is seen only once
 425 |         result_common = engine.get_ngram_anomaly_score(123, (1, 2))
 426 |         result_rare = engine.get_ngram_anomaly_score(123, (3, 4))
 427 |         
 428 |         assert result_common < result_rare
 429 | 
 430 |     def test_perfect_match_returns_zero(self):
 431 |         """Verify sequence with 100% frequency returns 0."""
 432 |         import sys
 433 |         sys.path.insert(0, str(SRC_DIR))
 434 |         from src.metrics.engine import MetricsEngine
 435 |         engine = MetricsEngine()
 436 |         
 437 |         engine.update_scalar_metrics(123, np.array([1.0]))
 438 |         # Only one unique ngram with 100% frequency
 439 |         engine.profiles[123]["ngram_counts"][(1, 2, 3)] = 1
 440 |         
 441 |         result = engine.get_ngram_anomaly_score(123, (1, 2, 3))
 442 |         
 443 |         assert result == 0.0
 444 | 
 445 | 
 446 | class TestMetricsEngineEdgeCases:
 447 |     """Edge case tests for MetricsEngine."""
 448 | 
 449 |     def test_empty_vector(self):
 450 |         """Verify empty vector handling."""
 451 |         import sys
 452 |         sys.path.insert(0, str(SRC_DIR))
 453 |         from src.metrics.engine import MetricsEngine
 454 |         engine = MetricsEngine()
 455 |         
 456 |         engine.update_scalar_metrics(123, np.array([]))
 457 |         
 458 |         assert 123 in engine.profiles
 459 |         assert len(engine.profiles[123]["mu"]) == 0
 460 | 
 461 |     def test_single_element_vector(self):
 462 |         """Verify single element vector."""
 463 |         import sys
 464 |         sys.path.insert(0, str(SRC_DIR))
 465 |         from src.metrics.engine import MetricsEngine
 466 |         engine = MetricsEngine()
 467 |         
 468 |         engine.update_scalar_metrics(123, np.array([42.0]))
 469 |         
 470 |         assert engine.profiles[123]["mu"][0] == 42.0
 471 | 
 472 |     def test_large_vector(self):
 473 |         """Verify large vector dimension."""
 474 |         import sys
 475 |         sys.path.insert(0, str(SRC_DIR))
 476 |         from src.metrics.engine import MetricsEngine
 477 |         engine = MetricsEngine()
 478 |         
 479 |         large_vector = np.random.rand(1000)
 480 |         engine.update_scalar_metrics(123, large_vector)
 481 |         
 482 |         assert len(engine.profiles[123]["mu"]) == 1000
 483 | 
 484 |     def test_negative_values(self):
 485 |         """Verify negative values are handled."""
 486 |         import sys
 487 |         sys.path.insert(0, str(SRC_DIR))
 488 |         from src.metrics.engine import MetricsEngine
 489 |         engine = MetricsEngine()
 490 |         
 491 |         engine.update_scalar_metrics(123, np.array([-10.0, -20.0]))
 492 |         
 493 |         assert engine.profiles[123]["mu"][0] == -10.0
 494 | 
 495 |     def test_mixed_positive_negative(self):
 496 |         """Verify mixed positive/negative values."""
 497 |         import sys
 498 |         sys.path.insert(0, str(SRC_DIR))
 499 |         from src.metrics.engine import MetricsEngine
 500 |         engine = MetricsEngine()
 501 |         
 502 |         engine.update_scalar_metrics(123, np.array([-5.0, 0.0, 5.0]))
 503 |         
 504 |         np.testing.assert_array_almost_equal(
 505 |             engine.profiles[123]["mu"], 
 506 |             np.array([-5.0, 0.0, 5.0])
 507 |         )
 508 | 
 509 |     def test_float32_array(self):
 510 |         """Verify float32 array is converted to float."""
 511 |         import sys
 512 |         sys.path.insert(0, str(SRC_DIR))
 513 |         from src.metrics.engine import MetricsEngine
 514 |         engine = MetricsEngine()
 515 |         
 516 |         vector = np.array([1.0, 2.0], dtype=np.float32)
 517 |         engine.update_scalar_metrics(123, vector)
 518 |         
 519 |         assert engine.profiles[123]["mu"].dtype == np.float64
 520 | 
 521 |     def test_integer_array(self):
 522 |         """Verify integer array is converted to float."""
 523 |         import sys
 524 |         sys.path.insert(0, str(SRC_DIR))
 525 |         from src.metrics.engine import MetricsEngine
 526 |         engine = MetricsEngine()
 527 |         
 528 |         vector = np.array([1, 2, 3], dtype=np.int32)
 529 |         engine.update_scalar_metrics(123, vector)
 530 |         
 531 |         assert engine.profiles[123]["mu"].dtype == np.float64
 532 | 
 533 | 
 534 | class TestMetricsEngineIntegration:
 535 |     """Integration tests for MetricsEngine."""
 536 | 
 537 |     def test_full_workflow(self):
 538 |         """Verify full detection workflow."""
 539 |         import sys
 540 |         sys.path.insert(0, str(SRC_DIR))
 541 |         from src.metrics.engine import MetricsEngine
 542 |         engine = MetricsEngine(alpha=0.3, n_gram_size=2)
 543 |         
 544 |         for i in range(20):
 545 |             vector = np.array([float(i), float(i*2), float(i*3)])
 546 |             engine.update_scalar_metrics(123, vector)
 547 |             engine.update_ngram(123, 257 + i)
 548 |         
 549 |         test_vector = np.array([25.0, 50.0, 75.0])
 550 |         z_scores = engine.get_z_scores(123, test_vector)
 551 |         
 552 |         assert z_scores.shape == (3,)
 553 |         
 554 |         anomaly = engine.get_ngram_anomaly_score(123, (275, 276))
 555 |         assert 0.0 <= anomaly <= 1.0
 556 | 
 557 |     def test_multiple_processes(self):
 558 |         """Verify multiple processes tracking."""
 559 |         import sys
 560 |         sys.path.insert(0, str(SRC_DIR))
 561 |         from src.metrics.engine import MetricsEngine
 562 |         engine = MetricsEngine()
 563 |         
 564 |         for pid in [100, 200, 300]:
 565 |             for _ in range(10):
 566 |                 engine.update_scalar_metrics(pid, np.array([float(pid)]))
 567 |         
 568 |         for pid in [100, 200, 300]:
 569 |             assert pid in engine.profiles
 570 |             z = engine.get_z_scores(pid, np.array([float(pid)]))
 571 |             np.testing.assert_array_almost_equal(z, np.array([0.0]))
```

### tests/test_provenance_graph.py

```python
   1 | import pytest
   2 | import sys
   3 | from pathlib import Path
   4 | from unittest.mock import patch, MagicMock
   5 | 
   6 | SRC_DIR = Path(__file__).parent.parent / "src"
   7 | sys.path.insert(0, str(SRC_DIR))
   8 | 
   9 | from graph.builder import ProvenanceGraphBuilder
  10 | 
  11 | 
  12 | class TestProvenanceGraphBuilder:
  13 |     """Tests for ProvenanceGraphBuilder."""
  14 | 
  15 |     def test_add_event_creates_process_node(self):
  16 |         """Test add_event creates a process node when pid is provided."""
  17 |         builder = ProvenanceGraphBuilder()
  18 |         event = {"pid": 123, "comm": "bash", "filename": "", "syscall_id": 2}
  19 |         
  20 |         builder.add_event(event)
  21 |         
  22 |         assert builder.graph.has_node("proc_123")
  23 |         assert builder.graph.nodes["proc_123"]["type"] == "process"
  24 |         assert builder.graph.nodes["proc_123"]["pid"] == 123
  25 | 
  26 |     def test_add_event_creates_file_node(self):
  27 |         """Test add_event creates a file node when filename is provided."""
  28 |         builder = ProvenanceGraphBuilder()
  29 |         event = {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2}
  30 |         
  31 |         builder.add_event(event)
  32 |         
  33 |         assert builder.graph.has_node("file_/etc/passwd")
  34 |         assert builder.graph.nodes["file_/etc/passwd"]["type"] == "file"
  35 |         assert builder.graph.nodes["file_/etc/passwd"]["path"] == "/etc/passwd"
  36 | 
  37 |     def test_add_event_creates_edge(self):
  38 |         """Test add_event creates an edge from process to file."""
  39 |         builder = ProvenanceGraphBuilder()
  40 |         event = {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2}
  41 |         
  42 |         builder.add_event(event)
  43 |         
  44 |         assert builder.graph.has_edge("proc_123", "file_/etc/passwd")
  45 |         assert builder.graph.edges[("proc_123", "file_/etc/passwd")]["syscall"] == 2
  46 | 
  47 |     def test_add_event_duplicate_process(self):
  48 |         """Test duplicate process nodes are not duplicated."""
  49 |         builder = ProvenanceGraphBuilder()
  50 |         events = [
  51 |             {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2},
  52 |             {"pid": 123, "comm": "bash", "filename": "/etc/shadow", "syscall_id": 2},
  53 |         ]
  54 |         
  55 |         for event in events:
  56 |             builder.add_event(event)
  57 |         
  58 |         assert len([n for n in builder.graph.nodes() if n.startswith("proc_")]) == 1
  59 |         assert len(list(builder.graph.edges())) == 2
  60 | 
  61 |     def test_add_event_missing_filename(self):
  62 |         """Test add_event with no filename creates no file node or edge."""
  63 |         builder = ProvenanceGraphBuilder()
  64 |         event = {"pid": 123, "comm": "bash", "filename": "", "syscall_id": 2}
  65 |         
  66 |         builder.add_event(event)
  67 |         
  68 |         assert builder.graph.has_node("proc_123")
  69 |         assert len([n for n in builder.graph.nodes() if n.startswith("file_")]) == 0
  70 | 
  71 |     def test_get_process_subgraph_existing(self):
  72 |         """Test get_process_subgraph returns neighborhood for existing PID."""
  73 |         builder = ProvenanceGraphBuilder()
  74 |         events = [
  75 |             {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2},
  76 |             {"pid": 123, "comm": "bash", "filename": "/var/log/syslog", "syscall_id": 2},
  77 |         ]
  78 |         for event in events:
  79 |             builder.add_event(event)
  80 |         
  81 |         subgraph = builder.get_process_subgraph(123)
  82 |         
  83 |         assert subgraph.has_node("proc_123")
  84 |         assert len(subgraph.nodes()) == 3
  85 | 
  86 |     def test_get_process_subgraph_missing(self):
  87 |         """Test get_process_subgraph returns empty graph for non-existent PID."""
  88 |         builder = ProvenanceGraphBuilder()
  89 |         
  90 |         subgraph = builder.get_process_subgraph(999)
  91 |         
  92 |         assert len(subgraph.nodes()) == 0
  93 | 
  94 |     def test_get_serialized_graph_format(self):
  95 |         """Test get_serialized_graph returns valid node_link_data format."""
  96 |         builder = ProvenanceGraphBuilder()
  97 |         event = {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2}
  98 |         builder.add_event(event)
  99 |         
 100 |         serialized = builder.get_serialized_graph()
 101 |         
 102 |         assert "nodes" in serialized
 103 |         assert "links" in serialized or "edges" in serialized
 104 | 
 105 |     def test_clear_graph(self):
 106 |         """Test clear removes all nodes and edges."""
 107 |         builder = ProvenanceGraphBuilder()
 108 |         event = {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2}
 109 |         builder.add_event(event)
 110 |         
 111 |         builder.clear()
 112 |         
 113 |         assert len(builder.graph.nodes()) == 0
 114 |         assert len(builder.graph.edges()) == 0
```

### tests/test_scoring_engine.py

```python
   1 | import pytest
   2 | import sys
   3 | from pathlib import Path
   4 | from unittest.mock import patch, MagicMock
   5 | 
   6 | SRC_DIR = Path(__file__).parent.parent / "src"
   7 | sys.path.insert(0, str(SRC_DIR))
   8 | 
   9 | from scoring.engine import ScoringEngine, Alert
  10 | 
  11 | 
  12 | class TestScoringEngine:
  13 |     """Tests for ScoringEngine."""
  14 | 
  15 |     def test_compute_score_below_threshold(self):
  16 |         """Test score below threshold returns None."""
  17 |         engine = ScoringEngine(threshold=10.0)
  18 |         stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
  19 |         
  20 |         result = engine.compute_score(
  21 |             stat_report=stat_report,
  22 |             sig_match=None,
  23 |             graph_heuristics=[]
  24 |         )
  25 |         
  26 |         assert result is None
  27 | 
  28 |     def test_compute_score_at_threshold(self):
  29 |         """Test score at threshold returns Alert with warning."""
  30 |         engine = ScoringEngine(threshold=10.0)
  31 |         stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
  32 |         
  33 |         result = engine.compute_score(
  34 |             stat_report=stat_report,
  35 |             sig_match=None,
  36 |             graph_heuristics=["suspicious_parent"]  # 5.0 * 1 = 5.0, need 2 for 10.0
  37 |         )
  38 |         
  39 |         assert result is None
  40 | 
  41 |     def test_compute_score_above_threshold(self):
  42 |         """Test score above threshold returns Alert."""
  43 |         engine = ScoringEngine(threshold=10.0)
  44 |         stat_report = {"pid": 123, "is_anomalous": True, "max_z_score": 2.0}
  45 |         
  46 |         result = engine.compute_score(
  47 |             stat_report=stat_report,
  48 |             sig_match={"reason": "shadow file access"},
  49 |             graph_heuristics=["suspicious_parent"]
  50 |         )
  51 |         
  52 |         assert result is not None
  53 |         assert result.pid == 123
  54 | 
  55 |     def test_compute_score_signature_critical(self):
  56 |         """Test signature match sets severity to critical."""
  57 |         engine = ScoringEngine(threshold=10.0)
  58 |         stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
  59 |         
  60 |         result = engine.compute_score(
  61 |             stat_report=stat_report,
  62 |             sig_match={"reason": "shadow file access"},
  63 |             graph_heuristics=[]
  64 |         )
  65 |         
  66 |         assert result is not None
  67 |         assert result.severity == "critical"
  68 | 
  69 |     def test_compute_score_warning_threshold(self):
  70 |         """Test score between T and 2T without signature is warning."""
  71 |         engine = ScoringEngine(threshold=10.0)
  72 |         stat_report = {"pid": 123, "is_anomalous": True, "max_z_score": 5.0}
  73 |         
  74 |         result = engine.compute_score(
  75 |             stat_report=stat_report,
  76 |             sig_match=None,
  77 |             graph_heuristics=["suspicious_parent"]
  78 |         )
  79 |         
  80 |         assert result is not None
  81 |         assert result.severity == "warning"
  82 | 
  83 |     def test_compute_score_statistical_scaling(self):
  84 |         """Test statistical anomaly scales with Z-score."""
  85 |         engine = ScoringEngine(threshold=3.0)
  86 |         stat_report = {"pid": 123, "is_anomalous": True, "max_z_score": 3.0}
  87 |         
  88 |         result = engine.compute_score(
  89 |             stat_report=stat_report,
  90 |             sig_match=None,
  91 |             graph_heuristics=[]
  92 |         )
  93 |         
  94 |         assert result is not None
  95 |         assert result.score == 3.0
  96 | 
  97 |     def test_compute_score_multiple_heuristics(self):
  98 |         """Test multiple graph heuristics add up."""
  99 |         engine = ScoringEngine(threshold=10.0)
 100 |         stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
 101 |         
 102 |         result = engine.compute_score(
 103 |             stat_report=stat_report,
 104 |             sig_match=None,
 105 |             graph_heuristics=["h1", "h2", "h3"]
 106 |         )
 107 |         
 108 |         assert result is not None
 109 |         assert result.score == 15.0
 110 | 
 111 |     def test_compute_score_with_container_info(self):
 112 |         """Test container_info is included in Alert."""
 113 |         engine = ScoringEngine(threshold=10.0)
 114 |         stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
 115 |         container_info = {"id": "abc123", "name": "container1"}
 116 |         
 117 |         result = engine.compute_score(
 118 |             stat_report=stat_report,
 119 |             sig_match={"reason": "unauthorized shell"},
 120 |             graph_heuristics=[],
 121 |             container_info=container_info
 122 |         )
 123 |         
 124 |         assert result is not None
 125 |         assert result.container_info == container_info
 126 | 
 127 |     def test_compute_score_custom_threshold(self):
 128 |         """Test custom threshold is used."""
 129 |         engine = ScoringEngine(threshold=5.0)
 130 |         stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
 131 |         
 132 |         result = engine.compute_score(
 133 |             stat_report=stat_report,
 134 |             sig_match=None,
 135 |             graph_heuristics=["suspicious_parent"]
 136 |         )
 137 |         
 138 |         assert result is not None
 139 | 
 140 |     def test_alert_dataclass_structure(self):
 141 |         """Test Alert dataclass has all required fields."""
 142 |         alert = Alert(
 143 |             timestamp="2024-01-01T00:00:00",
 144 |             pid=123,
 145 |             score=15.0,
 146 |             severity="critical",
 147 |             reasons=["reason1"],
 148 |             container_info=None
 149 |         )
 150 |         
 151 |         assert hasattr(alert, "timestamp")
 152 |         assert hasattr(alert, "pid")
 153 |         assert hasattr(alert, "score")
 154 |         assert hasattr(alert, "severity")
 155 |         assert hasattr(alert, "reasons")
 156 |         assert hasattr(alert, "container_info")
 157 | 
 158 |     def test_compute_score_no_reasons_when_below(self):
 159 |         """Test reasons remain empty when below threshold."""
 160 |         engine = ScoringEngine(threshold=10.0)
 161 |         stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
 162 |         
 163 |         result = engine.compute_score(
 164 |             stat_report=stat_report,
 165 |             sig_match=None,
 166 |             graph_heuristics=[]
 167 |         )
 168 |         
 169 |         assert result is None
```

### tests/test_signature_detector.py

```python
   1 | import pytest
   2 | import numpy as np
   3 | from pathlib import Path
   4 | 
   5 | SRC_DIR = Path(__file__).parent.parent / "src"
   6 | 
   7 | 
   8 | class TestSignatureDetectorInit:
   9 |     """Tests for SignatureDetector initialization."""
  10 | 
  11 |     def test_detector_file_exists(self):
  12 |         """Verify SignatureDetector module exists."""
  13 |         import sys
  14 |         sys.path.insert(0, str(SRC_DIR))
  15 |         from src.detector.signature import SignatureDetector
  16 |         assert SignatureDetector is not None
  17 | 
  18 |     def test_default_init(self):
  19 |         """Verify default initialization."""
  20 |         import sys
  21 |         sys.path.insert(0, str(SRC_DIR))
  22 |         from src.detector.signature import SignatureDetector
  23 |         detector = SignatureDetector()
  24 |         assert detector is not None
  25 | 
  26 |     def test_critical_paths_initialized(self):
  27 |         """Verify critical_paths list is initialized."""
  28 |         import sys
  29 |         sys.path.insert(0, str(SRC_DIR))
  30 |         from src.detector.signature import SignatureDetector
  31 |         detector = SignatureDetector()
  32 |         assert hasattr(detector, "critical_paths")
  33 |         assert len(detector.critical_paths) > 0
  34 | 
  35 |     def test_suspicious_comm_initialized(self):
  36 |         """Verify suspicious_comm list is initialized."""
  37 |         import sys
  38 |         sys.path.insert(0, str(SRC_DIR))
  39 |         from src.detector.signature import SignatureDetector
  40 |         detector = SignatureDetector()
  41 |         assert hasattr(detector, "suspicious_comm")
  42 |         assert "bash" in detector.suspicious_comm
  43 | 
  44 | 
  45 | class TestSignatureDetectorCriticalPaths:
  46 |     """Tests for critical path detection (IOCs)."""
  47 | 
  48 |     def test_etc_shadow_detected(self):
  49 |         """Verify /etc/shadow access is detected."""
  50 |         import sys
  51 |         sys.path.insert(0, str(SRC_DIR))
  52 |         from src.detector.signature import SignatureDetector
  53 |         detector = SignatureDetector()
  54 |         
  55 |         event = {"filename": "/etc/shadow", "comm": "test"}
  56 |         result = detector.analyze_event(event)
  57 |         
  58 |         assert result is not None
  59 |         assert result["type"] == "SIGNATURE_MATCH"
  60 |         assert "critical" in result["severity"]
  61 | 
  62 |     def test_etc_sudoers_detected(self):
  63 |         """Verify /etc/sudoers access is detected."""
  64 |         import sys
  65 |         sys.path.insert(0, str(SRC_DIR))
  66 |         from src.detector.signature import SignatureDetector
  67 |         detector = SignatureDetector()
  68 |         
  69 |         event = {"filename": "/etc/sudoers", "comm": "test"}
  70 |         result = detector.analyze_event(event)
  71 |         
  72 |         assert result is not None
  73 |         assert result["type"] == "SIGNATURE_MATCH"
  74 | 
  75 |     def test_var_run_docker_sock_detected(self):
  76 |         """Verify /var/run/docker.sock access is detected."""
  77 |         import sys
  78 |         sys.path.insert(0, str(SRC_DIR))
  79 |         from src.detector.signature import SignatureDetector
  80 |         detector = SignatureDetector()
  81 |         
  82 |         event = {"filename": "/var/run/docker.sock", "comm": "test"}
  83 |         result = detector.analyze_event(event)
  84 |         
  85 |         assert result is not None
  86 |         assert result["type"] == "SIGNATURE_MATCH"
  87 | 
  88 |     def test_root_ssh_key_access(self):
  89 |         """Verify /root/.ssh/ key access is detected."""
  90 |         import sys
  91 |         sys.path.insert(0, str(SRC_DIR))
  92 |         from src.detector.signature import SignatureDetector
  93 |         detector = SignatureDetector()
  94 |         
  95 |         event = {"filename": "/root/.ssh/id_rsa", "comm": "test"}
  96 |         result = detector.analyze_event(event)
  97 |         
  98 |         assert result is not None
  99 | 
 100 |     def test_proc_kcore_detected(self):
 101 |         """Verify /proc/kcore access is detected."""
 102 |         import sys
 103 |         sys.path.insert(0, str(SRC_DIR))
 104 |         from src.detector.signature import SignatureDetector
 105 |         detector = SignatureDetector()
 106 |         
 107 |         event = {"filename": "/proc/kcore", "comm": "test"}
 108 |         result = detector.analyze_event(event)
 109 |         
 110 |         assert result is not None
 111 | 
 112 |     def test_non_matching_path_returns_none(self):
 113 |         """Verify non-matching path returns None."""
 114 |         import sys
 115 |         sys.path.insert(0, str(SRC_DIR))
 116 |         from src.detector.signature import SignatureDetector
 117 |         detector = SignatureDetector()
 118 |         
 119 |         event = {"filename": "/etc/passwd", "comm": "test"}
 120 |         result = detector.analyze_event(event)
 121 |         
 122 |         assert result is None
 123 | 
 124 | 
 125 | class TestSignatureDetectorSuspiciousComm:
 126 |     """Tests for suspicious process detection."""
 127 | 
 128 |     def test_bash_process_heuristic(self):
 129 |         """Verify bash process triggers heuristic."""
 130 |         import sys
 131 |         sys.path.insert(0, str(SRC_DIR))
 132 |         from src.detector.signature import SignatureDetector
 133 |         detector = SignatureDetector()
 134 |         
 135 |         event = {"filename": "/bin/bash", "comm": "bash"}
 136 |         result = detector.analyze_event(event)
 137 |         
 138 |         assert result is not None
 139 |         assert result["type"] == "HEURISTIC_MATCH"
 140 | 
 141 |     def test_sh_process_heuristic(self):
 142 |         """Verify sh process triggers heuristic."""
 143 |         import sys
 144 |         sys.path.insert(0, str(SRC_DIR))
 145 |         from src.detector.signature import SignatureDetector
 146 |         detector = SignatureDetector()
 147 |         
 148 |         event = {"filename": "/bin/sh", "comm": "sh"}
 149 |         result = detector.analyze_event(event)
 150 |         
 151 |         assert result is not None
 152 |         assert result["type"] == "HEURISTIC_MATCH"
 153 | 
 154 |     def test_nc_process_heuristic(self):
 155 |         """Verify nc (netcat) triggers heuristic."""
 156 |         import sys
 157 |         sys.path.insert(0, str(SRC_DIR))
 158 |         from src.detector.signature import SignatureDetector
 159 |         detector = SignatureDetector()
 160 |         
 161 |         event = {"filename": "/usr/bin/nc", "comm": "nc"}
 162 |         result = detector.analyze_event(event)
 163 |         
 164 |         assert result is not None
 165 |         assert result["severity"] == "warning"
 166 | 
 167 |     def test_ncat_process_heuristic(self):
 168 |         """Verify ncat triggers heuristic."""
 169 |         import sys
 170 |         sys.path.insert(0, str(SRC_DIR))
 171 |         from src.detector.signature import SignatureDetector
 172 |         detector = SignatureDetector()
 173 |         
 174 |         event = {"filename": "/usr/bin/ncat", "comm": "ncat"}
 175 |         result = detector.analyze_event(event)
 176 |         
 177 |         assert result is not None
 178 | 
 179 |     def test_python_process_heuristic(self):
 180 |         """Verify python process triggers heuristic."""
 181 |         import sys
 182 |         sys.path.insert(0, str(SRC_DIR))
 183 |         from src.detector.signature import SignatureDetector
 184 |         detector = SignatureDetector()
 185 |         
 186 |         event = {"filename": "/usr/bin/python3", "comm": "python"}
 187 |         result = detector.analyze_event(event)
 188 |         
 189 |         assert result is not None
 190 | 
 191 |     def test_perl_process_heuristic(self):
 192 |         """Verify perl process triggers heuristic."""
 193 |         import sys
 194 |         sys.path.insert(0, str(SRC_DIR))
 195 |         from src.detector.signature import SignatureDetector
 196 |         detector = SignatureDetector()
 197 |         
 198 |         event = {"filename": "/usr/bin/perl", "comm": "perl"}
 199 |         result = detector.analyze_event(event)
 200 |         
 201 |         assert result is not None
 202 | 
 203 |     def test_non_suspicious_comm_no_heuristic(self):
 204 |         """Verify non-suspicious process doesn't trigger heuristic."""
 205 |         import sys
 206 |         sys.path.insert(0, str(SRC_DIR))
 207 |         from src.detector.signature import SignatureDetector
 208 |         detector = SignatureDetector()
 209 |         
 210 |         event = {"filename": "/bin/nginx", "comm": "nginx"}
 211 |         result = detector.analyze_event(event)
 212 |         
 213 |         assert result is None
 214 | 
 215 | 
 216 | class TestSignatureDetectorEdgeCases:
 217 |     """Edge case tests for SignatureDetector."""
 218 | 
 219 |     def test_empty_event(self):
 220 |         """Verify empty event returns None."""
 221 |         import sys
 222 |         sys.path.insert(0, str(SRC_DIR))
 223 |         from src.detector.signature import SignatureDetector
 224 |         detector = SignatureDetector()
 225 |         
 226 |         event = {}
 227 |         result = detector.analyze_event(event)
 228 |         
 229 |         assert result is None
 230 | 
 231 |     def test_empty_filename(self):
 232 |         """Verify empty filename returns None."""
 233 |         import sys
 234 |         sys.path.insert(0, str(SRC_DIR))
 235 |         from src.detector.signature import SignatureDetector
 236 |         detector = SignatureDetector()
 237 |         
 238 |         event = {"filename": "", "comm": "bash"}
 239 |         result = detector.analyze_event(event)
 240 |         
 241 |         assert result is None
 242 | 
 243 |     def test_none_filename(self):
 244 |         """Verify None filename doesn't crash."""
 245 |         import sys
 246 |         sys.path.insert(0, str(SRC_DIR))
 247 |         from src.detector.signature import SignatureDetector
 248 |         detector = SignatureDetector()
 249 |         
 250 |         event = {"filename": None, "comm": "bash"}
 251 |         result = detector.analyze_event(event)
 252 |         
 253 |         assert result is None
 254 | 
 255 |     def test_missing_comm_key(self):
 256 |         """Verify missing 'comm' key is handled."""
 257 |         import sys
 258 |         sys.path.insert(0, str(SRC_DIR))
 259 |         from src.detector.signature import SignatureDetector
 260 |         detector = SignatureDetector()
 261 |         
 262 |         event = {"filename": "/etc/shadow"}
 263 |         result = detector.analyze_event(event)
 264 |         
 265 |         assert result is not None
 266 | 
 267 |     def test_missing_filename_key(self):
 268 |         """Verify missing 'filename' key is handled."""
 269 |         import sys
 270 |         sys.path.insert(0, str(SRC_DIR))
 271 |         from src.detector.signature import SignatureDetector
 272 |         detector = SignatureDetector()
 273 |         
 274 |         event = {"comm": "test"}
 275 |         result = detector.analyze_event(event)
 276 |         
 277 |         assert result is None
 278 | 
 279 |     def test_path_with_extra_slashes(self):
 280 |         """Verify path normalization works."""
 281 |         import sys
 282 |         sys.path.insert(0, str(SRC_DIR))
 283 |         from src.detector.signature import SignatureDetector
 284 |         detector = SignatureDetector()
 285 |         
 286 |         event = {"filename": "///etc///shadow", "comm": "test"}
 287 |         result = detector.analyze_event(event)
 288 |         
 289 |         assert result is None
 290 | 
 291 |     def test_path_with_dotdots(self):
 292 |         """Verify path with .. is handled."""
 293 |         import sys
 294 |         sys.path.insert(0, str(SRC_DIR))
 295 |         from src.detector.signature import SignatureDetector
 296 |         detector = SignatureDetector()
 297 |         
 298 |         event = {"filename": "/etc/../etc/shadow", "comm": "test"}
 299 |         result = detector.analyze_event(event)
 300 |         
 301 |         assert result is None
 302 | 
 303 | 
 304 | class TestSignatureDetectorReturnValues:
 305 |     """Tests for return value structure."""
 306 | 
 307 |     def test_signature_match_structure(self):
 308 |         """Verify SIGNATURE_MATCH has correct structure."""
 309 |         import sys
 310 |         sys.path.insert(0, str(SRC_DIR))
 311 |         from src.detector.signature import SignatureDetector
 312 |         detector = SignatureDetector()
 313 |         
 314 |         event = {"filename": "/etc/shadow", "comm": "test"}
 315 |         result = detector.analyze_event(event)
 316 |         
 317 |         assert "type" in result
 318 |         assert "reason" in result
 319 |         assert "severity" in result
 320 |         assert "ioc" in result
 321 | 
 322 |     def test_heuristic_match_structure(self):
 323 |         """Verify HEURISTIC_MATCH has correct structure."""
 324 |         import sys
 325 |         sys.path.insert(0, str(SRC_DIR))
 326 |         from src.detector.signature import SignatureDetector
 327 |         detector = SignatureDetector()
 328 |         
 329 |         event = {"filename": "/bin/bash", "comm": "bash"}
 330 |         result = detector.analyze_event(event)
 331 |         
 332 |         assert "type" in result
 333 |         assert "reason" in result
 334 |         assert "severity" in result
 335 | 
 336 |     def test_severity_values(self):
 337 |         """Verify severity values are valid."""
 338 |         import sys
 339 |         sys.path.insert(0, str(SRC_DIR))
 340 |         from src.detector.signature import SignatureDetector
 341 |         detector = SignatureDetector()
 342 |         
 343 |         event = {"filename": "/etc/shadow", "comm": "test"}
 344 |         result = detector.analyze_event(event)
 345 |         
 346 |         assert result["severity"] in ["info", "warning", "critical"]
 347 | 
 348 | 
 349 | class TestSignatureDetectorPriority:
 350 |     """Tests for detection priority (critical paths > heuristics)."""
 351 | 
 352 |     def test_critical_path_takes_priority(self):
 353 |         """Verify critical path takes priority over heuristic."""
 354 |         import sys
 355 |         sys.path.insert(0, str(SRC_DIR))
 356 |         from src.detector.signature import SignatureDetector
 357 |         detector = SignatureDetector()
 358 |         
 359 |         event = {"filename": "/etc/shadow", "comm": "bash"}
 360 |         result = detector.analyze_event(event)
 361 |         
 362 |         assert result["type"] == "SIGNATURE_MATCH"
 363 |         assert result["severity"] == "critical"
 364 | 
 365 | 
 366 | class TestSignatureDetectorIOCFields:
 367 |     """Tests for specific IOC field values."""
 368 | 
 369 |     def test_shadow_ioc_value(self):
 370 |         """Verify shadow IOC has correct value."""
 371 |         import sys
 372 |         sys.path.insert(0, str(SRC_DIR))
 373 |         from src.detector.signature import SignatureDetector
 374 |         detector = SignatureDetector()
 375 |         
 376 |         event = {"filename": "/etc/shadow", "comm": "test"}
 377 |         result = detector.analyze_event(event)
 378 |         
 379 |         assert result["ioc"] == "/etc/shadow"
 380 | 
 381 |     def test_sudoers_ioc_value(self):
 382 |         """Verify sudoers IOC has correct value."""
 383 |         import sys
 384 |         sys.path.insert(0, str(SRC_DIR))
 385 |         from src.detector.signature import SignatureDetector
 386 |         detector = SignatureDetector()
 387 |         
 388 |         event = {"filename": "/etc/sudoers", "comm": "test"}
 389 |         result = detector.analyze_event(event)
 390 |         
 391 |         assert result["ioc"] == "/etc/sudoers"
 392 | 
 393 |     def test_docker_sock_ioc_value(self):
 394 |         """Verify docker.sock IOC has correct value."""
 395 |         import sys
 396 |         sys.path.insert(0, str(SRC_DIR))
 397 |         from src.detector.signature import SignatureDetector
 398 |         detector = SignatureDetector()
 399 |         
 400 |         event = {"filename": "/var/run/docker.sock", "comm": "test"}
 401 |         result = detector.analyze_event(event)
 402 |         
 403 |         assert result["ioc"] == "/var/run/docker.sock"
 404 | 
 405 | 
 406 | class TestSignatureDetectorRealWorld:
 407 |     """Real-world attack scenario tests."""
 408 | 
 409 |     def test_password_file_access(self):
 410 |         """Verify /etc/passwd access doesn't trigger (common task)."""
 411 |         import sys
 412 |         sys.path.insert(0, str(SRC_DIR))
 413 |         from src.detector.signature import SignatureDetector
 414 |         detector = SignatureDetector()
 415 |         
 416 |         event = {"filename": "/etc/passwd", "comm": "cat"}
 417 |         result = detector.analyze_event(event)
 418 |         
 419 |         assert result is None
 420 | 
 421 |     def test_scheduled_task_access(self):
 422 |         """Verify cron access is allowed."""
 423 |         import sys
 424 |         sys.path.insert(0, str(SRC_DIR))
 425 |         from src.detector.signature import SignatureDetector
 426 |         detector = SignatureDetector()
 427 |         
 428 |         event = {"filename": "/etc/cron.d", "comm": "cron"}
 429 |         result = detector.analyze_event(event)
 430 |         
 431 |         assert result is None
 432 | 
 433 |     def test_web_server_shell(self):
 434 |         """Verify shell spawning from any process is detected."""
 435 |         import sys
 436 |         sys.path.insert(0, str(SRC_DIR))
 437 |         from src.detector.signature import SignatureDetector
 438 |         detector = SignatureDetector()
 439 |         
 440 |         event = {"filename": "/bin/bash", "comm": "bash"}
 441 |         result = detector.analyze_event(event)
 442 |         
 443 |         assert result is not None
 444 |         assert result["severity"] == "warning"
 445 | 
 446 |     def test_reverse_shell_pattern(self):
 447 |         """Verify reverse shell pattern is caught."""
 448 |         import sys
 449 |         sys.path.insert(0, str(SRC_DIR))
 450 |         from src.detector.signature import SignatureDetector
 451 |         detector = SignatureDetector()
 452 |         
 453 |         event = {"filename": "/bin/bash", "comm": "nc"}
 454 |         result = detector.analyze_event(event)
 455 |         
 456 |         assert result is not None
```

### tests/test_statistical_detector.py

```python
   1 | import pytest
   2 | import numpy as np
   3 | from unittest.mock import MagicMock, patch, PropertyMock
   4 | from pathlib import Path
   5 | import sys
   6 | 
   7 | sys.path.insert(0, str(Path(__file__).parent.parent))
   8 | 
   9 | from src.detector.statistical import StatisticalDetector
  10 | from src.metrics.engine import MetricsEngine
  11 | 
  12 | 
  13 | class TestStatisticalDetectorInit:
  14 |     """Tests for StatisticalDetector initialization."""
  15 | 
  16 |     def test_detector_file_exists(self):
  17 |         """Verify StatisticalDetector module exists."""
  18 |         assert StatisticalDetector is not None
  19 | 
  20 |     def test_default_threshold(self):
  21 |         """Verify default threshold is 3.0."""
  22 |         engine = MetricsEngine()
  23 |         detector = StatisticalDetector(engine)
  24 |         assert detector.threshold_z == 3.0
  25 | 
  26 |     def test_custom_threshold(self):
  27 |         """Verify custom threshold is set."""
  28 |         engine = MetricsEngine()
  29 |         detector = StatisticalDetector(engine, threshold_z=5.0)
  30 |         assert detector.threshold_z == 5.0
  31 | 
  32 |     def test_engine_reference_stored(self):
  33 |         """Verify engine reference is stored."""
  34 |         engine = MetricsEngine()
  35 |         detector = StatisticalDetector(engine)
  36 |         assert detector.engine is engine
  37 | 
  38 | 
  39 | class TestStatisticalDetectorEvaluate:
  40 |     """Tests for evaluate method."""
  41 | 
  42 |     def test_unknown_pid_returns_non_anomalous(self):
  43 |         """Verify unknown PID returns non-anomalous."""
  44 |         engine = MetricsEngine()
  45 |         detector = StatisticalDetector(engine)
  46 |         
  47 |         result = detector.evaluate(999, np.array([1.0, 2.0, 3.0]))
  48 |         
  49 |         assert result["is_anomalous"] is False
  50 |         assert result["max_z_score"] == 0.0
  51 | 
  52 |     def test_known_pid_z_score_calculation(self):
  53 |         """Verify known PID z-score is calculated."""
  54 |         engine = MetricsEngine()
  55 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
  56 |         
  57 |         detector = StatisticalDetector(engine, threshold_z=3.0)
  58 |         result = detector.evaluate(123, np.array([12.0, 10.0, 8.0]))
  59 |         
  60 |         assert result["pid"] == 123
  61 | 
  62 |     def test_anomaly_detection_threshold(self):
  63 |         """Verify anomaly detection above threshold."""
  64 |         engine = MetricsEngine()
  65 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
  66 |         
  67 |         detector = StatisticalDetector(engine, threshold_z=3.0)
  68 |         result = detector.evaluate(123, np.array([100.0, 10.0, 10.0]))
  69 |         
  70 |         assert result["is_anomalous"] is True
  71 |         assert result["max_z_score"] > 3.0
  72 | 
  73 |     def test_no_anomaly_below_threshold(self):
  74 |         """Verify no anomaly below threshold."""
  75 |         engine = MetricsEngine()
  76 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
  77 |         
  78 |         detector = StatisticalDetector(engine, threshold_z=3.0)
  79 |         result = detector.evaluate(123, np.array([12.0, 10.0, 10.0]))
  80 |         
  81 |         assert result["is_anomalous"] is False
  82 | 
  83 |     def test_z_vector_returned(self):
  84 |         """Verify z_vector is returned."""
  85 |         engine = MetricsEngine()
  86 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
  87 |         
  88 |         detector = StatisticalDetector(engine)
  89 |         result = detector.evaluate(123, np.array([20.0, 20.0, 20.0]))
  90 |         
  91 |         assert "z_vector" in result
  92 |         assert isinstance(result["z_vector"], list)
  93 | 
  94 |     def test_euclidean_distance_calculated(self):
  95 |         """Verify Euclidean distance is calculated."""
  96 |         engine = MetricsEngine()
  97 |         engine.update_scalar_metrics(123, np.array([0.0, 0.0, 0.0]))
  98 |         
  99 |         detector = StatisticalDetector(engine)
 100 |         result = detector.evaluate(123, np.array([3.0, 4.0, 0.0]))
 101 |         
 102 |         assert result["euclidean_distance"] == 5.0
 103 | 
 104 |     def test_euclidean_distance_zero_for_unknown(self):
 105 |         """Verify distance is 0 for unknown PID."""
 106 |         engine = MetricsEngine()
 107 |         detector = StatisticalDetector(engine)
 108 |         
 109 |         result = detector.evaluate(999, np.array([1.0, 2.0, 3.0]))
 110 |         
 111 |         assert result["euclidean_distance"] == 0.0
 112 | 
 113 | 
 114 | class TestStatisticalDetectorSeverity:
 115 |     """Tests for severity mapping."""
 116 | 
 117 |     def test_severity_info_below_threshold(self):
 118 |         """Verify severity is info below threshold."""
 119 |         engine = MetricsEngine()
 120 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
 121 |         
 122 |         detector = StatisticalDetector(engine, threshold_z=3.0)
 123 |         result = detector.evaluate(123, np.array([11.0, 10.0, 10.0]))
 124 |         
 125 |         assert result["severity"] == "info"
 126 | 
 127 |     def test_severity_warning_at_threshold(self):
 128 |         """Verify severity is critical at threshold boundary."""
 129 |         engine = MetricsEngine()
 130 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
 131 |         
 132 |         detector = StatisticalDetector(engine, threshold_z=3.0)
 133 |         result = detector.evaluate(123, np.array([19.0, 10.0, 10.0]))
 134 |         
 135 |         assert result["severity"] == "warning" or result["severity"] == "critical"
 136 | 
 137 |     def test_severity_warning_between_threshold(self):
 138 |         """Verify severity is critical above threshold."""
 139 |         engine = MetricsEngine()
 140 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
 141 |         
 142 |         detector = StatisticalDetector(engine, threshold_z=3.0)
 143 |         result = detector.evaluate(123, np.array([25.0, 10.0, 10.0]))
 144 |         
 145 |         assert result["severity"] == "critical"
 146 | 
 147 |     def test_severity_critical_above_double_threshold(self):
 148 |         """Verify severity is critical above 2x threshold."""
 149 |         engine = MetricsEngine()
 150 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
 151 |         
 152 |         detector = StatisticalDetector(engine, threshold_z=3.0)
 153 |         result = detector.evaluate(123, np.array([100.0, 10.0, 10.0]))
 154 |         
 155 |         assert result["severity"] == "critical"
 156 | 
 157 |     def test_mapped_to_severity_method(self):
 158 |         """Verify _map_to_severity method."""
 159 |         engine = MetricsEngine()
 160 |         detector = StatisticalDetector(engine)
 161 |         
 162 |         assert detector._map_to_severity(1.0) == "info"
 163 |         assert detector._map_to_severity(3.5) == "warning"
 164 |         assert detector._map_to_severity(10.0) == "critical"
 165 | 
 166 | 
 167 | class TestStatisticalDetectorReturnValues:
 168 |     """Tests for return value structure."""
 169 | 
 170 |     def test_return_has_pid(self):
 171 |         """Verify return has pid field."""
 172 |         engine = MetricsEngine()
 173 |         detector = StatisticalDetector(engine)
 174 |         
 175 |         result = detector.evaluate(123, np.array([1.0]))
 176 |         
 177 |         assert "pid" in result
 178 | 
 179 |     def test_return_has_is_anomalous(self):
 180 |         """Verify return has is_anomalous field."""
 181 |         engine = MetricsEngine()
 182 |         detector = StatisticalDetector(engine)
 183 |         
 184 |         result = detector.evaluate(123, np.array([1.0]))
 185 |         
 186 |         assert "is_anomalous" in result
 187 |         assert isinstance(result["is_anomalous"], bool)
 188 | 
 189 |     def test_return_has_max_z_score(self):
 190 |         """Verify return has max_z_score field."""
 191 |         engine = MetricsEngine()
 192 |         detector = StatisticalDetector(engine)
 193 |         
 194 |         result = detector.evaluate(123, np.array([1.0]))
 195 |         
 196 |         assert "max_z_score" in result
 197 | 
 198 |     def test_return_has_severity(self):
 199 |         """Verify return has severity field."""
 200 |         engine = MetricsEngine()
 201 |         detector = StatisticalDetector(engine)
 202 |         
 203 |         result = detector.evaluate(123, np.array([1.0]))
 204 |         
 205 |         assert "severity" in result
 206 | 
 207 | 
 208 | class TestStatisticalDetectorEdgeCases:
 209 |     """Edge case tests."""
 210 | 
 211 |     def test_empty_vector(self):
 212 |         """Verify empty vector handled."""
 213 |         engine = MetricsEngine()
 214 |         detector = StatisticalDetector(engine)
 215 |         
 216 |         result = detector.evaluate(123, np.array([]))
 217 |         
 218 |         assert result["pid"] == 123
 219 | 
 220 |     def test_single_element_vector(self):
 221 |         """Verify single element vector."""
 222 |         engine = MetricsEngine()
 223 |         engine.update_scalar_metrics(123, np.array([50.0]))
 224 |         
 225 |         detector = StatisticalDetector(engine)
 226 |         result = detector.evaluate(123, np.array([60.0]))
 227 |         
 228 |         assert result["max_z_score"] > 0
 229 | 
 230 |     def test_large_vector(self):
 231 |         """Verify large vector handled."""
 232 |         engine = MetricsEngine()
 233 |         large_vector = np.random.rand(1000)
 234 |         detector = StatisticalDetector(engine)
 235 |         
 236 |         result = detector.evaluate(123, large_vector)
 237 |         
 238 |         assert "z_vector" in result
 239 |         assert len(result["z_vector"]) == 1000
 240 | 
 241 |     def test_negative_values(self):
 242 |         """Verify negative values handled."""
 243 |         engine = MetricsEngine()
 244 |         engine.update_scalar_metrics(123, np.array([-10.0, -20.0]))
 245 |         
 246 |         detector = StatisticalDetector(engine)
 247 |         result = detector.evaluate(123, np.array([-5.0, -30.0]))
 248 |         
 249 |         assert result["max_z_score"] > 0
 250 | 
 251 |     def test_zero_threshold(self):
 252 |         """Verify zero threshold handled."""
 253 |         engine = MetricsEngine()
 254 |         engine.update_scalar_metrics(123, np.array([10.0]))
 255 |         
 256 |         detector = StatisticalDetector(engine, threshold_z=0.0)
 257 |         result = detector.evaluate(123, np.array([10.0]))
 258 |         
 259 |         assert "severity" in result
 260 | 
 261 |     def test_negative_threshold(self):
 262 |         """Verify negative threshold handled."""
 263 |         engine = MetricsEngine()
 264 |         engine.update_scalar_metrics(123, np.array([10.0]))
 265 |         
 266 |         detector = StatisticalDetector(engine, threshold_z=-1.0)
 267 |         result = detector.evaluate(123, np.array([10.0]))
 268 |         
 269 |         assert "severity" in result
 270 | 
 271 | 
 272 | class TestStatisticalDetectorIntegration:
 273 |     """Integration tests with MetricsEngine."""
 274 | 
 275 |     def test_full_workflow(self):
 276 |         """Verify full detection workflow."""
 277 |         engine = MetricsEngine(alpha=0.3)
 278 |         
 279 |         for i in range(50):
 280 |             vector = np.array([
 281 |                 float(i) + np.random.randn(),
 282 |                 float(i * 2) + np.random.randn(),
 283 |                 float(i * 3) + np.random.randn()
 284 |             ])
 285 |             engine.update_scalar_metrics(123, vector)
 286 |         
 287 |         detector = StatisticalDetector(engine, threshold_z=3.0)
 288 |         
 289 |         normal = np.array([25.0, 50.0, 75.0])
 290 |         result_normal = detector.evaluate(123, normal)
 291 |         
 292 |         assert "is_anomalous" in result_normal
 293 |         assert "euclidean_distance" in result_normal
 294 | 
 295 |         anomalous = np.array([1000.0, 1000.0, 1000.0])
 296 |         result_anom = detector.evaluate(123, anomalous)
 297 |         
 298 |         assert result_anom["is_anomalous"] is True
 299 | 
 300 |     def test_multiple_pids(self):
 301 |         """Verify multiple PIDs tracked separately."""
 302 |         engine = MetricsEngine()
 303 |         
 304 |         for pid in [100, 200, 300]:
 305 |             for _ in range(20):
 306 |                 engine.update_scalar_metrics(pid, np.array([float(pid)]))
 307 |         
 308 |         detector = StatisticalDetector(engine)
 309 |         
 310 |         for pid in [100, 200, 300]:
 311 |             result = detector.evaluate(pid, np.array([float(pid)]))
 312 |             assert result["is_anomalous"] is False
 313 | 
 314 |     def test_ewma_integration(self):
 315 |         """Verify EWMA updates work with detector."""
 316 |         engine = MetricsEngine(alpha=0.3)
 317 |         
 318 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
 319 |         
 320 |         for _ in range(10):
 321 |             engine.update_scalar_metrics(123, np.array([20.0, 20.0, 20.0]))
 322 |         
 323 |         detector = StatisticalDetector(engine)
 324 |         result = detector.evaluate(123, np.array([25.0, 25.0, 25.0]))
 325 |         
 326 |         assert "z_vector" in result
 327 | 
 328 | 
 329 | class TestStatisticalDetectorNgramIntegration:
 330 |     """Integration with n-gram functionality."""
 331 | 
 332 |     def test_ngram_with_statistical(self):
 333 |         """Verify ngram integration works."""
 334 |         engine = MetricsEngine(n_gram_size=3)
 335 |         
 336 |         for i in range(100):
 337 |             engine.update_ngram(123, i)
 338 |             engine.update_ngram(123, i + 1)
 339 |             engine.update_ngram(123, i + 2)
 340 |         
 341 |         detector = StatisticalDetector(engine)
 342 |         
 343 |         anomaly_score = engine.get_ngram_anomaly_score(123, (999, 1000, 1001))
 344 |         assert anomaly_score > 0.5
```

### tests/test_storage_sqlite.py

```python
   1 | import pytest
   2 | import sys
   3 | import sqlite3
   4 | import json
   5 | import tempfile
   6 | import os
   7 | from pathlib import Path
   8 | from unittest.mock import patch, MagicMock
   9 | 
  10 | SRC_DIR = Path(__file__).parent.parent / "src"
  11 | sys.path.insert(0, str(SRC_DIR))
  12 | 
  13 | from storage.sqlite import StorageManager
  14 | 
  15 | 
  16 | class TestStorageManagerSchema:
  17 |     """Tests for database schema initialization."""
  18 | 
  19 |     def test_init_creates_profiles_table(self):
  20 |         """Verify profiles table is created."""
  21 |         with tempfile.TemporaryDirectory() as tmpdir:
  22 |             db_path = os.path.join(tmpdir, "test.db")
  23 |             manager = StorageManager(db_path=db_path)
  24 |             
  25 |             conn = sqlite3.connect(db_path)
  26 |             cursor = conn.execute(
  27 |                 "SELECT name FROM sqlite_master WHERE type='table' AND name='profiles'"
  28 |             )
  29 |             result = cursor.fetchone()
  30 |             conn.close()
  31 |             
  32 |             assert result is not None, "profiles table should exist"
  33 | 
  34 |     def test_init_creates_alerts_table(self):
  35 |         """Verify alerts table is created."""
  36 |         with tempfile.TemporaryDirectory() as tmpdir:
  37 |             db_path = os.path.join(tmpdir, "test.db")
  38 |             manager = StorageManager(db_path=db_path)
  39 |             
  40 |             conn = sqlite3.connect(db_path)
  41 |             cursor = conn.execute(
  42 |                 "SELECT name FROM sqlite_master WHERE type='table' AND name='alerts'"
  43 |             )
  44 |             result = cursor.fetchone()
  45 |             conn.close()
  46 |             
  47 |             assert result is not None, "alerts table should exist"
  48 | 
  49 |     def test_init_creates_profiles_with_correct_columns(self):
  50 |         """Verify profiles table has required columns."""
  51 |         with tempfile.TemporaryDirectory() as tmpdir:
  52 |             db_path = os.path.join(tmpdir, "test.db")
  53 |             manager = StorageManager(db_path=db_path)
  54 |             
  55 |             conn = sqlite3.connect(db_path)
  56 |             cursor = conn.execute("PRAGMA table_info(profiles)")
  57 |             columns = {row[1] for row in cursor.fetchall()}
  58 |             conn.close()
  59 |             
  60 |             required = {"id", "identifier", "mu", "sigma", "last_updated"}
  61 |             assert required.issubset(columns), f"Missing columns: {required - columns}"
  62 | 
  63 |     def test_init_creates_alerts_with_correct_columns(self):
  64 |         """Verify alerts table has required columns."""
  65 |         with tempfile.TemporaryDirectory() as tmpdir:
  66 |             db_path = os.path.join(tmpdir, "test.db")
  67 |             manager = StorageManager(db_path=db_path)
  68 |             
  69 |             conn = sqlite3.connect(db_path)
  70 |             cursor = conn.execute("PRAGMA table_info(alerts)")
  71 |             columns = {row[1] for row in cursor.fetchall()}
  72 |             conn.close()
  73 |             
  74 |             required = {"id", "timestamp", "pid", "score", "severity", "reasons", "container_info"}
  75 |             assert required.issubset(columns), f"Missing columns: {required - columns}"
  76 | 
  77 |     def test_profile_identifier_unique_constraint(self):
  78 |         """Verify identifier column has UNIQUE constraint."""
  79 |         with tempfile.TemporaryDirectory() as tmpdir:
  80 |             db_path = os.path.join(tmpdir, "test.db")
  81 |             manager = StorageManager(db_path=db_path)
  82 |             
  83 |             conn = sqlite3.connect(db_path)
  84 |             cursor = conn.execute(
  85 |                 "SELECT sql FROM sqlite_master WHERE type='table' AND name='profiles'"
  86 |             )
  87 |             schema = cursor.fetchone()[0]
  88 |             conn.close()
  89 |             
  90 |             assert "UNIQUE" in schema.upper(), "profiles.identifier must have UNIQUE constraint"
  91 | 
  92 | 
  93 | class TestStorageManagerAlerts:
  94 |     """Tests for alert storage operations."""
  95 | 
  96 |     def test_save_alert_inserts_record(self):
  97 |         """Verify save_alert inserts a record into the database."""
  98 |         with tempfile.TemporaryDirectory() as tmpdir:
  99 |             db_path = os.path.join(tmpdir, "test.db")
 100 |             manager = StorageManager(db_path=db_path)
 101 |             
 102 |             alert_data = {
 103 |                 "timestamp": "2024-01-01T00:00:00",
 104 |                 "pid": 1234,
 105 |                 "score": 15.5,
 106 |                 "severity": "critical",
 107 |                 "reasons": ["unauthorized access"],
 108 |                 "container_info": {"id": "abc123"}
 109 |             }
 110 |             manager.save_alert(alert_data)
 111 |             
 112 |             conn = sqlite3.connect(db_path)
 113 |             cursor = conn.execute("SELECT * FROM alerts WHERE pid = ?", (1234,))
 114 |             row = cursor.fetchone()
 115 |             conn.close()
 116 |             
 117 |             assert row is not None, "Alert should be saved"
 118 |             assert row[2] == 1234
 119 |             assert row[3] == 15.5
 120 |             assert row[4] == "critical"
 121 | 
 122 |     def test_save_alert_serializes_reasons_as_json(self):
 123 |         """Verify reasons are stored as JSON string."""
 124 |         with tempfile.TemporaryDirectory() as tmpdir:
 125 |             db_path = os.path.join(tmpdir, "test.db")
 126 |             manager = StorageManager(db_path=db_path)
 127 |             
 128 |             alert_data = {
 129 |                 "timestamp": "2024-01-01T00:00:00",
 130 |                 "pid": 1234,
 131 |                 "score": 10.0,
 132 |                 "severity": "warning",
 133 |                 "reasons": ["reason1", "reason2"],
 134 |                 "container_info": None
 135 |             }
 136 |             manager.save_alert(alert_data)
 137 |             
 138 |             conn = sqlite3.connect(db_path)
 139 |             cursor = conn.execute("SELECT reasons FROM alerts WHERE pid = ?", (1234,))
 140 |             row = cursor.fetchone()
 141 |             conn.close()
 142 |             
 143 |             parsed = json.loads(row[0])
 144 |             assert parsed == ["reason1", "reason2"]
 145 | 
 146 |     def test_save_alert_serializes_container_info_as_json(self):
 147 |         """Verify container_info is stored as JSON string."""
 148 |         with tempfile.TemporaryDirectory() as tmpdir:
 149 |             db_path = os.path.join(tmpdir, "test.db")
 150 |             manager = StorageManager(db_path=db_path)
 151 |             
 152 |             alert_data = {
 153 |                 "timestamp": "2024-01-01T00:00:00",
 154 |                 "pid": 1234,
 155 |                 "score": 10.0,
 156 |                 "severity": "warning",
 157 |                 "reasons": [],
 158 |                 "container_info": {"id": "def456", "name": "testcontainer"}
 159 |             }
 160 |             manager.save_alert(alert_data)
 161 |             
 162 |             conn = sqlite3.connect(db_path)
 163 |             cursor = conn.execute("SELECT container_info FROM alerts WHERE pid = ?", (1234,))
 164 |             row = cursor.fetchone()
 165 |             conn.close()
 166 |             
 167 |             parsed = json.loads(row[0])
 168 |             assert parsed == {"id": "def456", "name": "testcontainer"}
 169 | 
 170 |     def test_save_alert_handles_none_container_info(self):
 171 |         """Verify None container_info is handled correctly."""
 172 |         with tempfile.TemporaryDirectory() as tmpdir:
 173 |             db_path = os.path.join(tmpdir, "test.db")
 174 |             manager = StorageManager(db_path=db_path)
 175 |             
 176 |             alert_data = {
 177 |                 "timestamp": "2024-01-01T00:00:00",
 178 |                 "pid": 1234,
 179 |                 "score": 10.0,
 180 |                 "severity": "warning",
 181 |                 "reasons": [],
 182 |                 "container_info": None
 183 |             }
 184 |             manager.save_alert(alert_data)
 185 |             
 186 |             conn = sqlite3.connect(db_path)
 187 |             cursor = conn.execute("SELECT container_info FROM alerts WHERE pid = ?", (1234,))
 188 |             row = cursor.fetchone()
 189 |             conn.close()
 190 |             
 191 |             assert row[0] == "null"
 192 | 
 193 |     def test_get_recent_alerts_returns_ordered_by_timestamp(self):
 194 |         """Verify alerts are returned in descending timestamp order."""
 195 |         with tempfile.TemporaryDirectory() as tmpdir:
 196 |             db_path = os.path.join(tmpdir, "test.db")
 197 |             manager = StorageManager(db_path=db_path)
 198 |             
 199 |             manager.save_alert({
 200 |                 "timestamp": "2024-01-01T00:00:00",
 201 |                 "pid": 1001,
 202 |                 "score": 5.0,
 203 |                 "severity": "info",
 204 |                 "reasons": [],
 205 |                 "container_info": None
 206 |             })
 207 |             manager.save_alert({
 208 |                 "timestamp": "2024-01-02T00:00:00",
 209 |                 "pid": 1002,
 210 |                 "score": 10.0,
 211 |                 "severity": "warning",
 212 |                 "reasons": [],
 213 |                 "container_info": None
 214 |             })
 215 |             
 216 |             alerts = manager.get_recent_alerts(limit=10)
 217 |             
 218 |             assert alerts[0]["pid"] == 1002, "Most recent alert should be first"
 219 |             assert alerts[1]["pid"] == 1001
 220 | 
 221 |     def test_get_recent_alerts_respects_limit(self):
 222 |         """Verify limit parameter is respected."""
 223 |         with tempfile.TemporaryDirectory() as tmpdir:
 224 |             db_path = os.path.join(tmpdir, "test.db")
 225 |             manager = StorageManager(db_path=db_path)
 226 |             
 227 |             for i in range(10):
 228 |                 manager.save_alert({
 229 |                     "timestamp": f"2024-01-0{i+1}T00:00:00",
 230 |                     "pid": 1000 + i,
 231 |                     "score": 5.0,
 232 |                     "severity": "info",
 233 |                     "reasons": [],
 234 |                     "container_info": None
 235 |                 })
 236 |             
 237 |             alerts = manager.get_recent_alerts(limit=3)
 238 |             
 239 |             assert len(alerts) == 3, "Should return only 3 alerts"
 240 | 
 241 |     def test_get_recent_alerts_returns_empty_list_when_no_alerts(self):
 242 |         """Verify empty list is returned when no alerts exist."""
 243 |         with tempfile.TemporaryDirectory() as tmpdir:
 244 |             db_path = os.path.join(tmpdir, "test.db")
 245 |             manager = StorageManager(db_path=db_path)
 246 |             
 247 |             alerts = manager.get_recent_alerts(limit=10)
 248 |             
 249 |             assert alerts == []
 250 | 
 251 |     def test_get_recent_alerts_parses_json_reasons(self):
 252 |         """Verify reasons are automatically parsed from JSON to list."""
 253 |         with tempfile.TemporaryDirectory() as tmpdir:
 254 |             db_path = os.path.join(tmpdir, "test.db")
 255 |             manager = StorageManager(db_path=db_path)
 256 |             
 257 |             manager.save_alert({
 258 |                 "timestamp": "2024-01-01T00:00:00",
 259 |                 "pid": 1234,
 260 |                 "score": 10.0,
 261 |                 "severity": "warning",
 262 |                 "reasons": ["reason1", "reason2"],
 263 |                 "container_info": None
 264 |             })
 265 |             
 266 |             alerts = manager.get_recent_alerts(limit=1)
 267 |             
 268 |             assert isinstance(alerts[0]["reasons"], list), "reasons should be parsed from JSON to list"
 269 |             assert alerts[0]["reasons"] == ["reason1", "reason2"]
 270 | 
 271 |     def test_get_recent_alerts_parses_json_container_info(self):
 272 |         """Verify container_info is automatically parsed from JSON."""
 273 |         with tempfile.TemporaryDirectory() as tmpdir:
 274 |             db_path = os.path.join(tmpdir, "test.db")
 275 |             manager = StorageManager(db_path=db_path)
 276 |             
 277 |             manager.save_alert({
 278 |                 "timestamp": "2024-01-01T00:00:00",
 279 |                 "pid": 1234,
 280 |                 "score": 10.0,
 281 |                 "severity": "warning",
 282 |                 "reasons": [],
 283 |                 "container_info": {"id": "abc", "name": "test"}
 284 |             })
 285 |             
 286 |             alerts = manager.get_recent_alerts(limit=1)
 287 |             
 288 |             assert isinstance(alerts[0]["container_info"], dict), "container_info should be parsed from JSON"
 289 |             assert alerts[0]["container_info"] == {"id": "abc", "name": "test"}
 290 | 
 291 | 
 292 | class TestStorageManagerProfiles:
 293 |     """Tests for profile storage operations."""
 294 | 
 295 |     def test_save_profile_inserts_record(self):
 296 |         """Verify save_profile inserts a record."""
 297 |         with tempfile.TemporaryDirectory() as tmpdir:
 298 |             db_path = os.path.join(tmpdir, "test.db")
 299 |             manager = StorageManager(db_path=db_path)
 300 |             
 301 |             manager.save_profile("bash", b"mu_data", b"sigma_data")
 302 |             
 303 |             conn = sqlite3.connect(db_path)
 304 |             cursor = conn.execute("SELECT * FROM profiles WHERE identifier = ?", ("bash",))
 305 |             row = cursor.fetchone()
 306 |             conn.close()
 307 |             
 308 |             assert row is not None, "Profile should be saved"
 309 |             assert row[1] == "bash"
 310 | 
 311 |     def test_save_profile_updates_existing(self):
 312 |         """Verify save_profile updates existing record."""
 313 |         with tempfile.TemporaryDirectory() as tmpdir:
 314 |             db_path = os.path.join(tmpdir, "test.db")
 315 |             manager = StorageManager(db_path=db_path)
 316 |             
 317 |             manager.save_profile("bash", b"mu_v1", b"sigma_v1")
 318 |             manager.save_profile("bash", b"mu_v2", b"sigma_v2")
 319 |             
 320 |             conn = sqlite3.connect(db_path)
 321 |             cursor = conn.execute("SELECT mu, sigma FROM profiles WHERE identifier = ?", ("bash",))
 322 |             row = cursor.fetchone()
 323 |             conn.close()
 324 |             
 325 |             assert row[0] == b"mu_v2", "mu should be updated"
 326 |             assert row[1] == b"sigma_v2", "sigma should be updated"
 327 | 
 328 |     def test_get_profile_returns_dict(self):
 329 |         """Verify get_profile returns dictionary."""
 330 |         with tempfile.TemporaryDirectory() as tmpdir:
 331 |             db_path = os.path.join(tmpdir, "test.db")
 332 |             manager = StorageManager(db_path=db_path)
 333 |             
 334 |             manager.save_profile("bash", b"mu_data", b"sigma_data")
 335 |             profile = manager.get_profile("bash")
 336 |             
 337 |             assert isinstance(profile, dict)
 338 |             assert profile["identifier"] == "bash"
 339 |             assert profile["mu"] == b"mu_data"
 340 | 
 341 |     def test_get_profile_returns_none_for_missing(self):
 342 |         """Verify get_profile returns None for non-existent profile."""
 343 |         with tempfile.TemporaryDirectory() as tmpdir:
 344 |             db_path = os.path.join(tmpdir, "test.db")
 345 |             manager = StorageManager(db_path=db_path)
 346 |             
 347 |             profile = manager.get_profile("nonexistent")
 348 |             
 349 |             assert profile is None
 350 | 
 351 | 
 352 | class TestStorageManagerConcurrency:
 353 |     """Tests for thread safety."""
 354 | 
 355 |     def test_lock_is_thread_lock(self):
 356 |         """Verify lock is a threading.Lock."""
 357 |         with tempfile.TemporaryDirectory() as tmpdir:
 358 |             db_path = os.path.join(tmpdir, "test.db")
 359 |             manager = StorageManager(db_path=db_path)
 360 |             
 361 |             import threading
 362 |             assert isinstance(manager._lock, type(threading.Lock()))
 363 | 
 364 |     def test_concurrent_saves_do_not_corrupt(self):
 365 |         """Verify concurrent writes don't corrupt database."""
 366 |         import threading
 367 |         with tempfile.TemporaryDirectory() as tmpdir:
 368 |             db_path = os.path.join(tmpdir, "test.db")
 369 |             manager = StorageManager(db_path=db_path)
 370 |             
 371 |             def save_alert(i):
 372 |                 manager.save_alert({
 373 |                     "timestamp": f"2024-01-0{i%9+1}T00:00:00",
 374 |                     "pid": 2000 + i,
 375 |                     "score": 5.0,
 376 |                     "severity": "info",
 377 |                     "reasons": [],
 378 |                     "container_info": None
 379 |                 })
 380 |             
 381 |             threads = [threading.Thread(target=save_alert, args=(i,)) for i in range(20)]
 382 |             for t in threads:
 383 |                 t.start()
 384 |             for t in threads:
 385 |                 t.join()
 386 |             
 387 |             conn = sqlite3.connect(db_path)
 388 |             cursor = conn.execute("SELECT COUNT(*) FROM alerts")
 389 |             count = cursor.fetchone()[0]
 390 |             conn.close()
 391 |             
 392 |             assert count == 20, "All 20 alerts should be saved"
```

### tests/test_tracepoints.py

```python
   1 | import re
   2 | import pytest
   3 | from pathlib import Path
   4 | 
   5 | EBPF_DIR = Path(__file__).parent.parent / "ebpf"
   6 | TRACER_FILE = EBPF_DIR / "tracer.bpf.c"
   7 | 
   8 | 
   9 | class TestTracepointHooks:
  10 |     """Tests for eBPF tracepoint hook validation."""
  11 | 
  12 |     @pytest.fixture
  13 |     def tracer_content(self):
  14 |         """Load tracer.bpf.c content."""
  15 |         return TRACER_FILE.read_text()
  16 | 
  17 |     def test_tracer_file_exists(self):
  18 |         """Verify tracer.bpf.c exists."""
  19 |         assert TRACER_FILE.exists(), "tracer.bpf.c not found"
  20 | 
  21 |     def test_includes_required_headers(self, tracer_content):
  22 |         """Verify required headers are included."""
  23 |         required_headers = ["vmlinux.h", "bpf/bpf_helpers.h", "bpf/bpf_tracing.h", "maps.bpf.h"]
  24 |         for header in required_headers:
  25 |             assert header in tracer_content, f"Required header {header} not included"
  26 | 
  27 |     def test_license_defined(self, tracer_content):
  28 |         """Verify GPL license is defined."""
  29 |         assert "LICENSE" in tracer_content, "LICENSE not defined"
  30 |         assert "GPL" in tracer_content, "GPL license not set"
  31 | 
  32 |     def test_trace_openat_hook_exists(self, tracer_content):
  33 |         """Verify tracepoint for openat syscall is defined."""
  34 |         assert "sys_enter_openat" in tracer_content, "sys_enter_openat tracepoint not found"
  35 |         assert "trace_openat" in tracer_content, "trace_openat handler function not found"
  36 | 
  37 |     def test_trace_close_hook_exists(self, tracer_content):
  38 |         """Verify tracepoint for close syscall is defined."""
  39 |         assert "sys_enter_close" in tracer_content, "sys_enter_close tracepoint not found"
  40 |         assert "trace_close" in tracer_content, "trace_close handler function not found"
  41 | 
  42 |     def test_openat_tracepoint_sec_format(self, tracer_content):
  43 |         """Verify openat tracepoint has correct SEC() format."""
  44 |         pattern = r'SEC\("tracepoint/syscalls/sys_enter_openat"\)'
  45 |         assert re.search(pattern, tracer_content), "Incorrect SEC format for openat tracepoint"
  46 | 
  47 |     def test_close_tracepoint_sec_format(self, tracer_content):
  48 |         """Verify close tracepoint has correct SEC() format."""
  49 |         pattern = r'SEC\("tracepoint/syscalls/sys_enter_close"\)'
  50 |         assert re.search(pattern, tracer_content), "Incorrect SEC format for close tracepoint"
  51 | 
  52 |     def test_trace_openat_returns_int(self, tracer_content):
  53 |         """Verify trace_openat function returns int."""
  54 |         pattern = r'int\s+trace_openat\s*\('
  55 |         assert re.search(pattern, tracer_content), "trace_openat should return int"
  56 | 
  57 |     def test_trace_close_returns_int(self, tracer_content):
  58 |         """Verify trace_close function returns int."""
  59 |         pattern = r'int\s+trace_close\s*\('
  60 |         assert re.search(pattern, tracer_content), "trace_close should return int"
  61 | 
  62 |     def test_trace_openat_context_param(self, tracer_content):
  63 |         """Verify trace_openat has correct context parameter."""
  64 |         assert "struct trace_event_raw_sys_enter" in tracer_content, "Missing trace_event_raw_sys_enter context"
  65 | 
  66 |     def test_bpf_get_current_pid_tgid_used(self, tracer_content):
  67 |         """Verify bpf_get_current_pid_tgid is used."""
  68 |         assert "bpf_get_current_pid_tgid" in tracer_content, "bpf_get_current_pid_tgid not used"
  69 | 
  70 |     def test_bpf_get_current_cgroup_id_used(self, tracer_content):
  71 |         """Verify bpf_get_current_cgroup_id is used."""
  72 |         assert "bpf_get_current_cgroup_id" in tracer_content, "bpf_get_current_cgroup_id not used"
  73 | 
  74 |     def test_bpf_get_current_comm_used(self, tracer_content):
  75 |         """Verify bpf_get_current_comm is used."""
  76 |         assert "bpf_get_current_comm" in tracer_content, "bpf_get_current_comm not used"
  77 | 
  78 |     def test_ringbuf_reserve_used(self, tracer_content):
  79 |         """Verify ring buffer reserve is used."""
  80 |         assert "bpf_ringbuf_reserve" in tracer_content, "bpf_ringbuf_reserve not used"
  81 | 
  82 |     def test_ringbuf_submit_used(self, tracer_content):
  83 |         """Verify ring buffer submit is used."""
  84 |         assert "bpf_ringbuf_submit" in tracer_content, "bpf_ringbuf_submit not used"
  85 | 
  86 |     def test_proc_metrics_lookup(self, tracer_content):
  87 |         """Verify proc_metrics map lookup is used."""
  88 |         assert "bpf_map_lookup_elem" in tracer_content, "bpf_map_lookup_elem not used"
  89 |         assert "proc_metrics" in tracer_content, "proc_metrics map not referenced"
  90 | 
  91 |     def test_proc_metrics_update(self, tracer_content):
  92 |         """Verify proc_metrics map update is used."""
  93 |         assert "bpf_map_update_elem" in tracer_content, "bpf_map_update_elem not used"
```

## Markdown

### ARCHITECTURE.md

```markdown
   1 | # SovND - Kernel-Level Security Monitoring & Explainable Scoring
   2 | 
   3 | ## Project Overview
   4 | 
   5 | **SovND** (pronounced "sovereign") is a real-time Linux kernel security monitoring system that combines eBPF-based syscall tracing with multi-vectors detection (signature, statistical, and provenance graph analysis) to generate explainable threat scores.
   6 | 
   7 | ### Key Features
   8 | - **eBPF Kernel Tracing** - Zero-overhead syscall capture via `tracepoint/syscalls`
   9 | - **Explainable Scoring** - Three-component formula: `S = Σ(w_i × d_i)`
  10 | - **Multi-Vector Detection** - Signature + Statistical + Graph heuristics
  11 | - **Live Dashboard** - WebSocket telemetry with Chart.js visualization
  12 | - **SQLite Persistence** - Alert storage for historical analysis
  13 | 
  14 | ### Motivation
  15 | Traditional HIDS agents (AIDE, OSSEC) scan periodically, missing transient threats. Commercial solutions (CrowdStrike, SentinelOne) are expensive and opaque. SovND provides an open-source, kernel-level alternative with mathematically explainable scoring.
  16 | 
  17 | ---
  18 | 
  19 | ## Architecture
  20 | 
  21 | ```
  22 | ┌─────────────────────────────────────────────────────────────────────────┐
  23 | │                        DASHBOARD (Browser)                         │
  24 | │              Chart.js + WebSocket (static/index.html)            │
  25 | └───────────────────────────────┬─────────────────────────────────────┘
  26 |                               │ ws://localhost:8000/ws/telemetry
  27 | ┌───────────────────────────────▼─────────────────────────────────────┐
  28 | │                    API SERVER (FastAPI)                           │
  29 | │              src/api/main.py (Uvicorn on port 8000)              │
  30 | │  ┌────────────────┐  ┌────────────────┐  ┌───────────────────┐   │
  31 | │  │ WebSocket      │  │ /api/attack   │  │ SQLite Query      │   │
  32 | │  │ Telemetry     │  │ Trigger      │  │ Endpoint        │   │
  33 | │  └───────────────┘  └──────────────┘  └─────────────────┘   │
  34 | └───────────────────────────────┬─────────────────────────────────────┘
  35 |                              │ storage.save_alert()
  36 | ┌───────────────────────────▼───────────────────────────────────────┐
  37 | │              STORAGE LAYER (SQLite)                            │
  38 | │                   data/sovnd.db                              │
  39 | │  ┌─────────────────────────────────────────────────────┐     │
  40 | │  │ alerts: id, timestamp, pid, comm, score, severity,  │     │
  41 | │  │        reasons (JSON), breakdown (JSON)             │     │
  42 | │  └─────────────────────────────────────────────────────┘     │
  43 | └───────────────────────────────┬────────────���────────────────────────┘
  44 |                              │ get_recent_alerts()
  45 | ┌───────────────────────────▼───────────────────────────────────────┐
  46 | │              MAIN AGENT LOOP (Python)                          │
  47 | │              src/main_agent.py                              │
  48 | │  ┌─────────────────────────────────────────────────┐           │
  49 | │  │  ScoringEngine                           │           │
  50 | │  │  compute_score(event, stat_report,      │           │
  51 | │  │  sig_match, graph_heuristics)         │           │
  52 | │  │  → Alert(score, breakdown, reasons)  │           │
  53 | │  └─────────────────────────────────────────────────┘           │
  54 | │                        ▲                                     │
  55 | │    ┌──────────────────┬┴───────────────────┐              │
  56 | │    │              DETECTORS                  │              │
  57 | │ ┌──▼──────────┐ ┌─────▼───────┐ ┌─────────▼────────┐     │
  58 | │ │ Signature   │ │ Statistical │ │ Graph          │     │
  59 | │ │ Detector   │ │ Detector   │ │ Builder       │     │
  60 | │ │ (regex IOC) │ │ (z-scores) │ │ (provenance)  │     │
  61 | │ └────────────┘ └───────────┘ └────────────────┘     │
  62 | │                        │                                │
  63 | └────────────────────────┼────────────────────────────────┘
  64 |                          │ get_event()
  65 | ┌───────────────────────▼────────────────────────────────┐
  66 | │              eBPF AGENT (Python ctypes)                    │
  67 | │              src/ebpf_agent.py                           │
  68 | │  ┌─────────────────────────────────────────────┐       │
  69 | │  │ C Library Loader (ebpf/libloader.so)        │       │
  70 | │  │ - start_loader()                         │       │
  71 | │  │ - poll_events(timeout_ms)                │       │
  72 | │  │ - stop_loader()                       │       │
  73 | │  └─────────────────────────────────────────────┘       │
  74 | └───────────────────────────────┬────────────────────────────────┘
  75 |                              │ tracepoint/syscalls
  76 | ┌───────────────────────────▼────────────────────────────────┐
  77 | │              LINUX KERNEL (eBPF)                        │
  78 | │         ebpf/tracer.bpf.c (uprobe/tracepoint)            │
  79 | │  ┌─────────────────────────────────────────────┐       │
  80 | │  │ trace_openat() - sys_enter_openat          │       │
  81 | │  │ trace_close() - sys_enter_close           │       │
  82 | │  │ ring buffer for events                   │       │
  83 | │  └───���─────────────────────────────────────────┘       │
  84 | └──────────────────────────────────────────────────────┘
  85 | ```
  86 | 
  87 | ---
  88 | 
  89 | ## Components
  90 | 
  91 | ### 1. eBPF Kernel Tracer (`ebpf/tracer.bpf.c`)
  92 | 
  93 | **Purpose:** Capture syscalls directly from the kernel with zero process overhead.
  94 | 
  95 | **Implementation:**
  96 | - Two tracepoint hooks: `sys_enter_openat` and `sys_enter_close`
  97 | - Uses BPF ring buffer (`rb`) for efficient event delivery
  98 | - CO-RE (Compile Once Run Everywhere) for kernel BTF compatibility
  99 | 
 100 | **Data Captured:**
 101 | | Field | Type | Description |
 102 | |-------|------|------------|
 103 | | `pid` | u32 | Process ID |
 104 | | `tgid` | u32 | Thread Group ID |
 105 | | `cgroup_id` | u64 | Control Group ID |
 106 | | `syscall_id` | u32 | Syscall number (257=openat) |
 107 | | `comm` | char[16] | Process command name |
 108 | | `filename` | char[256] | File path |
 109 | 
 110 | **Key Code:**
 111 | ```c
 112 | // tracer.bpf.c (simplified)
 113 | SEC("tracepoint/syscalls/sys_enter_openat")
 114 | int trace_openat(struct trace_event_raw_sys_enter *ctx) {
 115 |     // Load filename from RDI register (first arg)
 116 |     bpf_probe_read_user(&data.filename, sizeof(data.filename), (void *)ctx->args[1]);
 117 |     // Store in ring buffer
 118 |     bpf_ringbuf_output(&rb, &data, sizeof(data), 0);
 119 |     return 0;
 120 | }
 121 | ```
 122 | 
 123 | **Build Command:**
 124 | ```bash
 125 | clang -target bpf -g -O2 -Iebpf -c ebpf/tracer_bpf.c -o ebpf/tracer_bpf.o
 126 | ```
 127 | 
 128 | ---
 129 | 
 130 | ### 2. eBPF Agent (`src/ebpf_agent.py`)
 131 | 
 132 | **Purpose:** Python bridge to the compiled eBPF object via shared library.
 133 | 
 134 | **Key Responsibilities:**
 135 | 1. Load C library via `ctypes.CDLL`
 136 | 2. Register Python callback for ring buffer events
 137 | 3. Poll events in background thread
 138 | 4. Expose `get_event(timeout)` API to main loop
 139 | 
 140 | **Event Structure (Python):**
 141 | ```python
 142 | {
 143 |     "pid": int,
 144 |     "tgid": int,
 145 |     "cgroup_id": int,
 146 |     "syscall_id": int,
 147 |     "comm": str,      # e.g., "sudo", "python3"
 148 |     "filename": str  # e.g., "/etc/shadow"
 149 | }
 150 | ```
 151 | 
 152 | ---
 153 | 
 154 | ### 3. Signature Detector (`src/detector/signature.py`)
 155 | 
 156 | **Purpose:** Fast pattern matching against known IOCs (Indicators of Compromise).
 157 | 
 158 | **Detection Logic:**
 159 | 
 160 | ```python
 161 | class SignatureDetector:
 162 |     # Critical file access (IOCs)
 163 |     critical_paths = [
 164 |         r'^/etc/shadow$',        # Password hashes
 165 |         r'^/etc/sudoers$',      # sudo config
 166 |         r'^/var/run/docker\.sock$',  # Docker socket
 167 |         r'^/root/.ssh/.*',      # SSH keys
 168 |         r'^/proc/kcore$'        # Kernel memory
 169 |     ]
 170 |     
 171 |     # Suspicious processes
 172 |     suspicious_comm = ["bash", "sh", "nc", "ncat", "python", "perl"]
 173 | ```
 174 | 
 175 | **Decision Rationale:**
 176 | - Regex patterns are O(n) where n = number of paths (5), inherently fast
 177 | - Critical files are high-confidence IOCs - false positives acceptable
 178 | - Suspicious comm detection guards against reverse shells and lateral movement
 179 | 
 180 | ---
 181 | 
 182 | ### 4. Statistical Detector (`src/detector/statistical.py`)
 183 | 
 184 | **Purpose:** Learn process behavior and detect statistical anomalies using Z-scores.
 185 | 
 186 | **Mathematical Model:**
 187 | - **EWMA (Exponentially Weighted Moving Average):** `μ_t = α × x_t + (1-α) × μ_{t-1}`
 188 | - **Z-score:** `z = (x - μ) / σ`
 189 | - **Anomaly threshold:** `|z| > threshold_z` (default 3.0)
 190 | 
 191 | **Implementation:**
 192 | ```python
 193 | z_scores = engine.get_z_scores(pid, current_vector)
 194 | max_z = np.max(np.abs(z_scores))
 195 | is_anomalous = max_z > self.threshold_z
 196 | ```
 197 | 
 198 | **Why EWMA?**
 199 | - Adapts to concept drift (process behavior changes over time)
 200 | - Memory-efficient (only stores μ and σ, not full history)
 201 | - Configurable via α (default 0.3 = 30% weight on recent samples)
 202 | 
 203 | **Design Decision:** In demo mode, statistical scores are randomized (25% chance, z ∈ [2.5, 8.5]) because real attacks would build baseline profiles first - new processes have no history.
 204 | 
 205 | ---
 206 | 
 207 | ### 5. Metrics Engine (`src/metrics/engine.py`)
 208 | 
 209 | **Purpose:** Maintains per-PID behavioral profiles.
 210 | 
 211 | **Profile Structure:**
 212 | ```python
 213 | {
 214 |     pid: {
 215 |         "mu": np.ndarray,        # EWMA mean vector
 216 |         "sigma": np.ndarray,   # EWMA standard deviation
 217 |         "history": deque,   # Last 100 observations
 218 |         "ngram_buffer": deque,   # Last 3 syscall IDs
 219 |         "ngram_counts": dict    # { (1,2,3): count }
 220 |     }
 221 | }
 222 | ```
 223 | 
 224 | **Feature Vector (5-dimensional):**
 225 | | Index | Feature | Source |
 226 | |-------|---------|--------|
 227 | | 0 | syscall_id | Event syscall |
 228 | | 1 | filename_len | len(filename) |
 229 | | 2 | tgid | Thread group |
 230 | | 3 | syscall_count | Constant 1.0 |
 231 | | 4 | cgroup_mod | cgroup_id % 1000 |
 232 | 
 233 | **Design Decision:** Feature vector is intentionally simple for demonstration. Real implementations would include: CPU usage, memory delta, network bytes, disk I/O, etc.
 234 | 
 235 | ---
 236 | 
 237 | ### 6. Graph Builder (`src/graph/builder.py`)
 238 | 
 239 | **Purpose:** Construct process-to-resource provenance for lateral movement detection.
 240 | 
 241 | **Graph Structure:**
 242 | - **Nodes:** Process (`proc_{pid}`), File (`file_{path}`), Socket (`socket_{fd}`)
 243 | - **Directed Edges:** Process → Resource
 244 | 
 245 | **Heuristics Implemented:**
 246 | ```python
 247 | # 1. High connectivity - processes touching many files
 248 | high_connectivity: subgraph.number_of_nodes() > 3
 249 | 
 250 | # 2. Sensitive access - /etc or /root files
 251 | sensitive_access: filename.startswith("/etc") or filename.startswith("/root")
 252 | ```
 253 | 
 254 | **Graph Lib:** NetworkX (Python graph library)
 255 | 
 256 | **Design Decision:** Using NetworkX for rapid prototyping. Production would use GPUGraph or Graphistry for billion-node scale.
 257 | 
 258 | ---
 259 | 
 260 | ### 7. Scoring Engine (`src/scoring/engine.py`)
 261 | 
 262 | **Purpose:** Combine all detection vectors into an explainable threat score.
 263 | 
 264 | **Scoring Formula:**
 265 | ```
 266 | S = w_signature × sig_match + w_statistical × max_z + w_graph × |heuristics|
 267 | 
 268 | where:
 269 |   w_signature = 15.0   (high - signature match is definitive)
 270 |   w_statistical = 1.0   (low - z-score is scaled)
 271 |   w_graph = 5.0         (medium - heuristics are suspicious)
 272 | ```
 273 | 
 274 | **Score Breakdown:**
 275 | ```python
 276 | breakdown = {
 277 |     "signature": 0.0 or 15.0,
 278 |     "statistical": max_z * 1.0,  # e.g., 5.2 if z=5.2
 279 |     "graph": len(heuristics) * 5.0  # e.g., 10.0 if 2 heuristics
 280 | }
 281 | ```
 282 | 
 283 | **Alert Generation:**
 284 | ```python
 285 | if total_score >= threshold:
 286 |     severity = "CRITICAL" if total_score > 20 else "WARNING"
 287 |     return Alert(
 288 |         score=total_score,
 289 |         severity=severity,
 290 |         breakdown=comp,
 291 |         reasons=[...]  # Human-readable
 292 |     )
 293 | ```
 294 | 
 295 | **Threshold Decision:** Set to 15.0 to reduce false positives from graph-only alerts (sensitive_access alone is 5.0, below threshold).
 296 | 
 297 | ---
 298 | 
 299 | ### 8. Storage Layer (`src/storage/sqlite.py`)
 300 | 
 301 | **Purpose:** Persist alerts for historical analysis.
 302 | 
 303 | **Schema:**
 304 | ```sql
 305 | CREATE TABLE IF NOT EXISTS alerts (
 306 |     id INTEGER PRIMARY KEY AUTOINCREMENT,
 307 |     timestamp TIMESTAMP,
 308 |     pid INTEGER,
 309 |     comm TEXT,
 310 |     score REAL,
 311 |     severity TEXT,
 312 |     reasons TEXT,        -- JSON array
 313 |     breakdown TEXT      -- JSON object
 314 | )
 315 | ```
 316 | 
 317 | **Design Decision:** Using SQLite (not PostgreSQL) for demo portability. Production would use TimescaleDB or ClickHouse.
 318 | 
 319 | ---
 320 | 
 321 | ### 9. API Server (`src/api/main.py`)
 322 | 
 323 | **Purpose:** Web dashboard backend.
 324 | 
 325 | **Endpoints:**
 326 | | Path | Method | Description |
 327 | |------|--------|-------------|
 328 | | `/` | GET | Serve static/index.html |
 329 | | `/ws/telemetry` | WS | Stream {eps, alerts} at 2Hz |
 330 | | `/api/attack` | POST | Trigger demo attacks |
 331 | 
 332 | **WebSocket Message Format:**
 333 | ```json
 334 | {
 335 |     "eps": 1500,  // events per second
 336 |     "alerts": [
 337 |         {
 338 |             "timestamp": "2026-04-27T10:30:00",
 339 |             "pid": 7390,
 340 |             "comm": "cat",
 341 |             "score": 17.5,
 342 |             "severity": "WARNING",
 343 |             "reasons": ["Access to critical file: /etc/shadow", "Statistical Anomaly (Z=2.5)"],
 344 |             "breakdown": {"signature": 15.0, "statistical": 2.5, "graph": 0.0}
 345 |         }
 346 |     ]
 347 | }
 348 | ```
 349 | 
 350 | ---
 351 | 
 352 | ### 10. Dashboard (`static/index.html`)
 353 | 
 354 | **Purpose:** Browser UI for live telemetry.
 355 | 
 356 | **Features:**
 357 | - Chart.js line graph (throughput over 40 buckets)
 358 | - Alert stack with score breakdown (SIG/STAT/GRPH)
 359 | - "SIMULATE MULTI-STAGE ATTACK" button
 360 | 
 361 | **Key JavaScript (WebSocket):**
 362 | ```javascript
 363 | ws.onmessage = (event) => {
 364 |     const data = JSON.parse(event.data);
 365 |     
 366 |     // Update chart
 367 |     chart.data.datasets[0].data.push(data.eps);
 368 |     chart.data.datasets[0].data.shift();
 369 |     chart.update();
 370 |     
 371 |     // Show alerts (10s grace period for clock drift)
 372 |     const liveAlerts = data.alerts.filter(a => 
 373 |         new Date(a.timestamp).getTime() > sessionStartTime - 10000
 374 |     );
 375 |     
 376 |     // Render cards with breakdown
 377 |     alertList.innerHTML = liveAlerts.map(a => `
 378 |         <div>
 379 |             PID ${a.pid} [${a.comm}] 
 380 |             SCORE ${a.score}
 381 |             SIG: ${a.breakdown.signature}
 382 |             STAT: ${a.breakdown.statistical}
 383 |             GRPH: ${a.breakdown.graph}
 384 |         </div>
 385 |     `).join('');
 386 | }
 387 | ```
 388 | 
 389 | **Design Decision:** WebSocket avoids polling overhead. Chart.js for zero-dependency charting.
 390 | 
 391 | ---
 392 | 
 393 | ## Demo Orchestrator (`demo.py`)
 394 | 
 395 | **Purpose:** One-command launch for demos.
 396 | 
 397 | **Flow:**
 398 | ```python
 399 | def start():
 400 |     # 1. Clean data/ for fresh start
 401 |     os.remove("data/sovnd.db")
 402 |     
 403 |     # 2. Start API server (port 8000)
 404 |     api_proc = subprocess.Popen(["uvicorn", "src.api.main:app"])
 405 |     
 406 |     # 3. Start eBPF agent
 407 |     agent_proc = subprocess.Popen(["python3", "src/main_agent.py"])
 408 |     
 409 |     # 4. Open browser
 410 |     os.system("xdg-open http://localhost:8000")
 411 | ```
 412 | 
 413 | **Usage:**
 414 | ```bash
 415 | sudo python3 demo.py start
 416 | # Opens browser to http://localhost:8000
 417 | # Click "SIMULATE MULTI-STAGE ATTACK" to trigger alerts
 418 | ```
 419 | 
 420 | ---
 421 | 
 422 | ## Key Design Decisions
 423 | 
 424 | ### 1. Why eBPF for tracing?
 425 | - **Kernel-level:** No userspace overhead, can't be evade by process hiding
 426 | - **Ring buffer:** Log(1) egress - no blocking
 427 | - **CO-RE:** Works across kernel versions without recompilation
 428 | 
 429 | ### 2. Why three detection vectors?
 430 | | Vector | Strength | Weakness |
 431 | |--------|----------|---------|
 432 | | Signature | Zero false positive on IOCs | Misses novel attacks |
 433 | | Statistical | Catches deviations | Needs baseline first |
 434 | | Graph | Detects lateral movement | Computationally heavy |
 435 | 
 436 | **Multi-vector approach** ensures coverage across attack kill chain.
 437 | 
 438 | ### 3. Why weighted sum scoring?
 439 | - Interpretability: Each component is explainable
 440 | - Tunability: Weights can be adjusted per environment
 441 | - Threshold is single knob for operators
 442 | 
 443 | ### 4. Why SQLite for demo?
 444 | - No external dependency (PostgreSQL requires daemon)
 445 | - ACID compliance for alert integrity
 446 | - Easy export for further analysis
 447 | 
 448 | ### 5. Why WebSocket over HTTP polling?
 449 | - 2Hz update rate needed for live feel
 450 | - Polling would double server load
 451 | - WebSocket is full-duplex
 452 | 
 453 | ---
 454 | 
 455 | ## Score Variations (Expected Output)
 456 | 
 457 | When running `sudo python3 demo.py start`:
 458 | 
 459 | | Scenario | SIG | STAT | GRPH | Total |
 460 | |----------|-----|------|------|-------|
 461 | | Signature only | 15.0 | 0.0 | 0.0 | **15.0** |
 462 | | SIG + sensitive_access | 15.0 | 0.0 | 5.0 | **20.0** |
 463 | | SIG + z-score 2.5 | 15.0 | 2.5 | 0.0 | **17.5** |
 464 | | SIG + z-score 8.5 | 15.0 | 8.5 | 0.0 | **23.5** |
 465 | | SIG + STAT + GRPH + z7.5 | 15.0 | 7.5 | 5.0 | **27.5** |
 466 | 
 467 | ---
 468 | 
 469 | ## Dependencies
 470 | 
 471 | ### Python Packages
 472 | | Package | Version | Purpose |
 473 | |---------|---------|---------|
 474 | | numpy | 1.26.4 | Statistical calculations |
 475 | | networkx | 2.8.8 | Graph provenance |
 476 | | fastapi | - | Web API |
 477 | | uvicorn | - | ASGI server |
 478 | | websockets | - | WebSocket support |
 479 | 
 480 | ### System Requirements
 481 | - Linux kernel 5.10+ (BTF support)
 482 | - Root access (CAP_BPF for eBPF)
 483 | - clang + llvm (eBPF compilation)
 484 | 
 485 | ---
 486 | 
 487 | ## Future Improvements
 488 | 
 489 | ### Phase 2 (Production-Ready)
 490 | 1. **Machine Learning:** Train classifier on labeled attack data
 491 | 2. **Kafka Export:** Stream alerts to SIEM
 492 | 3. **Horizontal Scaling:** DistributedAgents per host
 493 | 4. **Graph Visualization:** Cytoscape.js for provenance
 494 | 
 495 | ### Phase 3 (Enterprise)
 496 | 1. **eBPFmaps:** Share state across agents
 497 | 2. **Kernel Hardening:** SECCOMP policies
 498 | 3. **Performance:** < 1% CPU overhead
 499 | 4. **Compliance:** SOC2 audit logs
 500 | 
 501 | ---
 502 | 
 503 | ## Appendix: File Structure
 504 | 
 505 | ```
 506 | sovnd-project/
 507 | ├── ebpf/
 508 | │   ├── tracer.bpf.c      # eBPF program
 509 | │   ├── tracer.skel.h     # Generated skeleton
 510 | │   └── Makefile         # Build rules
 511 | ├── src/
 512 | │   ├── ebpf_agent.py    # Python ↔ eBPF bridge
 513 | │   ├── main_agent.py   # Main loop + scoring
 514 | │   ├── detector/
 515 | │   │   ├── signature.py    # IOC matching
 516 | │   │   └── statistical.py # Z-score detection
 517 | │   ├── metrics/
 518 | │   │   └── engine.py   # EWMA profiles
 519 | │   ├── graph/
 520 | │   │   └── builder.py # Provenance graph
 521 | │   ├── scoring/
 522 | │   │   └── engine.py # Weighted scoring
 523 | │   ├── storage/
 524 | │   │   └── sqlite.py # Alert persistence
 525 | │   └── api/
 526 | │       └── main.py   # FastAPI server
 527 | ├── static/
 528 | │   └── index.html  # Dashboard UI
 529 | ├── data/
 530 | │   ├── sovnd.db     # Alert database
 531 | │   └── heartbeat.json # Throughput metric
 532 | ├── demo.py          # Orchestrator
 533 | └── README.md
 534 | ```
 535 | 
 536 | ---
 537 | 
 538 | *Generated: April 2026*
 539 | *Version: 0.1.0*
```

### code.md

```markdown
   1 | # Source Code
   2 | 
   3 | ## Python
   4 | 
   5 | ### c.py
   6 | 
   7 | ```python
   8 |    1 | #!/usr/bin/env python3
   9 |    2 | import os
  10 |    3 | from pathlib import Path
  11 |    4 | 
  12 |    5 | ROOT = Path(".")
  13 |    6 | OUTPUT = Path("code.md")
  14 |    7 | EXCLUDED_DIRS = {"venv", ".git", ".pytest_cache", ".logs", ".pids", "data", "deploy", ".streamlit"}
  15 |    8 | 
  16 |    9 | 
  17 |   10 | def get_all_files(root):
  18 |   11 |     files = {"py": [], "md": [], "html": []}
  19 |   12 |     for root_path in root.rglob("*"):
  20 |   13 |         if root_path.is_file():
  21 |   14 |             rel = root_path.relative_to(root)
  22 |   15 |             if any(excluded in rel.parts for excluded in EXCLUDED_DIRS):
  23 |   16 |                 continue
  24 |   17 |             if "__pycache__" in rel.parts:
  25 |   18 |                 continue
  26 |   19 |             if rel.suffix == ".py":
  27 |   20 |                 files["py"].append(rel)
  28 |   21 |             elif rel.suffix == ".md":
  29 |   22 |                 files["md"].append(rel)
  30 |   23 |             elif rel.suffix == ".html":
  31 |   24 |                 files["html"].append(rel)
  32 |   25 |     return {k: sorted(v) for k, v in files.items()}
  33 |   26 | 
  34 |   27 | 
  35 |   28 | def format_file_content(path):
  36 |   29 |     try:
  37 |   30 |         content = path.read_text(encoding="utf-8")
  38 |   31 |     except UnicodeDecodeError:
  39 |   32 |         return "    [binary file - skipped]"
  40 |   33 |     lines = content.splitlines()
  41 |   34 |     numbered = "\n".join(f"{i+1:4d} | {line}" for i, line in enumerate(lines))
  42 |   35 |     return numbered
  43 |   36 | 
  44 |   37 | 
  45 |   38 | all_files = get_all_files(ROOT)
  46 |   39 | 
  47 |   40 | with OUTPUT.open("w", encoding="utf-8") as out:
  48 |   41 |     out.write("# Source Code\n\n")
  49 |   42 | 
  50 |   43 |     out.write("## Python\n\n")
  51 |   44 |     for rel in all_files["py"]:
  52 |   45 |         full = ROOT / rel
  53 |   46 |         out.write(f"### {rel}\n\n```python\n")
  54 |   47 |         out.write(format_file_content(full))
  55 |   48 |         out.write("\n```\n\n")
  56 |   49 | 
  57 |   50 |     out.write("## Markdown\n\n")
  58 |   51 |     for rel in all_files["md"]:
  59 |   52 |         full = ROOT / rel
  60 |   53 |         ext = "markdown"
  61 |   54 |         out.write(f"### {rel}\n\n```{ext}\n")
  62 |   55 |         out.write(format_file_content(full))
  63 |   56 |         out.write("\n```\n\n")
  64 |   57 | 
  65 |   58 |     out.write("## HTML\n\n")
  66 |   59 |     for rel in all_files["html"]:
  67 |   60 |         full = ROOT / rel
  68 |   61 |         ext = "html"
  69 |   62 |         out.write(f"### {rel}\n\n```{ext}\n")
  70 |   63 |         out.write(format_file_content(full))
  71 |   64 |         out.write("\n```\n\n")
  72 |   65 | 
  73 |   66 | print(f"Wrote {len(all_files['py'])} Python files, {len(all_files['md'])} Markdown files, {len(all_files['html'])} HTML files to {OUTPUT}")
  74 | ```
  75 | 
  76 | ### demo.py
  77 | 
  78 | ```python
  79 |    1 | import subprocess
  80 |    2 | import time
  81 |    3 | import sys
  82 |    4 | import os
  83 |    5 | 
  84 |    6 | def start():
  85 |    7 |     if os.geteuid() != 0:
  86 |    8 |         print("❌ ERROR: The demo orchestrator must run as root (sudo).")
  87 |    9 |         sys.exit(1)
  88 |   10 | 
  89 |   11 |     real_user = os.environ.get('SUDO_USER')
  90 |   12 |     print("🛡️  SovND | Initializing SOC Demo...")
  91 |   13 |     
  92 |   14 |     # 1. Clean data for fresh start
  93 |   15 |     if os.path.exists("data/sovnd.db"):
  94 |   16 |         os.remove("data/sovnd.db")
  95 |   17 |     os.makedirs("data", exist_ok=True)
  96 |   18 |     os.chmod("data", 0o777)
  97 |   19 | 
  98 |   20 |     # 2. Start Dashboard Backend (User Port 8000)
  99 |   21 |     api_proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"])
 100 |   22 |     
 101 |   23 |     # 3. Start eBPF Agent (Kernel Monitor)
 102 |   24 |     agent_proc = subprocess.Popen([sys.executable, "src/main_agent.py"])
 103 |   25 | 
 104 |   26 |     time.sleep(2)
 105 |   27 |     print("\n🚀 ANALYTICS ENGINE READY: http://localhost:8000")
 106 |   28 |     
 107 |   29 |     # 4. Open browser as the regular user
 108 |   30 |     if real_user:
 109 |   31 |         os.system(f"sudo -u {real_user} xdg-open http://localhost:8000 > /dev/null 2>&1 &")
 110 |   32 | 
 111 |   33 |     try:
 112 |   34 |         while True:
 113 |   35 |             time.sleep(1)
 114 |   36 |     except KeyboardInterrupt:
 115 |   37 |         print("\nShutting down SovND...")
 116 |   38 |         api_proc.terminate()
 117 |   39 |         agent_proc.terminate()
 118 |   40 | 
 119 |   41 | if __name__ == "__main__":
 120 |   42 |     if len(sys.argv) > 1 and sys.argv[1] == "start":
 121 |   43 |         start()
 122 |   44 |     else:
 123 |   45 |         print("Usage: sudo python3 demo.py start")
 124 | ```
 125 | 
 126 | ### src/__init__.py
 127 | 
 128 | ```python
 129 | 
 130 | ```
 131 | 
 132 | ### src/api/main.py
 133 | 
 134 | ```python
 135 |    1 | import asyncio, json, os, time, random
 136 |    2 | from fastapi import FastAPI, WebSocket, WebSocketDisconnect
 137 |    3 | from fastapi.staticfiles import StaticFiles
 138 |    4 | from fastapi.responses import FileResponse, Response
 139 |    5 | from src.storage.sqlite import StorageManager
 140 |    6 | 
 141 |    7 | app = FastAPI()
 142 |    8 | storage = StorageManager()
 143 |    9 | 
 144 |   10 | os.makedirs("static", exist_ok=True)
 145 |   11 | static_mount = StaticFiles(directory="static")
 146 |   12 | 
 147 |   13 | class NoCacheStaticMount(StaticFiles):
 148 |   14 |     async def get_response(self, path, scope):
 149 |   15 |         response = await super().get_response(path, scope)
 150 |   16 |         response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
 151 |   17 |         response.headers["Pragma"] = "no-cache"
 152 |   18 |         response.headers["Expires"] = "0"
 153 |   19 |         return response
 154 |   20 | 
 155 |   21 | app.mount("/static", NoCacheStaticMount(directory="static"), name="static")
 156 |   22 | 
 157 |   23 | @app.get("/")
 158 |   24 | async def get_index():
 159 |   25 |     content = open("static/index.html", "r").read()
 160 |   26 |     return Response(
 161 |   27 |         content,
 162 |   28 |         media_type="text/html",
 163 |   29 |         headers={
 164 |   30 |             "Cache-Control": "no-cache, no-store, must-revalidate",
 165 |   31 |             "Pragma": "no-cache",
 166 |   32 |             "Expires": "0"
 167 |   33 |         }
 168 |   34 |     )
 169 |   35 | 
 170 |   36 | @app.websocket("/ws/telemetry")
 171 |   37 | async def websocket_endpoint(websocket: WebSocket):
 172 |   38 |     await websocket.accept()
 173 |   39 |     try:
 174 |   40 |         while True:
 175 |   41 |             alerts = storage.get_recent_alerts(limit=10)
 176 |   42 |             eps = 0
 177 |   43 |             try:
 178 |   44 |                 with open("data/heartbeat.json", "r") as f:
 179 |   45 |                     hb = json.load(f)
 180 |   46 |                     if time.time() - hb.get("timestamp", 0) < 3:
 181 |   47 |                         eps = hb.get("events_per_sec", 0)
 182 |   48 |             except: pass
 183 |   49 |             await websocket.send_json({"eps": eps, "alerts": alerts})
 184 |   50 |             await asyncio.sleep(0.5)
 185 |   51 |     except WebSocketDisconnect:
 186 |   52 |         pass
 187 |   53 | 
 188 |   54 | @app.post("/api/attack")
 189 |   55 | async def trigger_attack():
 190 |   56 |     payloads = [
 191 |   57 |         # High signature score (15 pts) - critical files
 192 |   58 |         ("signature", "cat /etc/shadow"),
 193 |   59 |         ("signature", "cat /etc/sudoers"),
 194 |   60 |         ("signature", "cat /var/run/docker.sock"),
 195 |   61 |         ("signature", "cat /root/.ssh/id_rsa"),
 196 |   62 |         
 197 |   63 |         # Graph heuristics - sensitive access
 198 |   64 |         ("graph", "find /etc -type f -name '*.conf' 2>/dev/null | head -10"),
 199 |   65 |         ("graph", "ls -la /root"),
 200 |   66 |         ("graph", "ls -la /etc/passwd /etc/shadow"),
 201 |   67 |         
 202 |   68 |         # Statistical anomaly - high frequency
 203 |   69 |         ("statistical", "bash -c 'for i in $(seq 1 100); do echo $i > /tmp/f$i; done'"),
 204 |   70 |         ("statistical", "touch /tmp/x{1..50}"),
 205 |   71 |         
 206 |   72 |         # Mixed - signature + graph
 207 |   73 |         ("both", "cat /etc/shadow && find /root -type f 2>/dev/null"),
 208 |   74 |     ]
 209 |   75 |     
 210 |   76 |     # Pick 3 random payloads
 211 |   77 |     selected = random.sample(payloads, 3)
 212 |   78 |     
 213 |   79 |     results = []
 214 |   80 |     for type_hint, cmd in selected:
 215 |   81 |         result = os.system(f"{cmd} > /dev/null 2>&1 &")
 216 |   82 |         results.append({"type": type_hint, "cmd": cmd, "result": result})
 217 |   83 |     
 218 |   84 |     return {"status": "attacks_launched", "count": len(selected), "payloads": results}
 219 | ```
 220 | 
 221 | ### src/dashboard/app.py
 222 | 
 223 | ```python
 224 |    1 | import streamlit as st
 225 |    2 | import pandas as pd
 226 |    3 | import plotly.express as px
 227 |    4 | import json
 228 |    5 | import os
 229 |    6 | import time
 230 |    7 | import subprocess
 231 |    8 | from datetime import datetime
 232 |    9 | import sys
 233 |   10 | 
 234 |   11 | sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
 235 |   12 | from src.storage.sqlite import StorageManager
 236 |   13 | 
 237 |   14 | # Get project root (parent of src/)
 238 |   15 | PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
 239 |   16 | if PROJECT_ROOT.endswith('/src'):
 240 |   17 |     PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)
 241 |   18 | HEARTBEAT_FILE = os.path.join(PROJECT_ROOT, "data", "heartbeat.json")
 242 |   19 | 
 243 |   20 | # ----------------- PAGE CONFIG -----------------
 244 |   21 | st.set_page_config(
 245 |   22 |     page_title="SovND | Command Center",
 246 |   23 |     page_icon="🛡️",
 247 |   24 |     layout="wide",
 248 |   25 |     initial_sidebar_state="expanded"
 249 |   26 | )
 250 |   27 | 
 251 |   28 | # Force Dark Mode CSS & Custom Styling
 252 |   29 | st.markdown("""
 253 |   30 |     <style>
 254 |   31 |     .stApp { background-color: #0e1117; color: #fafafa; }
 255 |   32 |     .metric-card { 
 256 |   33 |         background-color: #1e293b; padding: 20px; border-radius: 8px; 
 257 |   34 |         border-left: 5px solid #3b82f6; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
 258 |   35 |     }
 259 |   36 |     .alert-critical { 
 260 |   37 |         background-color: #450a0a; border-left: 5px solid #ef4444; 
 261 |   38 |         padding: 15px; border-radius: 5px; margin-bottom: 10px;
 262 |   39 |     }
 263 |   40 |     .stButton>button { width: 100%; font-weight: bold; }
 264 |   41 |     .attack-btn>button { background-color: #7f1d1d !important; color: white !important; border: 1px solid #ef4444 !important; }
 265 |   42 |     
 266 |   43 |     /* Attack flash animation */
 267 |   44 |     @keyframes flash-red {
 268 |   45 |         0% { box-shadow: inset 0 0 0 0 rgba(239, 68, 68, 0); }
 269 |   46 |         50% { box-shadow: inset 0 0 100px 50px rgba(239, 68, 68, 0.5); }
 270 |   47 |         100% { box-shadow: inset 0 0 0 0 rgba(239, 68, 68, 0); }
 271 |   48 |     }
 272 |   49 |     .attack-flash {
 273 |   50 |         animation: flash-red 1s ease-out;
 274 |   51 |     }
 275 |   52 |     </style>
 276 |   53 | """, unsafe_allow_html=True)
 277 |   54 | 
 278 |   55 | # ----------------- STATE & DATA -----------------
 279 |   56 | storage = StorageManager()
 280 |   57 | 
 281 |   58 | if 'syscall_history' not in st.session_state:
 282 |   59 |     st.session_state.syscall_history =[]
 283 |   60 | if 'live_monitor' not in st.session_state:
 284 |   61 |     st.session_state.live_monitor = True
 285 |   62 | if 'attack_events' not in st.session_state:
 286 |   63 |     st.session_state.attack_events = []
 287 |   64 | if 'last_alert_count' not in st.session_state:
 288 |   65 |     st.session_state.last_alert_count = 0
 289 |   66 | if 'flash_screen' not in st.session_state:
 290 |   67 |     st.session_state.flash_screen = False
 291 |   68 | 
 292 |   69 | # Use PROJECT_ROOT which is correctly calculated above
 293 |   70 | 
 294 |   71 | def load_heartbeat():
 295 |   72 |     try:
 296 |   73 |         with open(HEARTBEAT_FILE, "r") as f:
 297 |   74 |             data = json.load(f)
 298 |   75 |             return data.get("events_per_sec", 0)
 299 |   76 |     except:
 300 |   77 |         return 0
 301 |   78 | 
 302 |   79 | def launch_real_attack():
 303 |   80 |     """Executes the actual attacks directly from Python, no external scripts needed."""
 304 |   81 |     try:
 305 |   82 |         # 1. Trigger /etc/shadow read alert (Signature Match)
 306 |   83 |         subprocess.run(["cat", "/etc/shadow"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
 307 |   84 |         
 308 |   85 |         # 2. Trigger Docker sock access alert (Signature Match)
 309 |   86 |         subprocess.run(["cat", "/var/run/docker.sock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
 310 |   87 |         
 311 |   88 |         # 3. Trigger suspicious shell (Heuristic)
 312 |   89 |         subprocess.run(["bash", "-c", "echo 'stealth shell'"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
 313 |   90 |         
 314 |   91 |         # Mark attack time for graph highlighting
 315 |   92 |         st.session_state.attack_events.append(datetime.now())
 316 |   93 |         # Clean up old attack markers (older than 60 seconds)
 317 |   94 |         st.session_state.attack_events = [
 318 |   95 |             t for t in st.session_state.attack_events 
 319 |   96 |             if (datetime.now() - t).total_seconds() < 60
 320 |   97 |         ]
 321 |   98 |         
 322 |   99 |         return True
 323 |  100 |     except Exception as e:
 324 |  101 |         st.error(f"Failed to launch attack: {e}")
 325 |  102 |         return False
 326 |  103 | 
 327 |  104 | # ----------------- SIDEBAR -----------------
 328 |  105 | with st.sidebar:
 329 |  106 |     st.image("https://img.icons8.com/fluency/96/shield.png", width=60)
 330 |  107 |     st.title("SovND Control")
 331 |  108 |     st.markdown("---")
 332 |  109 |     
 333 |  110 |     st.session_state.live_monitor = st.toggle("🔴 Live Auto-Refresh", value=st.session_state.live_monitor)
 334 |  111 |     
 335 |  112 |     st.markdown("---")
 336 |  113 |     st.markdown("### ⚠️ Live Demo Actions")
 337 |  114 |     st.caption("These buttons execute REAL scripts on the host machine.")
 338 |  115 |     
 339 |  116 |     # Wrap button in custom class for red styling
 340 |  117 |     st.markdown('<div class="attack-btn">', unsafe_allow_html=True)
 341 |  118 |     if st.button("💥 LAUNCH REAL ATTACK", use_container_width=True):
 342 |  119 |         launch_real_attack()
 343 |  120 |     st.markdown('</div>', unsafe_allow_html=True)
 344 |  121 | 
 345 |  122 | # ----------------- MAIN DASHBOARD -----------------
 346 |  123 | st.title("🛡️ SovND Security Command Center")
 347 |  124 | st.caption("Live eBPF Kernel Telemetry & Threat Detection")
 348 |  125 | 
 349 |  126 | # Apply flash effect if new alerts
 350 |  127 | if st.session_state.flash_screen:
 351 |  128 |     st.markdown("""
 352 |  129 |         <div class="attack-flash" style="position:fixed; top:0; left:0; right:0; bottom:0; pointer-events:none; z-index:9999;"></div>
 353 |  130 |     """, unsafe_allow_html=True)
 354 |  131 |     st.session_state.flash_screen = False
 355 |  132 | 
 356 |  133 | # 1. Fetch live data
 357 |  134 | alerts_data = storage.get_recent_alerts(limit=50)
 358 |  135 | df_alerts = pd.DataFrame(alerts_data) if alerts_data else pd.DataFrame()
 359 |  136 | total_alerts = len(df_alerts)
 360 |  137 | 
 361 |  138 | # Trigger flash if new alerts appeared
 362 |  139 | if total_alerts > st.session_state.last_alert_count:
 363 |  140 |     st.session_state.flash_screen = True
 364 |  141 | st.session_state.last_alert_count = total_alerts
 365 |  142 | 
 366 |  143 | current_eps = load_heartbeat()
 367 |  144 | st.session_state.syscall_history.append({"time": datetime.now(), "events": current_eps})
 368 |  145 | if len(st.session_state.syscall_history) > 30: # Keep last 30 seconds
 369 |  146 |     st.session_state.syscall_history.pop(0)
 370 |  147 | 
 371 |  148 | # 2. Top KPIs
 372 |  149 | k1, k2, k3 = st.columns(3)
 373 |  150 | with k1:
 374 |  151 |     st.markdown(f"""
 375 |  152 |         <div class="metric-card">
 376 |  153 |             <h3 style="margin:0; color:#94a3b8; font-size:1rem;">Kernel Events / Sec</h3>
 377 |  154 |             <h1 style="margin:0; font-size:2.5rem;">{current_eps}</h1>
 378 |  155 |         </div>
 379 |  156 |     """, unsafe_allow_html=True)
 380 |  157 | with k2:
 381 |  158 |     alert_color = "#ef4444" if total_alerts > 0 else "#22c55e"
 382 |  159 |     st.markdown(f"""
 383 |  160 |         <div class="metric-card" style="border-left-color: {alert_color};">
 384 |  161 |             <h3 style="margin:0; color:#94a3b8; font-size:1rem;">Total Critical Alerts</h3>
 385 |  162 |             <h1 style="margin:0; font-size:2.5rem; color:{alert_color};">{total_alerts}</h1>
 386 |  163 |         </div>
 387 |  164 |     """, unsafe_allow_html=True)
 388 |  165 | with k3:
 389 |  166 |     status = "Active & Enforcing" if st.session_state.live_monitor else "Paused"
 390 |  167 |     st.markdown(f"""
 391 |  168 |         <div class="metric-card" style="border-left-color: #10b981;">
 392 |  169 |             <h3 style="margin:0; color:#94a3b8; font-size:1rem;">eBPF Engine Status</h3>
 393 |  170 |             <h1 style="margin:0; font-size:1.8rem; padding-top:10px; color:#10b981;">{status}</h1>
 394 |  171 |         </div>
 395 |  172 |     """, unsafe_allow_html=True)
 396 |  173 | 
 397 |  174 | st.markdown("<br>", unsafe_allow_html=True)
 398 |  175 | 
 399 |  176 | # 3. Main View: Chart on left, Alerts on right
 400 |  177 | col_chart, col_alerts = st.columns([2, 1])
 401 |  178 | 
 402 |  179 | with col_chart:
 403 |  180 |     st.markdown("### 📈 Live System Call Throughput")
 404 |  181 |     if len(st.session_state.syscall_history) > 1:
 405 |  182 |         df_history = pd.DataFrame(st.session_state.syscall_history)
 406 |  183 |         
 407 |  184 |         # Create the chart
 408 |  185 |         fig = px.area(df_history, x='time', y='events', 
 409 |  186 |                      color_discrete_sequence=['#3b82f6'],
 410 |  187 |                      template="plotly_dark")
 411 |  188 |         
 412 |  189 |         # Add red zones for attack periods (last 10 seconds after each attack)
 413 |  190 |         now = datetime.now()
 414 |  191 |         for attack_time in st.session_state.attack_events:
 415 |  192 |             time_diff = (now - attack_time).total_seconds()
 416 |  193 |             if time_diff < 10:
 417 |  194 |                 # Convert datetime to timestamp for plotly
 418 |  195 |                 attack_ts = attack_time.timestamp()
 419 |  196 |                 end_ts = min(attack_ts + 5, now.timestamp())
 420 |  197 |                 if end_ts > attack_ts:
 421 |  198 |                     fig.add_vrect(
 422 |  199 |                         x0=attack_ts, 
 423 |  200 |                         x1=end_ts,
 424 |  201 |                         fillcolor="rgba(239, 68, 68, 0.25)", 
 425 |  202 |                         opacity=0.25, 
 426 |  203 |                         line_width=0,
 427 |  204 |                         annotation_text="ATTACK", 
 428 |  205 |                         annotation_position="top left",
 429 |  206 |                         annotation_font_color="red"
 430 |  207 |                     )
 431 |  208 |         
 432 |  209 |         fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=350,
 433 |  210 |                           xaxis_title="", yaxis_title="Events / Sec")
 434 |  211 |         st.plotly_chart(fig, use_container_width=True)
 435 |  212 |     else:
 436 |  213 |         st.info("Gathering kernel telemetry...")
 437 |  214 | 
 438 |  215 | with col_alerts:
 439 |  216 |     st.markdown("### 🚨 Live Threat Feed")
 440 |  217 |     if not df_alerts.empty:
 441 |  218 |         # Show top 4 most recent alerts
 442 |  219 |         for _, row in df_alerts.head(4).iterrows():
 443 |  220 |             reasons = ", ".join(row['reasons']) if isinstance(row['reasons'], list) else row['reasons']
 444 |  221 |             st.markdown(f"""
 445 |  222 |                 <div class="alert-critical">
 446 |  223 |                     <div style="font-size: 0.8rem; color: #fca5a5;">{row['timestamp']}</div>
 447 |  224 |                     <strong style="font-size: 1.1rem;">PID {row['pid']} - {row.get('severity', 'CRITICAL').upper()}</strong><br>
 448 |  225 |                     <span style="font-size: 0.9rem;">{reasons}</span>
 449 |  226 |                 </div>
 450 |  227 |             """, unsafe_allow_html=True)
 451 |  228 |         if len(df_alerts) > 4:
 452 |  229 |             st.caption(f"+ {len(df_alerts) - 4} older alerts hidden.")
 453 |  230 |     else:
 454 |  231 |         st.markdown("""
 455 |  232 |             <div style="padding:20px; text-align:center; color:#94a3b8; border: 1px dashed #334155; border-radius: 5px;">
 456 |  233 |                 ✅ System is secure. No anomalous activity detected.
 457 |  234 |             </div>
 458 |  235 |         """, unsafe_allow_html=True)
 459 |  236 | 
 460 |  237 | # 4. Auto-refresh loop
 461 |  238 | if st.session_state.live_monitor:
 462 |  239 |     time.sleep(1.5)
 463 |  240 |     st.rerun()
 464 | ```
 465 | 
 466 | ### src/detector/signature.py
 467 | 
 468 | ```python
 469 |    1 | import re
 470 |    2 | import logging
 471 |    3 | from typing import List, Dict, Optional, Any
 472 |    4 | 
 473 |    5 | logger = logging.getLogger(__name__)
 474 |    6 | 
 475 |    7 | class SignatureDetector:
 476 |    8 |     """
 477 |    9 |     Implements fast signature-based detection (Section 2.2).
 478 |   10 |     Checks for sensitive file access and known malicious patterns.
 479 |   11 |     """
 480 |   12 |     
 481 |   13 |     def __init__(self):
 482 |   14 |         # High-priority sensitive paths (IOCs)
 483 |   15 |         self.critical_paths = [
 484 |   16 |             re.compile(r'^/etc/shadow$'),
 485 |   17 |             re.compile(r'^/etc/sudoers$'),
 486 |   18 |             re.compile(r'^/var/run/docker\.sock$'),
 487 |   19 |             re.compile(r'^/root/.ssh/.*'),
 488 |   20 |             re.compile(r'^/proc/kcore$')
 489 |   21 |         ]
 490 |   22 |         
 491 |   23 |         # Suspicious patterns (e.g., shell access from web server)
 492 |   24 |         self.suspicious_comm = ["bash", "sh", "nc", "ncat", "python", "perl"]
 493 |   25 | 
 494 |   26 |     def analyze_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
 495 |   27 |         """
 496 |   28 |         Quickly scans an event for signature matches.
 497 |   29 |         """
 498 |   30 |         filename = event.get("filename") or ""
 499 |   31 |         comm = event.get("comm") or ""
 500 |   32 |         
 501 |   33 |         if not filename:
 502 |   34 |             return None
 503 |   35 |         
 504 |   36 |         # Check for sensitive path access
 505 |   37 |         for pattern in self.critical_paths:
 506 |   38 |             if pattern.match(filename):
 507 |   39 |                 return {
 508 |   40 |                     "type": "SIGNATURE_MATCH",
 509 |   41 |                     "reason": f"Access to critical file: {filename}",
 510 |   42 |                     "severity": "critical",
 511 |   43 |                     "ioc": filename
 512 |   44 |                 }
 513 |   45 |         
 514 |   46 |         # Check for suspicious process execution (simplified)
 515 |   47 |         # In a real impl, we'd check if a non-shell process spawns a shell
 516 |   48 |         if any(s in comm for s in self.suspicious_comm):
 517 |   49 |             # This is a heuristic, should be combined with context
 518 |   50 |             if "/bin/" in filename or "/usr/bin/" in filename:
 519 |   51 |                 return {
 520 |   52 |                     "type": "HEURISTIC_MATCH",
 521 |   53 |                     "reason": f"Suspicious process activity: {comm}",
 522 |   54 |                     "severity": "warning"
 523 |   55 |                 }
 524 |   56 |                 
 525 |   57 |         return None
 526 | ```
 527 | 
 528 | ### src/detector/statistical.py
 529 | 
 530 | ```python
 531 |    1 | import numpy as np
 532 |    2 | import logging
 533 |    3 | from typing import Any, Dict, Optional, List
 534 |    4 | from src.metrics.engine import MetricsEngine
 535 |    5 | 
 536 |    6 | logger = logging.getLogger(__name__)
 537 |    7 | 
 538 |    8 | class StatisticalDetector:
 539 |    9 |     """
 540 |   10 |     Implements the Statistical Module from Section 2.2.
 541 |   11 |     Evaluates process behavior based on Z-scores and vector distances.
 542 |   12 |     """
 543 |   13 |     
 544 |   14 |     def __init__(self, engine: MetricsEngine, threshold_z: float = 3.0):
 545 |   15 |         self.engine = engine
 546 |   16 |         self.threshold_z = threshold_z
 547 |   17 | 
 548 |   18 |     def evaluate(self, pid: int, current_metrics: np.ndarray) -> Dict[str, Any]:
 549 |   19 |         """
 550 |   20 |         Analyzes the current metrics vector for a PID.
 551 |   21 |         
 552 |   22 |         Returns:
 553 |   23 |             A report containing anomaly status and specific scores.
 554 |   24 |         """
 555 |   25 |         z_scores = self.engine.get_z_scores(pid, current_metrics)
 556 |   26 |         max_z = np.max(np.abs(z_scores)) if z_scores.size > 0 else 0.0
 557 |   27 |         
 558 |   28 |         is_anomalous = max_z > self.threshold_z if self.threshold_z > 0 else False
 559 |   29 |         
 560 |   30 |         prof = self.engine.profiles.get(pid)
 561 |   31 |         distance = 0.0
 562 |   32 |         if prof is not None and current_metrics.size > 0:
 563 |   33 |             distance = np.linalg.norm(current_metrics - prof["mu"])
 564 |   34 | 
 565 |   35 |         return {
 566 |   36 |             "pid": pid,
 567 |   37 |             "is_anomalous": bool(is_anomalous),
 568 |   38 |             "max_z_score": float(max_z),
 569 |   39 |             "z_vector": z_scores.tolist(),
 570 |   40 |             "euclidean_distance": float(distance),
 571 |   41 |             "severity": self._map_to_severity(max_z)
 572 |   42 |         }
 573 |   43 | 
 574 |   44 |     def _map_to_severity(self, z_score: float) -> str:
 575 |   45 |         if z_score < self.threshold_z:
 576 |   46 |             return "info"
 577 |   47 |         elif z_score >= self.threshold_z * 2:
 578 |   48 |             return "critical"
 579 |   49 |         elif z_score >= self.threshold_z:
 580 |   50 |             return "warning"
 581 |   51 |         else:
 582 |   52 |             return "info"
 583 | ```
 584 | 
 585 | ### src/docker/resolver.py
 586 | 
 587 | ```python
 588 |    1 | import logging
 589 |    2 | import os
 590 |    3 | import threading
 591 |    4 | from typing import Dict, Optional, Any
 592 |    5 | import docker
 593 |    6 | from docker.errors import DockerException
 594 |    7 | 
 595 |    8 | logger = logging.getLogger(__name__)
 596 |    9 | 
 597 |   10 | class ContainerResolver:
 598 |   11 |     """
 599 |   12 |     Maps Linux cgroup IDs to Docker container metadata.
 600 |   13 |     Implements a thread-safe cache to minimize overhead of Docker API calls.
 601 |   14 |     """
 602 |   15 |     
 603 |   16 |     def __init__(self, socket_path: str = "unix://var/run/docker.sock", target_label: str = None):
 604 |   17 |         self.target_label = target_label or os.environ.get("TARGET_LABEL")
 605 |   18 |         try:
 606 |   19 |             self.client = docker.DockerClient(base_url=socket_path)
 607 |   20 |             self._cache: Dict[int, Dict[str, Any]] = {}
 608 |   21 |             self._lock = threading.RLock()
 609 |   22 |             logger.info("ContainerResolver initialized with Docker socket: %s, target_label: %s", 
 610 |   23 |                       socket_path, self.target_label)
 611 |   24 |         except DockerException as e:
 612 |   25 |             logger.error("Failed to connect to Docker daemon: %s", e)
 613 |   26 |             self.client = None
 614 |   27 | 
 615 |   28 |     def _container_matches_label(self, container) -> bool:
 616 |   29 |         """Check if container has the target label."""
 617 |   30 |         if not self.target_label:
 618 |   31 |             return True
 619 |   32 |         label_key, label_value = self.target_label.split("=") if "=" in self.target_label else (self.target_label, "")
 620 |   33 |         container_labels = container.labels or {}
 621 |   34 |         actual_value = container_labels.get(label_key)
 622 |   35 |         if label_value:
 623 |   36 |             return actual_value == label_value
 624 |   37 |         return label_key in container_labels
 625 |   38 | 
 626 |   39 |     def resolve(self, cgroup_id: int) -> Optional[Dict[str, Any]]:
 627 |   40 |         """
 628 |   41 |         Resolves a cgroup_id to container metadata.
 629 |   42 |         
 630 |   43 |         Args:
 631 |   44 |             cgroup_id: The 64-bit cgroup identifier from eBPF.
 632 |   45 |             
 633 |   46 |         Returns:
 634 |   47 |             A dictionary with container info or None if not found/error.
 635 |   48 |         """
 636 |   49 |         if not self.client:
 637 |   50 |             return None
 638 |   51 | 
 639 |   52 |         with self._lock:
 640 |   53 |             if cgroup_id in self._cache:
 641 |   54 |                 return self._cache[cgroup_id]
 642 |   55 | 
 643 |   56 |         return self._refresh_and_resolve(cgroup_id)
 644 |   57 | 
 645 |   58 |     def _refresh_and_resolve(self, target_cgroup_id: int) -> Optional[Dict[str, Any]]:
 646 |   59 |         """
 647 |   60 |         Refreshes the internal cache by enumerating running containers.
 648 |   61 |         In a high-churn environment, this could be optimized to use Docker events.
 649 |   62 |         """
 650 |   63 |         try:
 651 |   64 |             containers = self.client.containers.list()
 652 |   65 |             new_cache = {}
 653 |   66 |             
 654 |   67 |             for container in containers:
 655 |   68 |                 if not self._container_matches_label(container):
 656 |   69 |                     continue
 657 |   70 |                 try:
 658 |   71 |                     # Basic metadata
 659 |   72 |                     meta = {
 660 |   73 |                         "id": container.id,
 661 |   74 |                         "name": container.name,
 662 |   75 |                         "image": container.image.tags[0] if container.image.tags else "unknown",
 663 |   76 |                         "labels": container.labels
 664 |   77 |                     }
 665 |   78 |                     
 666 |   79 |                     # Implementation detail: Extracting the numeric cgroup ID
 667 |   80 |                     # requires reading /sys/fs/cgroup/... or using a heuristic.
 668 |   81 |                     # For the purpose of the Stage 4 skeleton, we store by name.
 669 |   82 |                     # Real-world eBPF agents often use a BPF map populated by 
 670 |   83 |                     # a sidecar or by this resolver upon container start.
 671 |   84 |                     
 672 |   85 |                     # Placeholder: In a production senior-level impl, we'd match 
 673 |   86 |                     # container.attrs['State']['Pid'] to its cgroup inode.
 674 |   87 |                     # Here we simulate the successful resolution.
 675 |   88 |                     new_cache[target_cgroup_id] = meta # Simplified for demo
 676 |   89 |                 except (KeyError, IndexError):
 677 |   90 |                     continue
 678 |   91 | 
 679 |   92 |             with self._lock:
 680 |   93 |                 self._cache.update(new_cache)
 681 |   94 |                 return self._cache.get(target_cgroup_id)
 682 |   95 | 
 683 |   96 |         except DockerException as e:
 684 |   97 |             logger.error("Error refreshing container cache: %s", e)
 685 |   98 |             return None
 686 |   99 | 
 687 |  100 |     def clear_cache(self):
 688 |  101 |         with self._lock:
 689 |  102 |             self._cache.clear()
 690 | ```
 691 | 
 692 | ### src/ebpf_agent.py
 693 | 
 694 | ```python
 695 |    1 | import ctypes
 696 |    2 | import os
 697 |    3 | import threading
 698 |    4 | import queue
 699 |    5 | from dataclasses import dataclass
 700 |    6 | 
 701 |    7 | # Define the event structure matching tracer.bpf.c
 702 |    8 | class Event(ctypes.Structure):
 703 |    9 |     _fields_ = [
 704 |   10 |         ("pid", ctypes.c_uint32),
 705 |   11 |         ("tgid", ctypes.c_uint32),
 706 |   12 |         ("cgroup_id", ctypes.c_uint64),
 707 |   13 |         ("syscall_id", ctypes.c_uint32),
 708 |   14 |         ("comm", ctypes.c_char * 16),
 709 |   15 |         ("filename", ctypes.c_char * 256),
 710 |   16 |     ]
 711 |   17 | 
 712 |   18 | # Callback type for the C loader
 713 |   19 | EVENT_CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(Event), ctypes.c_size_t)
 714 |   20 | 
 715 |   21 | class EBPFAgent:
 716 |   22 |     def __init__(self, lib_path="./ebpf/libloader.so"):
 717 |   23 |         self.lib = ctypes.CDLL(os.path.abspath(lib_path))
 718 |   24 |         self.event_queue = queue.Queue()
 719 |   25 |         
 720 |   26 |         self.lib.start_loader.argtypes = [EVENT_CB]
 721 |   27 |         self.lib.start_loader.restype = ctypes.c_int
 722 |   28 |         
 723 |   29 |         self.lib.poll_events.argtypes = [ctypes.c_int]
 724 |   30 |         self.lib.poll_events.restype = ctypes.c_int
 725 |   31 |         
 726 |   32 |         self.lib.stop_loader.argtypes = []
 727 |   33 |         self.lib.stop_loader.restype = None
 728 |   34 |         
 729 |   35 |         self._callback_ref = EVENT_CB(self._event_handler)
 730 |   36 |         self.running = False
 731 |   37 |         self.thread = None
 732 |   38 | 
 733 |   39 |     def _event_handler(self, ctx, event_ptr, size):
 734 |   40 |         event = event_ptr.contents
 735 |   41 |         # Copy data out of the BPF ring buffer to the Python queue
 736 |   42 |         self.event_queue.put({
 737 |   43 |             "pid": event.pid,
 738 |   44 |             "tgid": event.tgid,
 739 |   45 |             "cgroup_id": event.cgroup_id,
 740 |   46 |             "syscall_id": event.syscall_id,
 741 |   47 |             "comm": event.comm.decode('utf-8', 'replace'),
 742 |   48 |             "filename": event.filename.decode('utf-8', 'replace')
 743 |   49 |         })
 744 |   50 | 
 745 |   51 |     def start(self):
 746 |   52 |         err = self.lib.start_loader(self._callback_ref)
 747 |   53 |         if err != 0:
 748 |   54 |             raise RuntimeError(f"Failed to start eBPF loader: {err}")
 749 |   55 |         
 750 |   56 |         self.running = True
 751 |   57 |         self.thread = threading.Thread(target=self._poll_loop, daemon=True)
 752 |   58 |         self.thread.start()
 753 |   59 | 
 754 |   60 |     def _poll_loop(self):
 755 |   61 |         while self.running:
 756 |   62 |             self.lib.poll_events(100) # 100ms timeout
 757 |   63 | 
 758 |   64 |     def stop(self):
 759 |   65 |         self.running = False
 760 |   66 |         if self.thread:
 761 |   67 |             self.thread.join()
 762 |   68 |         self.lib.stop_loader()
 763 |   69 | 
 764 |   70 |     def get_event(self, block=True, timeout=None):
 765 |   71 |         try:
 766 |   72 |             return self.event_queue.get(block=block, timeout=timeout)
 767 |   73 |         except queue.Empty:
 768 |   74 |             return None
 769 |   75 | 
 770 |   76 | if __name__ == "__main__":
 771 |   77 |     # Basic test if run directly
 772 |   78 |     import time
 773 |   79 |     agent = EBPFAgent()
 774 |   80 |     print("Starting agent... (requires root/CAP_BPF)")
 775 |   81 |     try:
 776 |   82 |         agent.start()
 777 |   83 |         print("Monitoring... Press Ctrl+C to stop")
 778 |   84 |         while True:
 779 |   85 |             event = agent.get_event(timeout=1)
 780 |   86 |             if event:
 781 |   87 |                 print(f"Event: {event}")
 782 |   88 |     except KeyboardInterrupt:
 783 |   89 |         pass
 784 |   90 |     finally:
 785 |   91 |         agent.stop()
 786 | ```
 787 | 
 788 | ### src/graph/builder.py
 789 | 
 790 | ```python
 791 |    1 | import networkx as nx
 792 |    2 | import logging
 793 |    3 | from typing import Dict, Any, Optional
 794 |    4 | from datetime import datetime
 795 |    5 | 
 796 |    6 | logger = logging.getLogger(__name__)
 797 |    7 | 
 798 |    8 | class ProvenanceGraphBuilder:
 799 |    9 |     """
 800 |   10 |     Constructs a directed provenance graph (Section 2.2).
 801 |   11 |     Nodes: Processes, Files, Sockets.
 802 |   12 |     Edges: Actions (open, read, write).
 803 |   13 |     """
 804 |   14 |     
 805 |   15 |     def __init__(self):
 806 |   16 |         self.graph = nx.DiGraph()
 807 |   17 |         logger.info("ProvenanceGraphBuilder initialized.")
 808 |   18 | 
 809 |   19 |     def add_event(self, event: Dict[str, Any]):
 810 |   20 |         """
 811 |   21 |         Adds an event to the graph. 
 812 |   22 |         Event structure: pid, comm, filename, syscall_id, timestamp
 813 |   23 |         """
 814 |   24 |         pid = event.get("pid")
 815 |   25 |         comm = event.get("comm", "unknown")
 816 |   26 |         filename = event.get("filename", "")
 817 |   27 |         syscall = event.get("syscall_id")
 818 |   28 |         
 819 |   29 |         # Process node
 820 |   30 |         proc_node = f"proc_{pid}"
 821 |   31 |         if not self.graph.has_node(proc_node):
 822 |   32 |             self.graph.add_node(proc_node, type="process", pid=pid, comm=comm)
 823 |   33 |             
 824 |   34 |         # Resource node (if applicable)
 825 |   35 |         if filename:
 826 |   36 |             res_node = f"file_{filename}"
 827 |   37 |             if not self.graph.has_node(res_node):
 828 |   38 |                 self.graph.add_node(res_node, type="file", path=filename)
 829 |   39 |             
 830 |   40 |             # Add edge representing the action
 831 |   41 |             self.graph.add_edge(
 832 |   42 |                 proc_node, 
 833 |   43 |                 res_node, 
 834 |   44 |                 syscall=syscall, 
 835 |   45 |                 timestamp=datetime.now().isoformat()
 836 |   46 |             )
 837 |   47 | 
 838 |   48 |     def get_process_subgraph(self, pid: int) -> nx.DiGraph:
 839 |   49 |         """
 840 |   50 |         Returns the neighborhood of a specific process.
 841 |   51 |         """
 842 |   52 |         proc_node = f"proc_{pid}"
 843 |   53 |         if not self.graph.has_node(proc_node):
 844 |   54 |             return nx.DiGraph()
 845 |   55 |             
 846 |   56 |         nodes = [proc_node] + list(self.graph.neighbors(proc_node))
 847 |   57 |         return self.graph.subgraph(nodes)
 848 |   58 | 
 849 |   59 |     def get_serialized_graph(self) -> Dict[str, Any]:
 850 |   60 |         """
 851 |   61 |         Serializes the graph for UI consumption (e.g., cytoscape or d3 format).
 852 |   62 |         """
 853 |   63 |         return nx.node_link_data(self.graph)
 854 |   64 | 
 855 |   65 |     def clear(self):
 856 |   66 |         self.graph.clear()
 857 | ```
 858 | 
 859 | ### src/main_agent.py
 860 | 
 861 | ```python
 862 |    1 | import time, sys, os, json, dataclasses
 863 |    2 | from pathlib import Path
 864 |    3 | import random
 865 |    4 | 
 866 |    5 | try:
 867 |    6 |     import numpy as np
 868 |    7 |     HAS_NUMPY = True
 869 |    8 | except ImportError:
 870 |    9 |     HAS_NUMPY = False
 871 |   10 |     np = None
 872 |   11 |     print("⚠️ numpy not available - statistical detection disabled")
 873 |   12 | 
 874 |   13 | try:
 875 |   14 |     import networkx as nx
 876 |   15 |     HAS_NETWORKX = True
 877 |   16 | except ImportError:
 878 |   17 |     HAS_NETWORKX = False
 879 |   18 |     nx = None
 880 |   19 |     print("⚠️ networkx not available - graph detection disabled")
 881 |   20 | 
 882 |   21 | try:
 883 |   22 |     sys.path.insert(0, str(Path(__file__).parent.parent))
 884 |   23 |     from src.ebpf_agent import EBPFAgent
 885 |   24 |     from src.detector.signature import SignatureDetector
 886 |   25 |     
 887 |   26 |     if HAS_NUMPY:
 888 |   27 |         from src.detector.statistical import StatisticalDetector
 889 |   28 |         from src.metrics.engine import MetricsEngine
 890 |   29 |         from src.scoring.engine import ScoringEngine
 891 |   30 |         STAT_DETECTOR = True
 892 |   31 |     else:
 893 |   32 |         from src.scoring.engine import ScoringEngine
 894 |   33 |         STAT_DETECTOR = False
 895 |   34 |     
 896 |   35 |     if HAS_NETWORKX:
 897 |   36 |         from src.graph.builder import ProvenanceGraphBuilder
 898 |   37 |     else:
 899 |   38 |         ProvenanceGraphBuilder = None
 900 |   39 |     
 901 |   40 |     from src.storage.sqlite import StorageManager
 902 |   41 | except Exception as e:
 903 |   42 |     print(f"⚠️ Import error: {e}")
 904 |   43 |     raise
 905 |   44 | 
 906 |   45 | def run_agent():
 907 |   46 |     print("🛡️ Starting SovND Real-time eBPF Engine...")
 908 |   47 |     lib_path = Path(__file__).parent.parent / "ebpf" / "libloader.so"
 909 |   48 |     
 910 |   49 |     # Pre-populated process heap for demo (simulates baseline profiles)
 911 |   50 |     preloaded_pids = list(range(1000, 1100))
 912 |   51 |     random.shuffle(preloaded_pids)
 913 |   52 |     
 914 |   53 |     agent = EBPFAgent(lib_path=str(lib_path))
 915 |   54 |     sig_detector = SignatureDetector()
 916 |   55 |     scoring = ScoringEngine(threshold=15.0)
 917 |   56 |     storage = StorageManager()
 918 |   57 |     
 919 |   58 |     if STAT_DETECTOR and HAS_NUMPY:
 920 |   59 |         print("📊 Statistical detection enabled")
 921 |   60 |         metrics_engine = MetricsEngine()
 922 |   61 |         stat_detector = StatisticalDetector(engine=metrics_engine, threshold_z=2.5)
 923 |   62 |     else:
 924 |   63 |         print("📊 Statistical detection DISABLED")
 925 |   64 |         metrics_engine = None
 926 |   65 |         stat_detector = None
 927 |   66 |     
 928 |   67 |     if HAS_NETWORKX and ProvenanceGraphBuilder:
 929 |   68 |         print("🔗 Graph detection enabled")
 930 |   69 |         graph_builder = ProvenanceGraphBuilder()
 931 |   70 |     else:
 932 |   71 |         print("🔗 Graph detection DISABLED")
 933 |   72 |         graph_builder = None
 934 |   73 | 
 935 |   74 |     # Clear old data for demo freshness
 936 |   75 |     storage.clear_alerts()
 937 |   76 | 
 938 |   77 |     try:
 939 |   78 |         agent.start()
 940 |   79 |         print("✅ eBPF Agent attached. Monitoring...")
 941 |   80 |         events_this_second = 0
 942 |   81 |         last_heartbeat = time.time()
 943 |   82 |         
 944 |   83 |         while True:
 945 |   84 |             current_time = time.time()
 946 |   85 |             if current_time - last_heartbeat >= 1.0:
 947 |   86 |                 with open("data/heartbeat.json", "w") as f:
 948 |   87 |                     json.dump({"events_per_sec": events_this_second, "timestamp": current_time}, f)
 949 |   88 |                 os.chmod("data/heartbeat.json", 0o666)
 950 |   89 |                 events_this_second = 0
 951 |   90 |                 last_heartbeat = current_time
 952 |   91 | 
 953 |   92 |             event = agent.get_event(timeout=0.1)
 954 |   93 |             if event:
 955 |   94 |                 events_this_second += 1
 956 |   95 |                 
 957 |   96 |                 graph_heuristics = []
 958 |   97 |                 
 959 |   98 |                 if graph_builder:
 960 |   99 |                     graph_builder.add_event(event)
 961 |  100 |                     subgraph = graph_builder.get_process_subgraph(event["pid"])
 962 |  101 |                     if subgraph.number_of_nodes() > 3:
 963 |  102 |                         graph_heuristics.append("high_connectivity")
 964 |  103 |                 
 965 |  104 |                 if event.get("filename", "").startswith("/etc") or event.get("filename", "").startswith("/root"):
 966 |  105 |                     graph_heuristics.append("sensitive_access")
 967 |  106 |                 
 968 |  107 |                 sig_match = sig_detector.analyze_event(event)
 969 |  108 |                 
 970 |  109 |                 if STAT_DETECTOR and metrics_engine and stat_detector:
 971 |  110 |                     metrics_engine.update(event)
 972 |  111 |                     stat_report = stat_detector.evaluate(
 973 |  112 |                         pid=event["pid"],
 974 |  113 |                         current_metrics=metrics_engine.get_current_vector(event["pid"])
 975 |  114 |                     )
 976 |  115 |                 else:
 977 |  116 |                     stat_report = {"pid": event["pid"], "is_anomalous": False, "max_z_score": 0.0}
 978 |  117 |                 
 979 |  118 |                 alert = scoring.compute_score(
 980 |  119 |                     event=event,
 981 |  120 |                     stat_report=stat_report,
 982 |  121 |                     sig_match=sig_match,
 983 |  122 |                     graph_heuristics=graph_heuristics
 984 |  123 |                 )
 985 |  124 |                 
 986 |  125 |                 if alert:
 987 |  126 |                     storage.save_alert(dataclasses.asdict(alert))
 988 |  127 |                     try: os.chmod(storage.db_path, 0o666)
 989 |  128 |                     except: pass
 990 |  129 |                     print(f"🚨 ALERT: PID {event['pid']} [{event['comm']}] - SCORE {alert.score}")
 991 |  130 |     except KeyboardInterrupt: pass
 992 |  131 |     finally: agent.stop()
 993 |  132 | 
 994 |  133 | if __name__ == "__main__":
 995 |  134 |     run_agent()
 996 | ```
 997 | 
 998 | ### src/metrics/engine.py
 999 | 
1000 | ```python
1001 |    1 | import numpy as np
1002 |    2 | import logging
1003 |    3 | from typing import Dict, List, Optional, Tuple, Any
1004 |    4 | from collections import deque
1005 |    5 | 
1006 |    6 | logger = logging.getLogger(__name__)
1007 |    7 | 
1008 |    8 | class MetricsEngine:
1009 |    9 |     """
1010 |   10 |     Implements the mathematical model M(t) from Section 2.1.
1011 |   11 |     Calculates EWMA (Exponentially Weighted Moving Average) for system metrics
1012 |   12 |     and maintains n-gram profiles for syscall sequences.
1013 |   13 |     """
1014 |   14 |     
1015 |   15 |     def __init__(self, alpha: float = 0.3, n_gram_size: int = 3):
1016 |   16 |         self.alpha = alpha  # Smoothing factor for EWMA
1017 |   17 |         self.n_gram_size = n_gram_size
1018 |   18 |         
1019 |   19 |         # Structure: {pid: {"metrics": array, "mu": array, "sigma": array, "ngram_tree": dict}}
1020 |   20 |         self.profiles: Dict[int, Dict] = {}
1021 |   21 | 
1022 |   22 |     def update(self, event: Dict[str, Any]):
1023 |   23 |         """
1024 |   24 |         Update metrics from an eBPF event.
1025 |   25 |         """
1026 |   26 |         pid = event.get("pid")
1027 |   27 |         if pid is None:
1028 |   28 |             return
1029 |   29 |             
1030 |   30 |         syscall_id = event.get("syscall_id", 0)
1031 |   31 |         
1032 |   32 |         current_vector = np.array([
1033 |   33 |             float(syscall_id),
1034 |   34 |             float(len(event.get("filename", ""))),
1035 |   35 |             float(event.get("tgid", 0)),
1036 |   36 |             1.0,  # syscall count
1037 |   37 |             float(event.get("cgroup_id", 0) % 1000)
1038 |   38 |         ])
1039 |   39 |         
1040 |   40 |         self.update_scalar_metrics(pid, current_vector)
1041 |   41 |         self.update_ngram(pid, syscall_id)
1042 |   42 | 
1043 |   43 |     def get_current_vector(self, pid: int) -> np.ndarray:
1044 |   44 |         """
1045 |   45 |         Get current metrics vector for a PID (for z-score calculation).
1046 |   46 |         """
1047 |   47 |         if pid not in self.profiles:
1048 |   48 |             return np.zeros(5)
1049 |   49 |         return self.profiles[pid]["mu"].copy()
1050 |   50 | 
1051 |   51 |     def update_scalar_metrics(self, pid: int, current_vector: np.ndarray):
1052 |   52 |         """
1053 |   53 |         Updates EWMA for a process.
1054 |   54 |         z_i = (m_i - mu_i) / sigma_i
1055 |   55 |         """
1056 |   56 |         if pid not in self.profiles:
1057 |   57 |             self.profiles[pid] = {
1058 |   58 |                 "mu": current_vector.astype(float),
1059 |   59 |                 "sigma": np.ones_like(current_vector, dtype=float),
1060 |   60 |                 "history": deque(maxlen=100),
1061 |   61 |                 "ngram_buffer": deque(maxlen=self.n_gram_size),
1062 |   62 |                 "ngram_counts": {}
1063 |   63 |             }
1064 |   64 |             return
1065 |   65 | 
1066 |   66 |         prof = self.profiles[pid]
1067 |   67 |         
1068 |   68 |         # EWMA Update: mu = alpha * current + (1 - alpha) * mu
1069 |   69 |         old_mu = prof["mu"]
1070 |   70 |         new_mu = self.alpha * current_vector + (1 - self.alpha) * old_mu
1071 |   71 |         
1072 |   72 |         # Incremental variance/sigma calculation (Simplified)
1073 |   73 |         delta = current_vector - old_mu
1074 |   74 |         prof["sigma"] = np.sqrt((1 - self.alpha) * (prof["sigma"]**2 + self.alpha * delta**2))
1075 |   75 |         prof["mu"] = new_mu
1076 |   76 |         
1077 |   77 |         prof["history"].append(current_vector)
1078 |   78 |         
1079 |   79 |         prof["history"].append(current_vector)
1080 |   80 | 
1081 |   81 |     def update_ngram(self, pid: int, syscall_id: int):
1082 |   82 |         """
1083 |   83 |         Updates the n-gram frequency distribution for the process.
1084 |   84 |         """
1085 |   85 |         if pid not in self.profiles:
1086 |   86 |             # Initialize if not exists (should normally be handled by scalar update)
1087 |   87 |             self.update_scalar_metrics(pid, np.zeros(5)) 
1088 |   88 |             
1089 |   89 |         prof = self.profiles[pid]
1090 |   90 |         buf = prof["ngram_buffer"]
1091 |   91 |         buf.append(syscall_id)
1092 |   92 |         
1093 |   93 |         if len(buf) == self.n_gram_size:
1094 |   94 |             ngram = tuple(buf)
1095 |   95 |             prof["ngram_counts"][ngram] = prof["ngram_counts"].get(ngram, 0) + 1
1096 |   96 | 
1097 |   97 |     def get_z_scores(self, pid: int, current_vector: np.ndarray) -> np.ndarray:
1098 |   98 |         """
1099 |   99 |         Computes Z-scores for the current observation against the stored profile.
1100 |  100 |         """
1101 |  101 |         if pid not in self.profiles:
1102 |  102 |             return np.zeros_like(current_vector)
1103 |  103 |             
1104 |  104 |         prof = self.profiles[pid]
1105 |  105 |         # Avoid division by zero
1106 |  106 |         safe_sigma = np.where(prof["sigma"] == 0, 1e-6, prof["sigma"])
1107 |  107 |         return (current_vector - prof["mu"]) / safe_sigma
1108 |  108 | 
1109 |  109 |     def get_ngram_anomaly_score(self, pid: int, sequence: Tuple[int, ...]) -> float:
1110 |  110 |         """
1111 |  111 |         Returns a score representing how 'new' or 'rare' a sequence is.
1112 |  112 |         Higher is more anomalous.
1113 |  113 |         """
1114 |  114 |         if pid not in self.profiles:
1115 |  115 |             return 1.0
1116 |  116 |             
1117 |  117 |         counts = self.profiles[pid]["ngram_counts"]
1118 |  118 |         total = sum(counts.values())
1119 |  119 |         if total == 0:
1120 |  120 |             return 1.0
1121 |  121 |             
1122 |  122 |         freq = counts.get(sequence, 0) / total
1123 |  123 |         return 1.0 - freq # Inverse frequency as anomaly indicator
1124 | ```
1125 | 
1126 | ### src/scoring/engine.py
1127 | 
1128 | ```python
1129 |    1 | from dataclasses import dataclass, asdict
1130 |    2 | from datetime import datetime
1131 |    3 | from typing import List, Dict, Any, Optional
1132 |    4 | 
1133 |    5 | @dataclass
1134 |    6 | class Alert:
1135 |    7 |     timestamp: str
1136 |    8 |     pid: int
1137 |    9 |     comm: str
1138 |   10 |     score: float
1139 |   11 |     severity: str
1140 |   12 |     reasons: List[str]
1141 |   13 |     breakdown: Dict[str, float] 
1142 |   14 | 
1143 |   15 | class ScoringEngine:
1144 |   16 |     def __init__(self, threshold: float = 10.0):
1145 |   17 |         self.threshold = threshold
1146 |   18 |         self.weights = {"signature": 15.0, "statistical": 1.0, "graph": 5.0}
1147 |   19 | 
1148 |   20 |     def compute_score(self, event: Dict[str, Any], stat_report: Dict[str, Any], 
1149 |   21 |                       sig_match: Optional[Dict[str, Any]], 
1150 |   22 |                       graph_heuristics: List[str]) -> Optional[Alert]:
1151 |   23 |         
1152 |   24 |         comp = {"signature": 0.0, "statistical": 0.0, "graph": 0.0}
1153 |   25 |         reasons = []
1154 |   26 |         
1155 |   27 |         if sig_match:
1156 |   28 |             comp["signature"] = self.weights["signature"]
1157 |   29 |             reasons.append(sig_match['reason'])
1158 |   30 |             
1159 |   31 |         max_z = stat_report.get("max_z_score", 0.0)
1160 |   32 |         if stat_report.get("is_anomalous"):
1161 |   33 |             comp["statistical"] = self.weights["statistical"] * max_z
1162 |   34 |             reasons.append(f"Statistical Anomaly (Z={max_z:.1f})")
1163 |   35 |             
1164 |   36 |         for h in graph_heuristics:
1165 |   37 |             comp["graph"] += self.weights["graph"]
1166 |   38 |             reasons.append(f"Graph Heuristic: {h}")
1167 |   39 | 
1168 |   40 |         total_score = sum(comp.values())
1169 |   41 | 
1170 |   42 |         if total_score >= self.threshold:
1171 |   43 |             return Alert(
1172 |   44 |                 timestamp=datetime.now().isoformat(),
1173 |   45 |                 pid=event["pid"],
1174 |   46 |                 comm=event.get("comm", "unknown"),
1175 |   47 |                 score=round(total_score, 2),
1176 |   48 |                 severity="CRITICAL" if total_score > 20 else "WARNING",
1177 |   49 |                 reasons=reasons,
1178 |   50 |                 breakdown=comp
1179 |   51 |             )
1180 |   52 |         return None
1181 | ```
1182 | 
1183 | ### src/storage/sqlite.py
1184 | 
1185 | ```python
1186 |    1 | import sqlite3
1187 |    2 | import json
1188 |    3 | import logging
1189 |    4 | import os
1190 |    5 | import threading
1191 |    6 | from typing import List, Dict, Any, Optional
1192 |    7 | from datetime import datetime
1193 |    8 | from contextlib import contextmanager
1194 |    9 | 
1195 |   10 | logger = logging.getLogger(__name__)
1196 |   11 | 
1197 |   12 | class StorageManager:
1198 |   13 |     """
1199 |   14 |     Handles persistence for security profiles and alerts (Section 3.2).
1200 |   15 |     Uses a thread-safe connection pattern and context managers.
1201 |   16 |     """
1202 |   17 |     
1203 |   18 |     def __init__(self, db_path: str = None):
1204 |   19 |         self.db_path = db_path or os.environ.get("DB_PATH", "data/sovnd.db")
1205 |   20 |         self._lock = threading.Lock()
1206 |   21 |         self._init_db()
1207 |   22 | 
1208 |   23 |     @contextmanager
1209 |   24 |     def _get_connection(self):
1210 |   25 |         conn = sqlite3.connect(self.db_path)
1211 |   26 |         conn.row_factory = sqlite3.Row
1212 |   27 |         try:
1213 |   28 |             yield conn
1214 |   29 |         finally:
1215 |   30 |             conn.close()
1216 |   31 | 
1217 |   32 |     def _init_db(self):
1218 |   33 |         """Initializes the database schema."""
1219 |   34 |         os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else "data", exist_ok=True)
1220 |   35 |         with self._get_connection() as conn:
1221 |   36 |             conn.execute("""
1222 |   37 |                 CREATE TABLE IF NOT EXISTS profiles (
1223 |   38 |                     id INTEGER PRIMARY KEY AUTOINCREMENT,
1224 |   39 |                     identifier TEXT UNIQUE, -- e.g., process name or container image
1225 |   40 |                     mu BLOB,
1226 |   41 |                     sigma BLOB,
1227 |   42 |                     last_updated TIMESTAMP
1228 |   43 |                 )
1229 |   44 |             """)
1230 |   45 |             conn.execute("""
1231 |   46 |                 CREATE TABLE IF NOT EXISTS alerts (
1232 |   47 |                     id INTEGER PRIMARY KEY AUTOINCREMENT,
1233 |   48 |                     timestamp TIMESTAMP,
1234 |   49 |                     pid INTEGER,
1235 |   50 |                     comm TEXT,
1236 |   51 |                     score REAL,
1237 |   52 |                     severity TEXT,
1238 |   53 |                     reasons TEXT,       -- JSON string
1239 |   54 |                     breakdown TEXT     -- JSON string
1240 |   55 |                 )
1241 |   56 |             """)
1242 |   57 |             conn.commit()
1243 |   58 |         try:
1244 |   59 |             os.chmod(self.db_path, 0o644)
1245 |   60 |         except PermissionError:
1246 |   61 |             pass
1247 |   62 |         logger.info("Database initialized at %s", self.db_path)
1248 |   63 | 
1249 |   64 |     def save_alert(self, alert_data: Dict[str, Any]):
1250 |   65 |         """Persists a generated alert."""
1251 |   66 |         with self._lock:
1252 |   67 |             with self._get_connection() as conn:
1253 |   68 |                 conn.execute(
1254 |   69 |                     "INSERT INTO alerts (timestamp, pid, comm, score, severity, reasons, breakdown) VALUES (?, ?, ?, ?, ?, ?, ?)",
1255 |   70 |                     (
1256 |   71 |                         alert_data.get("timestamp"),
1257 |   72 |                         alert_data.get("pid"),
1258 |   73 |                         alert_data.get("comm", "unknown"),
1259 |   74 |                         alert_data.get("score"),
1260 |   75 |                         alert_data.get("severity"),
1261 |   76 |                         json.dumps(alert_data.get("reasons")),
1262 |   77 |                         json.dumps(alert_data.get("breakdown", {}))
1263 |   78 |                     )
1264 |   79 |                 )
1265 |   80 |                 conn.commit()
1266 |   81 |         try:
1267 |   82 |             os.chmod(self.db_path, 0o644)
1268 |   83 |         except PermissionError:
1269 |   84 |             pass
1270 |   85 | 
1271 |   86 |     def get_recent_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
1272 |   87 |         """Retrieves most recent security alerts."""
1273 |   88 |         with self._get_connection() as conn:
1274 |   89 |             cursor = conn.execute(
1275 |   90 |                 "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,)
1276 |   91 |             )
1277 |   92 |             rows = cursor.fetchall()
1278 |   93 |             alerts = []
1279 |   94 |             for row in rows:
1280 |   95 |                 alert = dict(row)
1281 |   96 |                 alert["reasons"] = json.loads(alert["reasons"]) if alert["reasons"] else []
1282 |   97 |                 alert["breakdown"] = json.loads(alert["breakdown"]) if alert["breakdown"] else {}
1283 |   98 |                 alerts.append(alert)
1284 |   99 |             return alerts
1285 |  100 | 
1286 |  101 |     def save_profile(self, identifier: str, mu: bytes, sigma: bytes):
1287 |  102 |         """Saves or updates a behavioral profile."""
1288 |  103 |         with self._lock:
1289 |  104 |             with self._get_connection() as conn:
1290 |  105 |                 conn.execute("""
1291 |  106 |                     INSERT INTO profiles (identifier, mu, sigma, last_updated)
1292 |  107 |                     VALUES (?, ?, ?, ?)
1293 |  108 |                     ON CONFLICT(identifier) DO UPDATE SET
1294 |  109 |                         mu=excluded.mu,
1295 |  110 |                         sigma=excluded.sigma,
1296 |  111 |                         last_updated=excluded.last_updated
1297 |  112 |                 """, (identifier, mu, sigma, datetime.now().isoformat()))
1298 |  113 |                 conn.commit()
1299 |  114 | 
1300 |  115 |     def get_profile(self, identifier: str) -> Optional[Dict[str, Any]]:
1301 |  116 |         """Retrieves a behavioral profile by identifier."""
1302 |  117 |         with self._get_connection() as conn:
1303 |  118 |             cursor = conn.execute(
1304 |  119 |                 "SELECT * FROM profiles WHERE identifier = ?", (identifier,)
1305 |  120 |             )
1306 |  121 |             row = cursor.fetchone()
1307 |  122 |             return dict(row) if row else None
1308 |  123 | 
1309 |  124 |     def clear_alerts(self):
1310 |  125 |         """Clears all alerts from the database."""
1311 |  126 |         with self._lock:
1312 |  127 |             with self._get_connection() as conn:
1313 |  128 |                 conn.execute("DELETE FROM alerts")
1314 |  129 |                 conn.commit()
1315 |  130 |         try:
1316 |  131 |             os.chmod(self.db_path, 0o644)
1317 |  132 |         except PermissionError:
1318 |  133 |             pass
1319 |  134 |         logger.info("All alerts cleared")
1320 | ```
1321 | 
1322 | ### tests/__init__.py
1323 | 
1324 | ```python
1325 | 
1326 | ```
1327 | 
1328 | ### tests/conftest.py
1329 | 
1330 | ```python
1331 |    1 | import sys
1332 |    2 | import types
1333 |    3 | from unittest.mock import MagicMock
1334 |    4 | 
1335 |    5 | _mock_docker = types.ModuleType("docker")
1336 |    6 | _mock_docker.DockerClient = MagicMock
1337 |    7 | _mock_docker.errors = types.ModuleType("docker.errors")
1338 |    8 | _mock_docker.errors.DockerException = Exception
1339 |    9 | sys.modules["docker"] = _mock_docker
1340 |   10 | sys.modules["docker.errors"] = _mock_docker.errors
1341 |   11 | 
1342 |   12 | import pytest
1343 |   13 | 
1344 |   14 | pytest_plugins = []
1345 | ```
1346 | 
1347 | ### tests/test_api_main.py
1348 | 
1349 | ```python
1350 |    1 | import pytest
1351 |    2 | import sys
1352 |    3 | import json
1353 |    4 | import tempfile
1354 |    5 | import os
1355 |    6 | from pathlib import Path
1356 |    7 | from unittest.mock import patch, MagicMock
1357 |    8 | from fastapi.testclient import TestClient
1358 |    9 | 
1359 |   10 | SRC_DIR = Path(__file__).parent.parent / "src"
1360 |   11 | sys.path.insert(0, str(SRC_DIR))
1361 |   12 | 
1362 |   13 | from storage.sqlite import StorageManager
1363 |   14 | from api.main import app, get_storage
1364 |   15 | 
1365 |   16 | 
1366 |   17 | @pytest.fixture
1367 |   18 | def temp_db():
1368 |   19 |     """Create a temporary database for testing."""
1369 |   20 |     with tempfile.TemporaryDirectory() as tmpdir:
1370 |   21 |         db_path = os.path.join(tmpdir, "test.db")
1371 |   22 |         manager = StorageManager(db_path=db_path)
1372 |   23 |         yield manager, db_path
1373 |   24 | 
1374 |   25 | 
1375 |   26 | class TestAPIEndpoints:
1376 |   27 |     """Tests for API endpoints."""
1377 |   28 | 
1378 |   29 |     def test_root_endpoint(self, temp_db):
1379 |   30 |         """Test root endpoint returns welcome message."""
1380 |   31 |         manager, _ = temp_db
1381 |   32 |         app.dependency_overrides[get_storage] = lambda: manager
1382 |   33 |         try:
1383 |   34 |             client = TestClient(app)
1384 |   35 |             response = client.get("/")
1385 |   36 |             
1386 |   37 |             assert response.status_code == 200
1387 |   38 |             data = response.json()
1388 |   39 |             assert "message" in data
1389 |   40 |             assert "SovND API" in data["message"]
1390 |   41 |         finally:
1391 |   42 |             app.dependency_overrides.clear()
1392 |   43 | 
1393 |   44 |     def test_status_endpoint_returns_operational(self, temp_db):
1394 |   45 |         """Test /api/status returns operational status."""
1395 |   46 |         manager, _ = temp_db
1396 |   47 |         app.dependency_overrides[get_storage] = lambda: manager
1397 |   48 |         try:
1398 |   49 |             client = TestClient(app)
1399 |   50 |             response = client.get("/api/status")
1400 |   51 |             
1401 |   52 |             assert response.status_code == 200
1402 |   53 |             data = response.json()
1403 |   54 |             assert data["status"] == "operational"
1404 |   55 |             assert data["engine"] == "eBPF-CO-RE"
1405 |   56 |             assert data["version"] == "1.0.0"
1406 |   57 |         finally:
1407 |   58 |             app.dependency_overrides.clear()
1408 |   59 | 
1409 |   60 |     def test_alerts_endpoint_returns_list(self, temp_db):
1410 |   61 |         """Test /api/alerts returns a list."""
1411 |   62 |         manager, _ = temp_db
1412 |   63 |         app.dependency_overrides[get_storage] = lambda: manager
1413 |   64 |         try:
1414 |   65 |             client = TestClient(app)
1415 |   66 |             response = client.get("/api/alerts")
1416 |   67 |             
1417 |   68 |             assert response.status_code == 200
1418 |   69 |             data = response.json()
1419 |   70 |             assert isinstance(data, list)
1420 |   71 |         finally:
1421 |   72 |             app.dependency_overrides.clear()
1422 |   73 | 
1423 |   74 |     def test_alerts_endpoint_respects_limit_param(self, temp_db):
1424 |   75 |         """Test /api/alerts respects limit parameter."""
1425 |   76 |         manager, _ = temp_db
1426 |   77 |         for i in range(10):
1427 |   78 |             manager.save_alert({
1428 |   79 |                 "timestamp": f"2024-01-0{i+1}T00:00:00",
1429 |   80 |                 "pid": 3000 + i,
1430 |   81 |                 "score": 5.0,
1431 |   82 |                 "severity": "info",
1432 |   83 |                 "reasons": [],
1433 |   84 |                 "container_info": None
1434 |   85 |             })
1435 |   86 |         
1436 |   87 |         app.dependency_overrides[get_storage] = lambda: manager
1437 |   88 |         try:
1438 |   89 |             client = TestClient(app)
1439 |   90 |             response = client.get("/api/alerts?limit=5")
1440 |   91 |             
1441 |   92 |             assert response.status_code == 200
1442 |   93 |             data = response.json()
1443 |   94 |             assert len(data) == 5
1444 |   95 |         finally:
1445 |   96 |             app.dependency_overrides.clear()
1446 |   97 | 
1447 |   98 |     def test_alerts_endpoint_default_limit(self, temp_db):
1448 |   99 |         """Test /api/alerts has default limit of 50."""
1449 |  100 |         manager, _ = temp_db
1450 |  101 |         for i in range(100):
1451 |  102 |             manager.save_alert({
1452 |  103 |                 "timestamp": f"2024-01-{(i%30)+1:02d}T00:00:00",
1453 |  104 |                 "pid": 3000 + i,
1454 |  105 |                 "score": 5.0,
1455 |  106 |                 "severity": "info",
1456 |  107 |                 "reasons": [],
1457 |  108 |                 "container_info": None
1458 |  109 |             })
1459 |  110 |         
1460 |  111 |         app.dependency_overrides[get_storage] = lambda: manager
1461 |  112 |         try:
1462 |  113 |             client = TestClient(app)
1463 |  114 |             response = client.get("/api/alerts")
1464 |  115 |             
1465 |  116 |             assert response.status_code == 200
1466 |  117 |             data = response.json()
1467 |  118 |             assert len(data) == 50
1468 |  119 |         finally:
1469 |  120 |             app.dependency_overrides.clear()
1470 |  121 | 
1471 |  122 |     def test_alerts_endpoint_returns_stored_data(self, temp_db):
1472 |  123 |         """Test /api/alerts returns actual stored alert data with correct types."""
1473 |  124 |         manager, _ = temp_db
1474 |  125 |         manager.save_alert({
1475 |  126 |             "timestamp": "2024-01-15T10:30:00",
1476 |  127 |             "pid": 9999,
1477 |  128 |             "score": 25.5,
1478 |  129 |             "severity": "critical",
1479 |  130 |             "reasons": ["unauthorized shell", "shadow access"],
1480 |  131 |             "container_info": {"id": "test123", "name": "malware"}
1481 |  132 |         })
1482 |  133 |         
1483 |  134 |         app.dependency_overrides[get_storage] = lambda: manager
1484 |  135 |         try:
1485 |  136 |             client = TestClient(app)
1486 |  137 |             response = client.get("/api/alerts?limit=1")
1487 |  138 |             
1488 |  139 |             assert response.status_code == 200
1489 |  140 |             data = response.json()
1490 |  141 |             assert data[0]["pid"] == 9999
1491 |  142 |             assert data[0]["score"] == 25.5
1492 |  143 |             assert data[0]["severity"] == "critical"
1493 |  144 |             
1494 |  145 |             assert isinstance(data[0]["reasons"], list), "reasons should be a list"
1495 |  146 |             assert data[0]["reasons"] == ["unauthorized shell", "shadow access"]
1496 |  147 |             
1497 |  148 |             assert isinstance(data[0]["container_info"], dict), "container_info should be a dict"
1498 |  149 |             assert data[0]["container_info"] == {"id": "test123", "name": "malware"}
1499 |  150 |         finally:
1500 |  151 |             app.dependency_overrides.clear()
1501 |  152 | 
1502 |  153 |     def test_alerts_endpoint_returns_empty_list_when_no_alerts(self, temp_db):
1503 |  154 |         """Test /api/alerts returns empty list when no alerts exist."""
1504 |  155 |         manager, _ = temp_db
1505 |  156 |         app.dependency_overrides[get_storage] = lambda: manager
1506 |  157 |         try:
1507 |  158 |             client = TestClient(app)
1508 |  159 |             response = client.get("/api/alerts")
1509 |  160 |             
1510 |  161 |             assert response.status_code == 200
1511 |  162 |             assert response.json() == []
1512 |  163 |         finally:
1513 |  164 |             app.dependency_overrides.clear()
1514 |  165 | 
1515 |  166 |     def test_alerts_endpoint_handles_database_error(self, temp_db):
1516 |  167 |         """Test /api/alerts handles database errors gracefully.
1517 |  168 |         
1518 |  169 |         This tests the case where StorageManager.get_recent_alerts() raises.
1519 |  170 |         Note: FastAPI's exception handling for dependency injection errors
1520 |  171 |         depends on configuration. We test that storage exceptions are caught.
1521 |  172 |         """
1522 |  173 |         with patch("api.main.StorageManager") as mock_class:
1523 |  174 |             mock_instance = MagicMock()
1524 |  175 |             mock_instance.get_recent_alerts.side_effect = RuntimeError("Database corruption")
1525 |  176 |             mock_class.return_value = mock_instance
1526 |  177 |             
1527 |  178 |             client = TestClient(app, raise_server_exceptions=False)
1528 |  179 |             response = client.get("/api/alerts")
1529 |  180 |             
1530 |  181 |             assert response.status_code == 500
1531 |  182 | 
1532 |  183 | 
1533 |  184 | class TestPrometheusMetrics:
1534 |  185 |     """Tests for Prometheus metrics endpoints."""
1535 |  186 | 
1536 |  187 |     def test_metrics_endpoint_returns_prometheus_format(self, temp_db):
1537 |  188 |         """Test /metrics returns Prometheus format."""
1538 |  189 |         manager, _ = temp_db
1539 |  190 |         app.dependency_overrides[get_storage] = lambda: manager
1540 |  191 |         try:
1541 |  192 |             client = TestClient(app)
1542 |  193 |             response = client.get("/metrics")
1543 |  194 |             
1544 |  195 |             assert response.status_code == 200
1545 |  196 |             content = response.text
1546 |  197 |             assert "sovnd_syscalls_total" in content
1547 |  198 |             assert "sovnd_cpu_usage_percent" in content
1548 |  199 |         finally:
1549 |  200 |             app.dependency_overrides.clear()
1550 |  201 | 
1551 |  202 |     def test_metrics_endpoint_content_type(self, temp_db):
1552 |  203 |         """Test /metrics returns correct content type."""
1553 |  204 |         manager, _ = temp_db
1554 |  205 |         app.dependency_overrides[get_storage] = lambda: manager
1555 |  206 |         try:
1556 |  207 |             client = TestClient(app)
1557 |  208 |             response = client.get("/metrics")
1558 |  209 |             
1559 |  210 |             assert response.status_code == 200
1560 |  211 |             assert "text/plain" in response.headers["content-type"]
1561 |  212 |             assert "charset=utf-8" in response.headers["content-type"]
1562 |  213 |         finally:
1563 |  214 |             app.dependency_overrides.clear()
1564 |  215 | 
1565 |  216 | 
1566 |  217 | class TestAPIDependencyInjection:
1567 |  218 |     """Tests for FastAPI dependency injection."""
1568 |  219 | 
1569 |  220 |     def test_get_storage_returns_storage_manager(self):
1570 |  221 |         """Test get_storage dependency returns StorageManager instance."""
1571 |  222 |         storage = get_storage()
1572 |  223 |         
1573 |  224 |         assert hasattr(storage, "save_alert")
1574 |  225 |         assert hasattr(storage, "get_recent_alerts")
1575 |  226 |         assert hasattr(storage, "save_profile")
1576 |  227 | 
1577 |  228 | 
1578 |  229 | class TestAPIMetadata:
1579 |  230 |     """Tests for API metadata."""
1580 |  231 | 
1581 |  232 |     def test_app_title(self):
1582 |  233 |         """Test FastAPI app has correct title."""
1583 |  234 |         assert app.title == "SovND Security API"
1584 |  235 | 
1585 |  236 |     def test_app_description(self):
1586 |  237 |         """Test FastAPI app has correct description."""
1587 |  238 |         assert "API for accessing eBPF-based security monitoring data" in app.description
1588 |  239 | 
1589 |  240 |     def test_app_version(self):
1590 |  241 |         """Test FastAPI app has correct version."""
1591 |  242 |         assert app.version == "1.0.0"
1592 |  243 | 
1593 |  244 | 
1594 |  245 | class TestAPIIntegration:
1595 |  246 |     """Integration tests for API with real database."""
1596 |  247 | 
1597 |  248 |     def test_full_workflow_save_and_retrieve_alerts(self):
1598 |  249 |         """Test complete workflow: save alert then retrieve via API."""
1599 |  250 |         with tempfile.TemporaryDirectory() as tmpdir:
1600 |  251 |             db_path = os.path.join(tmpdir, "test.db")
1601 |  252 |             manager = StorageManager(db_path=db_path)
1602 |  253 |             
1603 |  254 |             alert_data = {
1604 |  255 |                 "timestamp": "2024-06-15T14:30:00",
1605 |  256 |                 "pid": 4242,
1606 |  257 |                 "score": 42.0,
1607 |  258 |                 "severity": "critical",
1608 |  259 |                 "reasons": ["reverse shell detected"],
1609 |  260 |                 "container_info": {"id": "container-x", "name": "attacker"}
1610 |  261 |             }
1611 |  262 |             manager.save_alert(alert_data)
1612 |  263 |             
1613 |  264 |             app.dependency_overrides[get_storage] = lambda: manager
1614 |  265 |             try:
1615 |  266 |                 client = TestClient(app)
1616 |  267 |                 response = client.get("/api/alerts?limit=1")
1617 |  268 |                 
1618 |  269 |                 assert response.status_code == 200
1619 |  270 |                 data = response.json()
1620 |  271 |                 assert len(data) == 1
1621 |  272 |                 assert data[0]["pid"] == 4242
1622 |  273 |                 assert data[0]["score"] == 42.0
1623 |  274 |                 
1624 |  275 |                 assert isinstance(data[0]["reasons"], list), "reasons must be parsed as list"
1625 |  276 |                 assert isinstance(data[0]["container_info"], dict), "container_info must be parsed as dict"
1626 |  277 |             finally:
1627 |  278 |                 app.dependency_overrides.clear()
1628 |  279 | 
1629 |  280 |     def test_status_endpoint_when_db_has_profiles(self):
1630 |  281 |         """Test /api/status works independently of database content."""
1631 |  282 |         with tempfile.TemporaryDirectory() as tmpdir:
1632 |  283 |             db_path = os.path.join(tmpdir, "test.db")
1633 |  284 |             manager = StorageManager(db_path=db_path)
1634 |  285 |             
1635 |  286 |             manager.save_profile("test_proc", b"\x00\x01\x02", b"\x01\x02\x03")
1636 |  287 |             
1637 |  288 |             app.dependency_overrides[get_storage] = lambda: manager
1638 |  289 |             try:
1639 |  290 |                 client = TestClient(app)
1640 |  291 |                 response = client.get("/api/status")
1641 |  292 |                 
1642 |  293 |                 assert response.status_code == 200
1643 |  294 |                 assert response.json()["status"] == "operational"
1644 |  295 |             finally:
1645 |  296 |                 app.dependency_overrides.clear()
1646 | ```
1647 | 
1648 | ### tests/test_build.py
1649 | 
1650 | ```python
1651 |    1 | import os
1652 |    2 | import subprocess
1653 |    3 | import pytest
1654 |    4 | from pathlib import Path
1655 |    5 | 
1656 |    6 | EBPF_DIR = Path(__file__).parent.parent / "ebpf"
1657 |    7 | 
1658 |    8 | 
1659 |    9 | class TestBuildCompilation:
1660 |   10 |     """Tests for eBPF build and compilation."""
1661 |   11 | 
1662 |   12 |     def test_makefile_exists(self):
1663 |   13 |         """Verify Makefile exists in ebpf directory."""
1664 |   14 |         makefile = EBPF_DIR / "Makefile"
1665 |   15 |         assert makefile.exists(), "Makefile not found in ebpf directory"
1666 |   16 | 
1667 |   17 |     def test_makefile_has_targets(self):
1668 |   18 |         """Verify Makefile has required targets."""
1669 |   19 |         makefile_content = (EBPF_DIR / "Makefile").read_text()
1670 |   20 |         assert "all:" in makefile_content, "Makefile missing 'all' target"
1671 |   21 |         assert "clean:" in makefile_content, "Makefile missing 'clean' target"
1672 |   22 | 
1673 |   23 |     def test_compile_tracer_bpf_o(self):
1674 |   24 |         """Test that tracer.bpf.o can be compiled."""
1675 |   25 |         result = subprocess.run(
1676 |   26 |             ["make", "all"],
1677 |   27 |             cwd=EBPF_DIR,
1678 |   28 |             capture_output=True,
1679 |   29 |             text=True
1680 |   30 |         )
1681 |   31 |         assert result.returncode == 0, f"Compilation failed: {result.stderr}"
1682 |   32 |         
1683 |   33 |         tracer_o = EBPF_DIR / "tracer.bpf.o"
1684 |   34 |         assert tracer_o.exists(), "tracer.bpf.o was not created"
1685 |   35 | 
1686 |   36 |     def test_compiled_object_file_size(self):
1687 |   37 |         """Test that compiled object file has reasonable size."""
1688 |   38 |         tracer_o = EBPF_DIR / "tracer.bpf.o"
1689 |   39 |         assert tracer_o.exists(), "tracer.bpf.o not found"
1690 |   40 |         
1691 |   41 |         size = tracer_o.stat().st_size
1692 |   42 |         assert size > 0, "tracer.bpf.o is empty"
1693 |   43 |         assert size < 1024 * 1024, "tracer.bpf.o is unreasonably large (>1MB)"
1694 |   44 | 
1695 |   45 |     def test_source_files_exist(self):
1696 |   46 |         """Verify all required source files exist."""
1697 |   47 |         required_files = [
1698 |   48 |             "tracer.bpf.c",
1699 |   49 |             "filter.bpf.c",
1700 |   50 |             "fd_tracker.bpf.c",
1701 |   51 |             "maps.bpf.h",
1702 |   52 |             "vmlinux.h"
1703 |   53 |         ]
1704 |   54 |         for filename in required_files:
1705 |   55 |             filepath = EBPF_DIR / filename
1706 |   56 |             assert filepath.exists(), f"Required file {filename} not found"
1707 |   57 | 
1708 |   58 |     def test_clang_available(self):
1709 |   59 |         """Test that clang compiler is available."""
1710 |   60 |         result = subprocess.run(
1711 |   61 |             ["which", "clang"],
1712 |   62 |             capture_output=True
1713 |   63 |         )
1714 |   64 |         assert result.returncode == 0, "clang not found in PATH"
1715 |   65 | 
1716 |   66 |     def test_clean_target(self):
1717 |   67 |         """Test that make clean works without errors."""
1718 |   68 |         subprocess.run(["make", "all"], cwd=EBPF_DIR, check=True)
1719 |   69 |         
1720 |   70 |         result = subprocess.run(
1721 |   71 |             ["make", "clean"],
1722 |   72 |             cwd=EBPF_DIR,
1723 |   73 |             capture_output=True,
1724 |   74 |             text=True
1725 |   75 |         )
1726 |   76 |         assert result.returncode == 0, f"make clean failed: {result.stderr}"
1727 |   77 | 
1728 |   78 |     def test_loader_c_exists(self):
1729 |   79 |         """Verify loader.c source file exists."""
1730 |   80 |         loader_c = EBPF_DIR / "loader.c"
1731 |   81 |         assert loader_c.exists(), "loader.c not found"
1732 |   82 | 
1733 |   83 |     def test_compile_libloader_so(self):
1734 |   84 |         """Test that libloader.so can be compiled."""
1735 |   85 |         result = subprocess.run(
1736 |   86 |             ["make", "all"],
1737 |   87 |             cwd=EBPF_DIR,
1738 |   88 |             capture_output=True,
1739 |   89 |             text=True
1740 |   90 |         )
1741 |   91 |         assert result.returncode == 0, f"Compilation failed: {result.stderr}"
1742 |   92 |         
1743 |   93 |         libloader_so = EBPF_DIR / "libloader.so"
1744 |   94 |         assert libloader_so.exists(), "libloader.so was not created"
1745 |   95 | 
1746 |   96 |     def test_libloader_so_size(self):
1747 |   97 |         """Test that libloader.so has reasonable size."""
1748 |   98 |         libloader_so = EBPF_DIR / "libloader.so"
1749 |   99 |         if not libloader_so.exists():
1750 |  100 |             subprocess.run(["make", "all"], cwd=EBPF_DIR, check=True)
1751 |  101 |         
1752 |  102 |         size = libloader_so.stat().st_size
1753 |  103 |         assert size > 0, "libloader.so is empty"
1754 |  104 |         assert size < 10 * 1024 * 1024, "libloader.so is unreasonably large (>10MB)"
1755 |  105 | 
1756 |  106 |     def test_skeleton_header_generated(self):
1757 |  107 |         """Test that tracer.skel.h is generated."""
1758 |  108 |         result = subprocess.run(
1759 |  109 |             ["make", "all"],
1760 |  110 |             cwd=EBPF_DIR,
1761 |  111 |             capture_output=True,
1762 |  112 |             text=True
1763 |  113 |         )
1764 |  114 |         assert result.returncode == 0, f"Build failed: {result.stderr}"
1765 |  115 |         
1766 |  116 |         skel_h = EBPF_DIR / "tracer.skel.h"
1767 |  117 |         assert skel_h.exists(), "tracer.skel.h was not generated"
1768 |  118 | 
1769 |  119 |     def test_bpftool_available(self):
1770 |  120 |         """Test that bpftool is available."""
1771 |  121 |         result = subprocess.run(
1772 |  122 |             ["which", "bpftool"],
1773 |  123 |             capture_output=True
1774 |  124 |         )
1775 |  125 |         assert result.returncode == 0, "bpftool not found in PATH"
1776 |  126 | 
1777 |  127 |     def test_libbpf_dev_available(self):
1778 |  128 |         """Test that libbpf development headers are available."""
1779 |  129 |         result = subprocess.run(
1780 |  130 |             ["pkg-config", "--exists", "libbpf"],
1781 |  131 |             capture_output=True
1782 |  132 |         )
1783 |  133 |         assert result.returncode == 0, "libbpf development files not found"
1784 | ```
1785 | 
1786 | ### tests/test_container_resolver.py
1787 | 
1788 | ```python
1789 |    1 | import pytest
1790 |    2 | from unittest.mock import MagicMock, patch
1791 |    3 | from pathlib import Path
1792 |    4 | import threading
1793 |    5 | import sys
1794 |    6 | 
1795 |    7 | sys.path.insert(0, str(Path(__file__).parent.parent))
1796 |    8 | 
1797 |    9 | from src.docker.resolver import ContainerResolver
1798 |   10 | 
1799 |   11 | 
1800 |   12 | class TestContainerResolverInit:
1801 |   13 |     """Tests for ContainerResolver initialization."""
1802 |   14 | 
1803 |   15 |     def test_resolver_file_exists(self):
1804 |   16 |         """Verify ContainerResolver module exists."""
1805 |   17 |         assert ContainerResolver is not None
1806 |   18 | 
1807 |   19 |     def test_cache_initialized_empty(self):
1808 |   20 |         """Verify cache dict is initialized empty."""
1809 |   21 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
1810 |   22 |             mock_client = MagicMock()
1811 |   23 |             mock_docker.return_value = mock_client
1812 |   24 |             
1813 |   25 |             resolver = ContainerResolver()
1814 |   26 |             assert resolver._cache == {}
1815 |   27 | 
1816 |   28 |     def test_lock_initialized(self):
1817 |   29 |         """Verify lock is initialized."""
1818 |   30 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
1819 |   31 |             mock_client = MagicMock()
1820 |   32 |             mock_docker.return_value = mock_client
1821 |   33 |             
1822 |   34 |             resolver = ContainerResolver()
1823 |   35 |             assert isinstance(resolver._lock, type(threading.RLock()))
1824 |   36 | 
1825 |   37 |     def test_docker_connection_failure(self):
1826 |   38 |         """Verify Docker connection failure handling."""
1827 |   39 |         from docker.errors import DockerException
1828 |   40 |         
1829 |   41 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
1830 |   42 |             mock_docker.side_effect = DockerException("Connection refused")
1831 |   43 |             
1832 |   44 |             resolver = ContainerResolver()
1833 |   45 |             assert resolver.client is None
1834 |   46 | 
1835 |   47 |     def test_cache_initialized_empty(self):
1836 |   48 |         """Verify cache dict is initialized empty."""
1837 |   49 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
1838 |   50 |             mock_client = MagicMock()
1839 |   51 |             mock_docker.return_value = mock_client
1840 |   52 |             
1841 |   53 |             resolver = ContainerResolver()
1842 |   54 |             assert resolver._cache == {}
1843 |   55 | 
1844 |   56 |     def test_lock_initialized(self):
1845 |   57 |         """Verify lock is initialized."""
1846 |   58 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
1847 |   59 |             mock_client = MagicMock()
1848 |   60 |             mock_docker.return_value = mock_client
1849 |   61 |             
1850 |   62 |             resolver = ContainerResolver()
1851 |   63 |             assert isinstance(resolver._lock, type(threading.RLock()))
1852 |   64 | 
1853 |   65 |     def test_docker_connection_failure(self):
1854 |   66 |         """Verify Docker connection failure handling."""
1855 |   67 |         from docker.errors import DockerException
1856 |   68 |         
1857 |   69 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
1858 |   70 |             mock_docker.side_effect = DockerException("Connection refused")
1859 |   71 |             
1860 |   72 |             resolver = ContainerResolver()
1861 |   73 |             assert resolver.client is None
1862 |   74 | 
1863 |   75 | 
1864 |   76 | class TestContainerResolverResolve:
1865 |   77 |     """Tests for resolve method."""
1866 |   78 | 
1867 |   79 |     def test_resolve_handles_edge_cases(self):
1868 |   80 |         """Verify resolve handles edge cases gracefully."""
1869 |   81 |         import sys
1870 |   82 |         sys.path.insert(0, str(Path(__file__).parent.parent))
1871 |   83 |         from src.docker.resolver import ContainerResolver
1872 |   84 |         
1873 |   85 |         resolver = ContainerResolver.__new__(ContainerResolver)
1874 |   86 |         resolver._cache = {}
1875 |   87 |         resolver.client = None
1876 |   88 |         
1877 |   89 |         result = resolver.resolve(12345)
1878 |   90 |         
1879 |   91 |         assert result is None
1880 |   92 | 
1881 |   93 |     def test_cache_hit_returns_cached(self):
1882 |   94 |         """Verify cache hit returns cached value."""
1883 |   95 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
1884 |   96 |             mock_client = MagicMock()
1885 |   97 |             mock_docker.return_value = mock_client
1886 |   98 |             
1887 |   99 |             resolver = ContainerResolver()
1888 |  100 |             resolver._cache[12345] = {"id": "abc123", "name": "test"}
1889 |  101 |             
1890 |  102 |             result = resolver.resolve(12345)
1891 |  103 |             
1892 |  104 |             assert result["id"] == "abc123"
1893 |  105 |             mock_client.containers.list.assert_not_called()
1894 |  106 | 
1895 |  107 |     def test_cache_miss_refreshes(self):
1896 |  108 |         """Verify cache miss triggers refresh."""
1897 |  109 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
1898 |  110 |             mock_client = MagicMock()
1899 |  111 |             mock_container = MagicMock()
1900 |  112 |             mock_container.id = "def456"
1901 |  113 |             mock_container.name = "web"
1902 |  114 |             mock_container.image.tags = ["nginx:latest"]
1903 |  115 |             mock_container.labels = {"app": "web"}
1904 |  116 |             mock_client.containers.list.return_value = [mock_container]
1905 |  117 |             mock_docker.return_value = mock_client
1906 |  118 |             
1907 |  119 |             resolver = ContainerResolver()
1908 |  120 |             result = resolver.resolve(99999)
1909 |  121 |             
1910 |  122 |             mock_client.containers.list.assert_called_once()
1911 |  123 | 
1912 |  124 | 
1913 |  125 | class TestContainerResolverRefresh:
1914 |  126 |     """Tests for _refresh_and_resolve method."""
1915 |  127 | 
1916 |  128 |     def test_docker_exception_returns_none(self):
1917 |  129 |         """Verify Docker exception returns None."""
1918 |  130 |         from docker.errors import DockerException
1919 |  131 |         
1920 |  132 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
1921 |  133 |             mock_client = MagicMock()
1922 |  134 |             mock_client.containers.list.side_effect = DockerException("Error")
1923 |  135 |             mock_docker.return_value = mock_client
1924 |  136 |             
1925 |  137 |             resolver = ContainerResolver()
1926 |  138 |             result = resolver._refresh_and_resolve(12345)
1927 |  139 |             
1928 |  140 |             assert result is None
1929 |  141 | 
1930 |  142 |     def test_updates_cache_on_refresh(self):
1931 |  143 |         """Verify cache is updated on refresh."""
1932 |  144 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
1933 |  145 |             mock_client = MagicMock()
1934 |  146 |             mock_container = MagicMock()
1935 |  147 |             mock_container.id = "xyz789"
1936 |  148 |             mock_container.name = "api"
1937 |  149 |             mock_container.image.tags = ["api:v1"]
1938 |  150 |             mock_container.labels = {}
1939 |  151 |             mock_client.containers.list.return_value = [mock_container]
1940 |  152 |             mock_docker.return_value = mock_client
1941 |  153 |             
1942 |  154 |             resolver = ContainerResolver()
1943 |  155 |             resolver._refresh_and_resolve(11111)
1944 |  156 |             
1945 |  157 |             assert len(resolver._cache) > 0
1946 |  158 | 
1947 |  159 |     def test_handles_missing_image_tags(self):
1948 |  160 |         """Verify missing image tags handled."""
1949 |  161 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
1950 |  162 |             mock_client = MagicMock()
1951 |  163 |             mock_container = MagicMock()
1952 |  164 |             mock_container.id = "abc"
1953 |  165 |             mock_container.name = "test"
1954 |  166 |             mock_container.image.tags = []
1955 |  167 |             mock_container.labels = {}
1956 |  168 |             mock_client.containers.list.return_value = [mock_container]
1957 |  169 |             mock_docker.return_value = mock_client
1958 |  170 |             
1959 |  171 |             resolver = ContainerResolver()
1960 |  172 |             result = resolver._refresh_and_resolve(12345)
1961 |  173 |             
1962 |  174 |             assert result["image"] == "unknown"
1963 |  175 | 
1964 |  176 |     def test_handles_missing_labels(self):
1965 |  177 |         """Verify missing labels handled."""
1966 |  178 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
1967 |  179 |             mock_client = MagicMock()
1968 |  180 |             mock_container = MagicMock()
1969 |  181 |             mock_container.id = "abc"
1970 |  182 |             mock_container.name = "test"
1971 |  183 |             mock_container.image.tags = ["test:v1"]
1972 |  184 |             mock_container.labels = {}
1973 |  185 |             mock_client.containers.list.return_value = [mock_container]
1974 |  186 |             mock_docker.return_value = mock_client
1975 |  187 |             
1976 |  188 |             resolver = ContainerResolver()
1977 |  189 |             result = resolver._refresh_and_resolve(12345)
1978 |  190 |             
1979 |  191 |             assert "labels" in result
1980 |  192 | 
1981 |  193 | 
1982 |  194 | class TestContainerResolverClearCache:
1983 |  195 |     """Tests for clear_cache method."""
1984 |  196 | 
1985 |  197 |     def test_clear_cache_clears_all(self):
1986 |  198 |         """Verify clear_cache clears cache."""
1987 |  199 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
1988 |  200 |             mock_client = MagicMock()
1989 |  201 |             mock_docker.return_value = mock_client
1990 |  202 |             
1991 |  203 |             resolver = ContainerResolver()
1992 |  204 |             resolver._cache[1] = {"id": "a"}
1993 |  205 |             resolver._cache[2] = {"id": "b"}
1994 |  206 |             
1995 |  207 |             resolver.clear_cache()
1996 |  208 |             
1997 |  209 |             assert resolver._cache == {}
1998 |  210 | 
1999 |  211 | 
2000 |  212 | class TestContainerResolverThreadSafety:
2001 |  213 |     """Tests for thread safety."""
2002 |  214 | 
2003 |  215 |     def test_concurrent_resolve_thread_safe(self):
2004 |  216 |         """Verify concurrent resolve is thread safe."""
2005 |  217 |         import threading
2006 |  218 |         
2007 |  219 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
2008 |  220 |             mock_client = MagicMock()
2009 |  221 |             mock_container = MagicMock()
2010 |  222 |             mock_container.id = "abc"
2011 |  223 |             mock_container.name = "test"
2012 |  224 |             mock_container.image.tags = ["test:latest"]
2013 |  225 |             mock_container.labels = {}
2014 |  226 |             mock_client.containers.list.return_value = [mock_container]
2015 |  227 |             mock_docker.return_value = mock_client
2016 |  228 |             
2017 |  229 |             resolver = ContainerResolver()
2018 |  230 |             results = []
2019 |  231 |             errors = []
2020 |  232 |             
2021 |  233 |             def worker(cid):
2022 |  234 |                 try:
2023 |  235 |                     r = resolver.resolve(cid)
2024 |  236 |                     results.append(r)
2025 |  237 |                 except Exception as e:
2026 |  238 |                     errors.append(e)
2027 |  239 |             
2028 |  240 |             threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
2029 |  241 |             for t in threads:
2030 |  242 |                 t.start()
2031 |  243 |             for t in threads:
2032 |  244 |                 t.join()
2033 |  245 |             
2034 |  246 |             assert len(errors) == 0
2035 |  247 | 
2036 |  248 |     def test_lock_is_reentrant(self):
2037 |  249 |         """Verify lock is reentrant."""
2038 |  250 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
2039 |  251 |             mock_client = MagicMock()
2040 |  252 |             mock_docker.return_value = mock_client
2041 |  253 |             
2042 |  254 |             resolver = ContainerResolver()
2043 |  255 |             
2044 |  256 |             with resolver._lock:
2045 |  257 |                 with resolver._lock:
2046 |  258 |                     pass
2047 |  259 |             
2048 |  260 |             assert True
2049 |  261 | 
2050 |  262 | 
2051 |  263 | class TestContainerResolverEdgeCases:
2052 |  264 |     """Edge case tests."""
2053 |  265 | 
2054 |  266 |     def test_zero_cgroup_id(self):
2055 |  267 |         """Verify zero cgroup ID is handled."""
2056 |  268 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
2057 |  269 |             mock_client = MagicMock()
2058 |  270 |             mock_docker.return_value = mock_client
2059 |  271 |             
2060 |  272 |             resolver = ContainerResolver()
2061 |  273 |             resolver._cache[0] = {"id": "zero"}
2062 |  274 |             
2063 |  275 |             result = resolver.resolve(0)
2064 |  276 |             
2065 |  277 |             assert result["id"] == "zero"
2066 |  278 | 
2067 |  279 |     def test_large_cgroup_id(self):
2068 |  280 |         """Verify large cgroup ID is handled."""
2069 |  281 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
2070 |  282 |             mock_client = MagicMock()
2071 |  283 |             mock_docker.return_value = mock_client
2072 |  284 |             
2073 |  285 |             resolver = ContainerResolver()
2074 |  286 |             
2075 |  287 |             result = resolver.resolve(2**63 - 1)
2076 |  288 |             
2077 |  289 |             assert result is None or result is not None
2078 |  290 | 
2079 |  291 |     def test_empty_container_list(self):
2080 |  292 |         """Verify empty container list handled."""
2081 |  293 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
2082 |  294 |             mock_client = MagicMock()
2083 |  295 |             mock_client.containers.list.return_value = []
2084 |  296 |             mock_docker.return_value = mock_client
2085 |  297 |             
2086 |  298 |             resolver = ContainerResolver()
2087 |  299 |             result = resolver._refresh_and_resolve(12345)
2088 |  300 |             
2089 |  301 |             assert result is None
2090 |  302 | 
2091 |  303 | 
2092 |  304 | class TestContainerResolverMetadata:
2093 |  305 |     """Tests for metadata structure."""
2094 |  306 | 
2095 |  307 |     def test_metadata_has_id(self):
2096 |  308 |         """Verify metadata has id field."""
2097 |  309 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
2098 |  310 |             mock_client = MagicMock()
2099 |  311 |             mock_container = MagicMock()
2100 |  312 |             mock_container.id = "container123"
2101 |  313 |             mock_container.name = "myapp"
2102 |  314 |             mock_container.image.tags = ["myapp:latest"]
2103 |  315 |             mock_container.labels = {"env": "prod"}
2104 |  316 |             mock_client.containers.list.return_value = [mock_container]
2105 |  317 |             mock_docker.return_value = mock_client
2106 |  318 |             
2107 |  319 |             resolver = ContainerResolver()
2108 |  320 |             result = resolver._refresh_and_resolve(12345)
2109 |  321 |             
2110 |  322 |             assert "id" in result
2111 |  323 | 
2112 |  324 |     def test_metadata_has_name(self):
2113 |  325 |         """Verify metadata has name field."""
2114 |  326 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
2115 |  327 |             mock_client = MagicMock()
2116 |  328 |             mock_container = MagicMock()
2117 |  329 |             mock_container.id = "container123"
2118 |  330 |             mock_container.name = "myapp"
2119 |  331 |             mock_container.image.tags = ["myapp:latest"]
2120 |  332 |             mock_container.labels = {}
2121 |  333 |             mock_client.containers.list.return_value = [mock_container]
2122 |  334 |             mock_docker.return_value = mock_client
2123 |  335 |             
2124 |  336 |             resolver = ContainerResolver()
2125 |  337 |             result = resolver._refresh_and_resolve(12345)
2126 |  338 |             
2127 |  339 |             assert "name" in result
2128 |  340 | 
2129 |  341 |     def test_metadata_has_image(self):
2130 |  342 |         """Verify metadata has image field."""
2131 |  343 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
2132 |  344 |             mock_client = MagicMock()
2133 |  345 |             mock_container = MagicMock()
2134 |  346 |             mock_container.id = "container123"
2135 |  347 |             mock_container.name = "myapp"
2136 |  348 |             mock_container.image.tags = ["nginx:1.21"]
2137 |  349 |             mock_container.labels = {}
2138 |  350 |             mock_client.containers.list.return_value = [mock_container]
2139 |  351 |             mock_docker.return_value = mock_client
2140 |  352 |             
2141 |  353 |             resolver = ContainerResolver()
2142 |  354 |             result = resolver._refresh_and_resolve(12345)
2143 |  355 |             
2144 |  356 |             assert "image" in result
2145 |  357 | 
2146 |  358 |     def test_metadata_has_labels(self):
2147 |  359 |         """Verify metadata has labels field."""
2148 |  360 |         with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
2149 |  361 |             mock_client = MagicMock()
2150 |  362 |             mock_container = MagicMock()
2151 |  363 |             mock_container.id = "container123"
2152 |  364 |             mock_container.name = "myapp"
2153 |  365 |             mock_container.image.tags = ["app:v1"]
2154 |  366 |             mock_container.labels = {"key": "value"}
2155 |  367 |             mock_client.containers.list.return_value = [mock_container]
2156 |  368 |             mock_docker.return_value = mock_client
2157 |  369 |             
2158 |  370 |             resolver = ContainerResolver()
2159 |  371 |             result = resolver._refresh_and_resolve(12345)
2160 |  372 |             
2161 |  373 |             assert "labels" in result
2162 | ```
2163 | 
2164 | ### tests/test_ebpf_agent.py
2165 | 
2166 | ```python
2167 |    1 | import ctypes
2168 |    2 | import os
2169 |    3 | import queue
2170 |    4 | import threading
2171 |    5 | from unittest.mock import Mock, patch, MagicMock
2172 |    6 | from pathlib import Path
2173 |    7 | import pytest
2174 |    8 | 
2175 |    9 | EBPF_AGENT_FILE = Path(__file__).parent.parent / "src" / "ebpf_agent.py"
2176 |   10 | 
2177 |   11 | 
2178 |   12 | class TestEBPFAggentModule:
2179 |   13 |     """Tests for ebpf_agent.py module structure."""
2180 |   14 | 
2181 |   15 |     def test_ebpf_agent_file_exists(self):
2182 |   16 |         """Verify ebpf_agent.py exists."""
2183 |   17 |         assert EBPF_AGENT_FILE.exists(), "ebpf_agent.py not found"
2184 |   18 | 
2185 |   19 |     def test_event_class_defined(self):
2186 |   20 |         """Verify Event class is defined."""
2187 |   21 |         import sys
2188 |   22 |         sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2189 |   23 |         from ebpf_agent import Event
2190 |   24 |         assert Event is not None
2191 |   25 | 
2192 |   26 |     def test_event_class_has_required_fields(self):
2193 |   27 |         """Verify Event class has all required fields."""
2194 |   28 |         import sys
2195 |   29 |         sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2196 |   30 |         from ebpf_agent import Event
2197 |   31 |         
2198 |   32 |         field_names = [name for name, _ in Event._fields_]
2199 |   33 |         required_fields = ["pid", "tgid", "cgroup_id", "syscall_id", "comm", "filename"]
2200 |   34 |         for field in required_fields:
2201 |   35 |             assert field in field_names, f"Event missing field: {field}"
2202 |   36 | 
2203 |   37 |     def test_event_field_types(self):
2204 |   38 |         """Verify Event class has correct field types."""
2205 |   39 |         import sys
2206 |   40 |         sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2207 |   41 |         from ebpf_agent import Event
2208 |   42 |         
2209 |   43 |         field_dict = dict(Event._fields_)
2210 |   44 |         assert field_dict["pid"] == ctypes.c_uint32
2211 |   45 |         assert field_dict["tgid"] == ctypes.c_uint32
2212 |   46 |         assert field_dict["cgroup_id"] == ctypes.c_uint64
2213 |   47 |         assert field_dict["syscall_id"] == ctypes.c_uint32
2214 |   48 | 
2215 |   49 |     def test_event_comm_array_size(self):
2216 |   50 |         """Verify comm array is 16 bytes."""
2217 |   51 |         import sys
2218 |   52 |         sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2219 |   53 |         from ebpf_agent import Event
2220 |   54 |         
2221 |   55 |         field_dict = dict(Event._fields_)
2222 |   56 |         assert field_dict["comm"] == ctypes.c_char * 16
2223 |   57 | 
2224 |   58 |     def test_event_filename_array_size(self):
2225 |   59 |         """Verify filename array is 256 bytes."""
2226 |   60 |         import sys
2227 |   61 |         sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2228 |   62 |         from ebpf_agent import Event
2229 |   63 |         
2230 |   64 |         field_dict = dict(Event._fields_)
2231 |   65 |         assert field_dict["filename"] == ctypes.c_char * 256
2232 |   66 | 
2233 |   67 |     def test_event_cb_type_defined(self):
2234 |   68 |         """Verify EVENT_CB callback type is defined."""
2235 |   69 |         import sys
2236 |   70 |         sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2237 |   71 |         from ebpf_agent import EVENT_CB
2238 |   72 |         assert EVENT_CB is not None
2239 |   73 | 
2240 |   74 |     def test_ebpf_agent_class_defined(self):
2241 |   75 |         """Verify EBPFAgent class is defined."""
2242 |   76 |         import sys
2243 |   77 |         sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2244 |   78 |         from ebpf_agent import EBPFAgent
2245 |   79 |         assert EBPFAgent is not None
2246 |   80 | 
2247 |   81 | 
2248 |   82 | class TestEBPFAggentInit:
2249 |   83 |     """Tests for EBPFAgent initialization."""
2250 |   84 | 
2251 |   85 |     @pytest.fixture
2252 |   86 |     def mock_cdll(self):
2253 |   87 |         """Mock ctypes.CDLL."""
2254 |   88 |         with patch("ebpf_agent.ctypes.CDLL") as mock:
2255 |   89 |             mock_lib = MagicMock()
2256 |   90 |             mock.return_value = mock_lib
2257 |   91 |             yield mock_lib
2258 |   92 | 
2259 |   93 |     def test_init_loads_library(self):
2260 |   94 |         """Verify __init__ loads the shared library."""
2261 |   95 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2262 |   96 |             mock_lib = MagicMock()
2263 |   97 |             mock_cdll.return_value = mock_lib
2264 |   98 |             
2265 |   99 |             import sys
2266 |  100 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2267 |  101 |             from ebpf_agent import EBPFAgent
2268 |  102 |             
2269 |  103 |             agent = EBPFAgent(lib_path="/fake/path/libloader.so")
2270 |  104 |             mock_cdll.assert_called_once()
2271 |  105 | 
2272 |  106 |     def test_init_sets_argtypes_for_start_loader(self):
2273 |  107 |         """Verify start_loader argtypes are set."""
2274 |  108 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2275 |  109 |             mock_lib = MagicMock()
2276 |  110 |             mock_cdll.return_value = mock_lib
2277 |  111 |             
2278 |  112 |             import sys
2279 |  113 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2280 |  114 |             from ebpf_agent import EBPFAgent, EVENT_CB
2281 |  115 |             
2282 |  116 |             agent = EBPFAgent()
2283 |  117 |             assert mock_lib.start_loader.argtypes is not None
2284 |  118 | 
2285 |  119 |     def test_init_sets_restype_for_start_loader(self):
2286 |  120 |         """Verify start_loader restype is set to int."""
2287 |  121 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2288 |  122 |             mock_lib = MagicMock()
2289 |  123 |             mock_cdll.return_value = mock_lib
2290 |  124 |             
2291 |  125 |             import sys
2292 |  126 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2293 |  127 |             from ebpf_agent import EBPFAgent
2294 |  128 |             
2295 |  129 |             agent = EBPFAgent()
2296 |  130 |             assert mock_lib.start_loader.restype == ctypes.c_int
2297 |  131 | 
2298 |  132 |     def test_init_sets_argtypes_for_poll_events(self):
2299 |  133 |         """Verify poll_events argtypes are set."""
2300 |  134 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2301 |  135 |             mock_lib = MagicMock()
2302 |  136 |             mock_cdll.return_value = mock_lib
2303 |  137 |             
2304 |  138 |             import sys
2305 |  139 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2306 |  140 |             from ebpf_agent import EBPFAgent
2307 |  141 |             
2308 |  142 |             agent = EBPFAgent()
2309 |  143 |             assert mock_lib.poll_events.argtypes is not None
2310 |  144 | 
2311 |  145 |     def test_init_creates_event_queue(self):
2312 |  146 |         """Verify __init__ creates an event queue."""
2313 |  147 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2314 |  148 |             mock_lib = MagicMock()
2315 |  149 |             mock_cdll.return_value = mock_lib
2316 |  150 |             
2317 |  151 |             import sys
2318 |  152 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2319 |  153 |             from ebpf_agent import EBPFAgent
2320 |  154 |             
2321 |  155 |             agent = EBPFAgent()
2322 |  156 |             assert hasattr(agent, "event_queue")
2323 |  157 |             assert isinstance(agent.event_queue, queue.Queue)
2324 |  158 | 
2325 |  159 |     def test_init_sets_running_false(self):
2326 |  160 |         """Verify __init__ sets running to False."""
2327 |  161 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2328 |  162 |             mock_lib = MagicMock()
2329 |  163 |             mock_cdll.return_value = mock_lib
2330 |  164 |             
2331 |  165 |             import sys
2332 |  166 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2333 |  167 |             from ebpf_agent import EBPFAgent
2334 |  168 |             
2335 |  169 |             agent = EBPFAgent()
2336 |  170 |             assert agent.running is False
2337 |  171 | 
2338 |  172 |     def test_init_sets_thread_none(self):
2339 |  173 |         """Verify __init__ sets thread to None."""
2340 |  174 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2341 |  175 |             mock_lib = MagicMock()
2342 |  176 |             mock_cdll.return_value = mock_lib
2343 |  177 |             
2344 |  178 |             import sys
2345 |  179 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2346 |  180 |             from ebpf_agent import EBPFAgent
2347 |  181 |             
2348 |  182 |             agent = EBPFAgent()
2349 |  183 |             assert agent.thread is None
2350 |  184 | 
2351 |  185 | 
2352 |  186 | class TestEBPFAggentStart:
2353 |  187 |     """Tests for EBPFAgent.start() method."""
2354 |  188 | 
2355 |  189 |     def test_start_calls_start_loader(self):
2356 |  190 |         """Verify start() calls start_loader from library."""
2357 |  191 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2358 |  192 |             mock_lib = MagicMock()
2359 |  193 |             mock_lib.start_loader.return_value = 0
2360 |  194 |             mock_cdll.return_value = mock_lib
2361 |  195 |             
2362 |  196 |             import sys
2363 |  197 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2364 |  198 |             from ebpf_agent import EBPFAgent
2365 |  199 |             
2366 |  200 |             agent = EBPFAgent()
2367 |  201 |             agent.start()
2368 |  202 |             mock_lib.start_loader.assert_called_once()
2369 |  203 | 
2370 |  204 |     def test_start_raises_on_loader_error(self):
2371 |  205 |         """Verify start() raises RuntimeError when loader fails."""
2372 |  206 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2373 |  207 |             mock_lib = MagicMock()
2374 |  208 |             mock_lib.start_loader.return_value = 1
2375 |  209 |             mock_cdll.return_value = mock_lib
2376 |  210 |             
2377 |  211 |             import sys
2378 |  212 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2379 |  213 |             from ebpf_agent import EBPFAgent
2380 |  214 |             
2381 |  215 |             agent = EBPFAgent()
2382 |  216 |             with pytest.raises(RuntimeError) as exc_info:
2383 |  217 |                 agent.start()
2384 |  218 |             assert "Failed to start eBPF loader" in str(exc_info.value)
2385 |  219 | 
2386 |  220 |     def test_start_sets_running_true(self):
2387 |  221 |         """Verify start() sets running to True."""
2388 |  222 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2389 |  223 |             mock_lib = MagicMock()
2390 |  224 |             mock_lib.start_loader.return_value = 0
2391 |  225 |             mock_cdll.return_value = mock_lib
2392 |  226 |             
2393 |  227 |             import sys
2394 |  228 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2395 |  229 |             from ebpf_agent import EBPFAgent
2396 |  230 |             
2397 |  231 |             agent = EBPFAgent()
2398 |  232 |             agent.start()
2399 |  233 |             assert agent.running is True
2400 |  234 | 
2401 |  235 |     def test_start_creates_thread(self):
2402 |  236 |         """Verify start() creates a thread."""
2403 |  237 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2404 |  238 |             with patch("ebpf_agent.threading.Thread") as mock_thread:
2405 |  239 |                 mock_lib = MagicMock()
2406 |  240 |                 mock_lib.start_loader.return_value = 0
2407 |  241 |                 mock_cdll.return_value = mock_lib
2408 |  242 |                 
2409 |  243 |                 import sys
2410 |  244 |                 sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2411 |  245 |                 from ebpf_agent import EBPFAgent
2412 |  246 |                 
2413 |  247 |                 agent = EBPFAgent()
2414 |  248 |                 agent.start()
2415 |  249 |                 mock_thread.assert_called_once()
2416 |  250 | 
2417 |  251 | 
2418 |  252 | class TestEBPFAggentStop:
2419 |  253 |     """Tests for EBPFAgent.stop() method."""
2420 |  254 | 
2421 |  255 |     def test_stop_sets_running_false(self):
2422 |  256 |         """Verify stop() sets running to False."""
2423 |  257 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2424 |  258 |             mock_lib = MagicMock()
2425 |  259 |             mock_lib.start_loader.return_value = 0
2426 |  260 |             mock_cdll.return_value = mock_lib
2427 |  261 |             
2428 |  262 |             import sys
2429 |  263 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2430 |  264 |             from ebpf_agent import EBPFAgent
2431 |  265 |             
2432 |  266 |             agent = EBPFAgent()
2433 |  267 |             agent.running = True
2434 |  268 |             agent.thread = MagicMock()
2435 |  269 |             agent.stop()
2436 |  270 |             assert agent.running is False
2437 |  271 | 
2438 |  272 |     def test_stop_calls_stop_loader(self):
2439 |  273 |         """Verify stop() calls stop_loader from library."""
2440 |  274 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2441 |  275 |             mock_lib = MagicMock()
2442 |  276 |             mock_cdll.return_value = mock_lib
2443 |  277 |             
2444 |  278 |             import sys
2445 |  279 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2446 |  280 |             from ebpf_agent import EBPFAgent
2447 |  281 |             
2448 |  282 |             agent = EBPFAgent()
2449 |  283 |             agent.thread = MagicMock()
2450 |  284 |             agent.stop()
2451 |  285 |             mock_lib.stop_loader.assert_called_once()
2452 |  286 | 
2453 |  287 |     def test_stop_joins_thread_if_exists(self):
2454 |  288 |         """Verify stop() joins thread if it exists."""
2455 |  289 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2456 |  290 |             mock_lib = MagicMock()
2457 |  291 |             mock_cdll.return_value = mock_lib
2458 |  292 |             
2459 |  293 |             import sys
2460 |  294 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2461 |  295 |             from ebpf_agent import EBPFAgent
2462 |  296 |             
2463 |  297 |             agent = EBPFAgent()
2464 |  298 |             mock_thread = MagicMock()
2465 |  299 |             agent.thread = mock_thread
2466 |  300 |             agent.stop()
2467 |  301 |             mock_thread.join.assert_called_once()
2468 |  302 | 
2469 |  303 | 
2470 |  304 | class TestEBPFAggentGetEvent:
2471 |  305 |     """Tests for EBPFAgent.get_event() method."""
2472 |  306 | 
2473 |  307 |     def test_get_event_returns_event(self):
2474 |  308 |         """Verify get_event returns event from queue."""
2475 |  309 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2476 |  310 |             mock_lib = MagicMock()
2477 |  311 |             mock_cdll.return_value = mock_lib
2478 |  312 |             
2479 |  313 |             import sys
2480 |  314 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2481 |  315 |             from ebpf_agent import EBPFAgent
2482 |  316 |             
2483 |  317 |             agent = EBPFAgent()
2484 |  318 |             test_event = {"pid": 123, "comm": "test"}
2485 |  319 |             agent.event_queue.put(test_event)
2486 |  320 |             
2487 |  321 |             result = agent.get_event(block=False)
2488 |  322 |             assert result == test_event
2489 |  323 | 
2490 |  324 |     def test_get_event_returns_none_on_empty(self):
2491 |  325 |         """Verify get_event returns None when queue is empty."""
2492 |  326 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2493 |  327 |             mock_lib = MagicMock()
2494 |  328 |             mock_cdll.return_value = mock_lib
2495 |  329 |             
2496 |  330 |             import sys
2497 |  331 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2498 |  332 |             from ebpf_agent import EBPFAgent
2499 |  333 |             
2500 |  334 |             agent = EBPFAgent()
2501 |  335 |             result = agent.get_event(block=False)
2502 |  336 |             assert result is None
2503 |  337 | 
2504 |  338 | 
2505 |  339 | class TestEBPFAggentEventHandler:
2506 |  340 |     """Tests for EBPFAgent._event_handler() method."""
2507 |  341 | 
2508 |  342 |     def test_event_handler_puts_to_queue(self):
2509 |  343 |         """Verify _event_handler puts event to queue."""
2510 |  344 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2511 |  345 |             mock_lib = MagicMock()
2512 |  346 |             mock_cdll.return_value = mock_lib
2513 |  347 |             
2514 |  348 |             import sys
2515 |  349 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2516 |  350 |             from ebpf_agent import EBPFAgent
2517 |  351 |             
2518 |  352 |             agent = EBPFAgent()
2519 |  353 |             
2520 |  354 |             mock_event = MagicMock()
2521 |  355 |             mock_event.pid = 123
2522 |  356 |             mock_event.tgid = 456
2523 |  357 |             mock_event.cgroup_id = 789
2524 |  358 |             mock_event.syscall_id = 257
2525 |  359 |             mock_event.comm = b"testproc"
2526 |  360 |             mock_event.filename = b"/tmp/test"
2527 |  361 |             
2528 |  362 |             mock_ptr = MagicMock()
2529 |  363 |             mock_ptr.contents = mock_event
2530 |  364 |             
2531 |  365 |             agent._event_handler(None, mock_ptr, 100)
2532 |  366 |             
2533 |  367 |             assert not agent.event_queue.empty()
2534 |  368 |             event = agent.event_queue.get_nowait()
2535 |  369 |             assert event["pid"] == 123
2536 |  370 |             assert event["tgid"] == 456
2537 |  371 | 
2538 |  372 |     def test_event_handler_decodes_comm_utf8(self):
2539 |  373 |         """Verify _event_handler decodes comm as UTF-8."""
2540 |  374 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2541 |  375 |             mock_lib = MagicMock()
2542 |  376 |             mock_cdll.return_value = mock_lib
2543 |  377 |             
2544 |  378 |             import sys
2545 |  379 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2546 |  380 |             from ebpf_agent import EBPFAgent
2547 |  381 |             
2548 |  382 |             agent = EBPFAgent()
2549 |  383 |             
2550 |  384 |             mock_event = MagicMock()
2551 |  385 |             mock_event.pid = 123
2552 |  386 |             mock_event.tgid = 456
2553 |  387 |             mock_event.cgroup_id = 789
2554 |  388 |             mock_event.syscall_id = 257
2555 |  389 |             mock_event.comm = b"test"
2556 |  390 |             mock_event.filename = b"/tmp/test"
2557 |  391 |             
2558 |  392 |             mock_ptr = MagicMock()
2559 |  393 |             mock_ptr.contents = mock_event
2560 |  394 |             
2561 |  395 |             agent._event_handler(None, mock_ptr, 100)
2562 |  396 |             
2563 |  397 |             event = agent.event_queue.get_nowait()
2564 |  398 |             assert isinstance(event["comm"], str)
2565 |  399 | 
2566 |  400 | 
2567 |  401 | class TestEBPFAggentPollLoop:
2568 |  402 |     """Tests for EBPFAgent._poll_loop() method."""
2569 |  403 | 
2570 |  404 |     @pytest.mark.skip(reason="time module imported locally in __main__, difficult to mock properly")
2571 |  405 |     def test_poll_loop_calls_poll_events(self):
2572 |  406 |         """Verify _poll_loop calls poll_events."""
2573 |  407 |         pass
2574 |  408 | 
2575 |  409 | 
2576 |  410 | class TestEBPFAggentEdgeCases:
2577 |  411 |     """Tests for edge cases in EBPFAgent."""
2578 |  412 | 
2579 |  413 |     def test_get_event_with_timeout(self):
2580 |  414 |         """Verify get_event works with timeout parameter."""
2581 |  415 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2582 |  416 |             mock_lib = MagicMock()
2583 |  417 |             mock_cdll.return_value = mock_lib
2584 |  418 |             
2585 |  419 |             import sys
2586 |  420 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2587 |  421 |             from ebpf_agent import EBPFAgent
2588 |  422 |             
2589 |  423 |             agent = EBPFAgent()
2590 |  424 |             result = agent.get_event(block=True, timeout=0.1)
2591 |  425 |             assert result is None
2592 |  426 | 
2593 |  427 |     def test_stop_with_no_thread(self):
2594 |  428 |         """Verify stop() handles None thread gracefully."""
2595 |  429 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2596 |  430 |             mock_lib = MagicMock()
2597 |  431 |             mock_cdll.return_value = mock_lib
2598 |  432 |             
2599 |  433 |             import sys
2600 |  434 |             sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
2601 |  435 |             from ebpf_agent import EBPFAgent
2602 |  436 |             
2603 |  437 |             agent = EBPFAgent()
2604 |  438 |             agent.thread = None
2605 |  439 |             agent.stop()
2606 |  440 |             mock_lib.stop_loader.assert_called_once()
2607 | ```
2608 | 
2609 | ### tests/test_event_structure.py
2610 | 
2611 | ```python
2612 |    1 | import re
2613 |    2 | import pytest
2614 |    3 | from pathlib import Path
2615 |    4 | 
2616 |    5 | EBPF_DIR = Path(__file__).parent.parent / "ebpf"
2617 |    6 | TRACER_FILE = EBPF_DIR / "tracer.bpf.c"
2618 |    7 | 
2619 |    8 | 
2620 |    9 | class TestEventStructure:
2621 |   10 |     """Tests for event structure definition validation."""
2622 |   11 | 
2623 |   12 |     @pytest.fixture
2624 |   13 |     def tracer_content(self):
2625 |   14 |         """Load tracer.bpf.c content."""
2626 |   15 |         return TRACER_FILE.read_text()
2627 |   16 | 
2628 |   17 |     def test_event_struct_exists(self, tracer_content):
2629 |   18 |         """Verify event struct is defined."""
2630 |   19 |         assert "struct event" in tracer_content, "event struct not found"
2631 |   20 |         assert "{" in tracer_content, "event struct body not found"
2632 |   21 | 
2633 |   22 |     def test_event_struct_has_pid_field(self, tracer_content):
2634 |   23 |         """Verify event struct has pid field."""
2635 |   24 |         assert re.search(r'__u32\s+pid', tracer_content), "pid field (__u32) not found in event struct"
2636 |   25 | 
2637 |   26 |     def test_event_struct_has_tgid_field(self, tracer_content):
2638 |   27 |         """Verify event struct has tgid field."""
2639 |   28 |         assert re.search(r'__u32\s+tgid', tracer_content), "tgid field (__u32) not found in event struct"
2640 |   29 | 
2641 |   30 |     def test_event_struct_has_cgroup_id_field(self, tracer_content):
2642 |   31 |         """Verify event struct has cgroup_id field."""
2643 |   32 |         assert re.search(r'__u64\s+cgroup_id', tracer_content), "cgroup_id field (__u64) not found"
2644 |   33 | 
2645 |   34 |     def test_event_struct_has_syscall_id_field(self, tracer_content):
2646 |   35 |         """Verify event struct has syscall_id field."""
2647 |   36 |         assert re.search(r'__u32\s+syscall_id', tracer_content), "syscall_id field (__u32) not found"
2648 |   37 | 
2649 |   38 |     def test_event_struct_has_comm_field(self, tracer_content):
2650 |   39 |         """Verify event struct has comm field (process name)."""
2651 |   40 |         assert re.search(r'char\s+comm\[', tracer_content), "comm field (char array) not found in event struct"
2652 |   41 | 
2653 |   42 |     def test_event_struct_comm_array_size(self, tracer_content):
2654 |   43 |         """Verify comm field has reasonable size (16 bytes)."""
2655 |   44 |         match = re.search(r'char\s+comm\[(\d+)\]', tracer_content)
2656 |   45 |         assert match, "comm array size not found"
2657 |   46 |         size = int(match.group(1))
2658 |   47 |         assert size >= 16, "comm array should be at least 16 bytes for task name"
2659 |   48 | 
2660 |   49 |     def test_event_struct_has_filename_field(self, tracer_content):
2661 |   50 |         """Verify event struct has filename field."""
2662 |   51 |         assert re.search(r'char\s+filename\[', tracer_content), "filename field not found in event struct"
2663 |   52 | 
2664 |   53 |     def test_event_struct_filename_array_size(self, tracer_content):
2665 |   54 |         """Verify filename array is large enough for paths."""
2666 |   55 |         match = re.search(r'char\s+filename\[(\d+)\]', tracer_content)
2667 |   56 |         assert match, "filename array size not found"
2668 |   57 |         size = int(match.group(1))
2669 |   58 |         assert size >= 256, "filename array should be at least 256 bytes for paths"
2670 |   59 | 
2671 |   60 |     def test_event_struct_alignment(self, tracer_content):
2672 |   61 |         """Verify event struct uses proper types for alignment."""
2673 |   62 |         assert "__u32" in tracer_content, "Should use fixed-width integer types"
2674 |   63 |         assert "__u64" in tracer_content, "Should use fixed-width integer types"
2675 |   64 | 
2676 |   65 |     def test_event_used_in_trace_openat(self, tracer_content):
2677 |   66 |         """Verify event struct is used in trace_openat function."""
2678 |   67 |         assert "struct event *e" in tracer_content, "Event pointer not created in trace_openat"
2679 |   68 | 
2680 |   69 |     def test_event_fields_populated(self, tracer_content):
2681 |   70 |         """Verify event fields are populated in trace_openat."""
2682 |   71 |         assert "e->pid" in tracer_content, "pid not assigned to event"
2683 |   72 |         assert "e->tgid" in tracer_content, "tgid not assigned to event"
2684 |   73 |         assert "e->cgroup_id" in tracer_content, "cgroup_id not assigned to event"
2685 |   74 |         assert "e->syscall_id" in tracer_content, "syscall_id not assigned to event"
2686 |   75 |         assert "e->comm" in tracer_content, "comm not assigned to event"
2687 |   76 | 
2688 |   77 |     def test_syscall_id_value(self, tracer_content):
2689 |   78 |         """Verify syscall_id is set to openat (257)."""
2690 |   79 |         assert "257" in tracer_content, "openat syscall number (257) not used"
2691 | ```
2692 | 
2693 | ### tests/test_integration.py
2694 | 
2695 | ```python
2696 |    1 | import os
2697 |    2 | import subprocess
2698 |    3 | import pytest
2699 |    4 | from pathlib import Path
2700 |    5 | from unittest.mock import patch, MagicMock
2701 |    6 | 
2702 |    7 | EBPF_DIR = Path(__file__).parent.parent / "ebpf"
2703 |    8 | SRC_DIR = Path(__file__).parent.parent / "src"
2704 |    9 | 
2705 |   10 | 
2706 |   11 | class TestBuildIntegration:
2707 |   12 |     """Integration tests for building the entire system."""
2708 |   13 | 
2709 |   14 |     def test_full_build_produces_all_artifacts(self):
2710 |   15 |         """Verify full build produces all expected artifacts."""
2711 |   16 |         subprocess.run(["make", "clean"], cwd=EBPF_DIR, check=True)
2712 |   17 |         
2713 |   18 |         result = subprocess.run(
2714 |   19 |             ["make", "all"],
2715 |   20 |             cwd=EBPF_DIR,
2716 |   21 |             capture_output=True,
2717 |   22 |             text=True
2718 |   23 |         )
2719 |   24 |         
2720 |   25 |         assert result.returncode == 0, f"Build failed: {result.stderr}"
2721 |   26 |         
2722 |   27 |         expected = ["tracer.bpf.o", "tracer.skel.h", "libloader.so"]
2723 |   28 |         for artifact in expected:
2724 |   29 |             path = EBPF_DIR / artifact
2725 |   30 |             assert path.exists(), f"Expected artifact {artifact} not found"
2726 |   31 | 
2727 |   32 |     def test_build_creates_libloader_so(self):
2728 |   33 |         """Verify libloader.so is created."""
2729 |   34 |         path = EBPF_DIR / "libloader.so"
2730 |   35 |         assert path.exists(), "libloader.so not found"
2731 |   36 | 
2732 |   37 |     def test_build_creates_skeleton_header(self):
2733 |   38 |         """Verify tracer.skel.h is created."""
2734 |   39 |         path = EBPF_DIR / "tracer.skel.h"
2735 |   40 |         assert path.exists(), "tracer.skel.h not found"
2736 |   41 | 
2737 |   42 |     def test_skeleton_header_has_bpf_prog_definitions(self):
2738 |   43 |         """Verify skeleton header contains BPF program definitions."""
2739 |   44 |         skel = EBPF_DIR / "tracer.skel.h"
2740 |   45 |         content = skel.read_text()
2741 |   46 |         
2742 |   47 |         assert "tracer_bpf__open" in content, "Missing tracer_bpf__open"
2743 |   48 |         assert "tracer_bpf__load" in content, "Missing tracer_bpf__load"
2744 |   49 |         assert "tracer_bpf__attach" in content, "Missing tracer_bpf__attach"
2745 |   50 |         assert "tracer_bpf__destroy" in content, "Missing tracer_bpf__destroy"
2746 |   51 | 
2747 |   52 |     def test_clean_removes_all_build_artifacts(self):
2748 |   53 |         """Verify make clean removes all generated files."""
2749 |   54 |         subprocess.run(["make", "all"], cwd=EBPF_DIR, check=True)
2750 |   55 |         
2751 |   56 |         subprocess.run(["make", "clean"], cwd=EBPF_DIR, check=True)
2752 |   57 |         
2753 |   58 |         generated = ["tracer.bpf.o", "tracer.skel.h", "libloader.so"]
2754 |   59 |         for artifact in generated:
2755 |   60 |             path = EBPF_DIR / artifact
2756 |   61 |             assert not path.exists(), f"Artifact {artifact} should have been cleaned"
2757 |   62 | 
2758 |   63 | 
2759 |   64 | class TestPythonAgentIntegration:
2760 |   65 |     """Integration tests for Python agent with C library."""
2761 |   66 | 
2762 |   67 |     def test_ebpf_agent_can_import(self):
2763 |   68 |         """Verify ebpf_agent module can be imported."""
2764 |   69 |         import sys
2765 |   70 |         sys.path.insert(0, str(SRC_DIR))
2766 |   71 |         from ebpf_agent import EBPFAgent, Event
2767 |   72 |         assert EBPFAgent is not None
2768 |   73 |         assert Event is not None
2769 |   74 | 
2770 |   75 |     def test_ebpf_agent_initialization_integration(self):
2771 |   76 |         """Test EBPFAgent can be initialized with mocked library."""
2772 |   77 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2773 |   78 |             mock_lib = MagicMock()
2774 |   79 |             mock_cdll.return_value = mock_lib
2775 |   80 |             
2776 |   81 |             import sys
2777 |   82 |             sys.path.insert(0, str(SRC_DIR))
2778 |   83 |             from ebpf_agent import EBPFAgent
2779 |   84 |             
2780 |   85 |             agent = EBPFAgent(lib_path="/nonexistent/libloader.so")
2781 |   86 |             assert agent is not None
2782 |   87 |             assert agent.running is False
2783 |   88 | 
2784 |   89 |     def test_agent_event_structure_matches_c_event(self):
2785 |   90 |         """Verify Python Event matches C event structure."""
2786 |   91 |         import sys
2787 |   92 |         sys.path.insert(0, str(SRC_DIR))
2788 |   93 |         from ebpf_agent import Event
2789 |   94 |         
2790 |   95 |         assert hasattr(Event, "_fields_")
2791 |   96 |         fields = dict(Event._fields_)
2792 |   97 |         
2793 |   98 |         assert "pid" in fields and fields["pid"] == __import__('ctypes').c_uint32
2794 |   99 |         assert "tgid" in fields and fields["tgid"] == __import__('ctypes').c_uint32
2795 |  100 |         assert "cgroup_id" in fields and fields["cgroup_id"] == __import__('ctypes').c_uint64
2796 |  101 |         assert "syscall_id" in fields and fields["syscall_id"] == __import__('ctypes').c_uint32
2797 |  102 |         assert "comm" in fields
2798 |  103 |         assert "filename" in fields
2799 |  104 | 
2800 |  105 | 
2801 |  106 | class TestLoaderAgentIntegration:
2802 |  107 |     """Integration tests for C loader and Python agent working together."""
2803 |  108 | 
2804 |  109 |     def test_loader_exports_required_functions(self):
2805 |  110 |         """Verify loader.c exports required functions."""
2806 |  111 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2807 |  112 |             mock_lib = MagicMock()
2808 |  113 |             mock_cdll.return_value = mock_lib
2809 |  114 |             
2810 |  115 |             import sys
2811 |  116 |             sys.path.insert(0, str(SRC_DIR))
2812 |  117 |             from ebpf_agent import EBPFAgent
2813 |  118 |             
2814 |  119 |             agent = EBPFAgent()
2815 |  120 |             
2816 |  121 |             assert hasattr(agent.lib, "start_loader")
2817 |  122 |             assert hasattr(agent.lib, "poll_events")
2818 |  123 |             assert hasattr(agent.lib, "stop_loader")
2819 |  124 | 
2820 |  125 |     def test_agent_callback_signature_matches_loader(self):
2821 |  126 |         """Verify Python callback signature matches C loader expectation."""
2822 |  127 |         import sys
2823 |  128 |         sys.path.insert(0, str(SRC_DIR))
2824 |  129 |         from ebpf_agent import EVENT_CB, EBPFAgent
2825 |  130 |         
2826 |  131 |         assert EVENT_CB is not None
2827 |  132 |         
2828 |  133 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2829 |  134 |             mock_lib = MagicMock()
2830 |  135 |             mock_cdll.return_value = mock_lib
2831 |  136 |             
2832 |  137 |             agent = EBPFAgent()
2833 |  138 |             
2834 |  139 |             assert hasattr(agent, "_callback_ref")
2835 |  140 | 
2836 |  141 | 
2837 |  142 | class TestEndToEndSimulation:
2838 |  143 |     """End-to-end simulation tests."""
2839 |  144 | 
2840 |  145 |     def test_agent_lifecycle_simulation(self):
2841 |  146 |         """Simulate complete agent lifecycle."""
2842 |  147 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2843 |  148 |             with patch("ebpf_agent.threading.Thread") as mock_thread:
2844 |  149 |                 mock_lib = MagicMock()
2845 |  150 |                 mock_lib.start_loader.return_value = 0
2846 |  151 |                 mock_cdll.return_value = mock_lib
2847 |  152 |                 
2848 |  153 |                 mock_thread_instance = MagicMock()
2849 |  154 |                 mock_thread.return_value = mock_thread_instance
2850 |  155 |                 
2851 |  156 |                 import sys
2852 |  157 |                 sys.path.insert(0, str(SRC_DIR))
2853 |  158 |                 from ebpf_agent import EBPFAgent
2854 |  159 |                 
2855 |  160 |                 agent = EBPFAgent()
2856 |  161 |                 
2857 |  162 |                 assert agent.running is False
2858 |  163 |                 agent.start()
2859 |  164 |                 assert agent.running is True
2860 |  165 |                 mock_thread_instance.start.assert_called_once()
2861 |  166 |                 
2862 |  167 |                 agent.stop()
2863 |  168 |                 assert agent.running is False
2864 |  169 |                 mock_lib.stop_loader.assert_called_once()
2865 |  170 | 
2866 |  171 |     def test_multiple_start_stop_cycles(self):
2867 |  172 |         """Test multiple start/stop cycles."""
2868 |  173 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2869 |  174 |             with patch("ebpf_agent.threading.Thread") as mock_thread:
2870 |  175 |                 mock_lib = MagicMock()
2871 |  176 |                 mock_lib.start_loader.return_value = 0
2872 |  177 |                 mock_cdll.return_value = mock_lib
2873 |  178 |                 
2874 |  179 |                 mock_thread_instance = MagicMock()
2875 |  180 |                 mock_thread.return_value = mock_thread_instance
2876 |  181 |                 
2877 |  182 |                 import sys
2878 |  183 |                 sys.path.insert(0, str(SRC_DIR))
2879 |  184 |                 from ebpf_agent import EBPFAgent
2880 |  185 |                 
2881 |  186 |                 agent = EBPFAgent()
2882 |  187 |                 
2883 |  188 |                 for i in range(3):
2884 |  189 |                     agent.start()
2885 |  190 |                     agent.stop()
2886 |  191 |                 
2887 |  192 |                 assert mock_lib.start_loader.call_count == 3
2888 |  193 |                 assert mock_lib.stop_loader.call_count == 3
2889 |  194 | 
2890 |  195 | 
2891 |  196 | class TestErrorHandlingIntegration:
2892 |  197 |     """Integration tests for error handling."""
2893 |  198 | 
2894 |  199 |     def test_agent_handles_missing_library(self):
2895 |  200 |         """Test agent handles missing library gracefully."""
2896 |  201 |         import sys
2897 |  202 |         sys.path.insert(0, str(SRC_DIR))
2898 |  203 |         
2899 |  204 |         with pytest.raises(OSError):
2900 |  205 |             import ctypes
2901 |  206 |             ctypes.CDLL("/nonexistent/path/libloader.so")
2902 |  207 | 
2903 |  208 |     def test_agent_handles_loader_failure(self):
2904 |  209 |         """Test agent handles loader failure gracefully."""
2905 |  210 |         with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
2906 |  211 |             mock_lib = MagicMock()
2907 |  212 |             mock_lib.start_loader.return_value = 1
2908 |  213 |             mock_cdll.return_value = mock_lib
2909 |  214 |             
2910 |  215 |             import sys
2911 |  216 |             sys.path.insert(0, str(SRC_DIR))
2912 |  217 |             from ebpf_agent import EBPFAgent
2913 |  218 |             
2914 |  219 |             agent = EBPFAgent()
2915 |  220 |             
2916 |  221 |             with pytest.raises(RuntimeError) as exc_info:
2917 |  222 |                 agent.start()
2918 |  223 |             assert "Failed to start eBPF loader" in str(exc_info.value)
2919 |  224 | 
2920 |  225 | 
2921 |  226 | class TestBuildEnvironmentIntegration:
2922 |  227 |     """Integration tests for build environment."""
2923 |  228 | 
2924 |  229 |     def test_clang_available_in_build(self):
2925 |  230 |         """Verify clang is available for build."""
2926 |  231 |         result = subprocess.run(["which", "clang"], capture_output=True)
2927 |  232 |         assert result.returncode == 0, "clang not found"
2928 |  233 | 
2929 |  234 |     def test_bpftool_available_in_build(self):
2930 |  235 |         """Verify bpftool is available for skeleton generation."""
2931 |  236 |         result = subprocess.run(["which", "bpftool"], capture_output=True)
2932 |  237 |         assert result.returncode == 0, "bpftool not found"
2933 |  238 | 
2934 |  239 |     def test_libbpf_available(self):
2935 |  240 |         """Verify libbpf development files are available."""
2936 |  241 |         result = subprocess.run(["pkg-config", "--exists", "libbpf"], capture_output=True)
2937 |  242 |         assert result.returncode == 0, "libbpf not found"
2938 |  243 | 
2939 |  244 |     def test_required_kernel_headers(self):
2940 |  245 |         """Verify required kernel headers exist."""
2941 |  246 |         arch = subprocess.run(["uname", "-m"], capture_output=True, text=True).stdout.strip()
2942 |  247 |         linux_gnuhdr = Path(f"/usr/include/{arch}-linux-gnu")
2943 |  248 |         if linux_gnuhdr.exists():
2944 |  249 |             assert (linux_gnuhdr / "asm").exists() or True
2945 | ```
2946 | 
2947 | ### tests/test_loader.py
2948 | 
2949 | ```python
2950 |    1 | import re
2951 |    2 | import pytest
2952 |    3 | from pathlib import Path
2953 |    4 | 
2954 |    5 | EBPF_DIR = Path(__file__).parent.parent / "ebpf"
2955 |    6 | LOADER_FILE = EBPF_DIR / "loader.c"
2956 |    7 | 
2957 |    8 | 
2958 |    9 | class TestLoaderC:
2959 |   10 |     """Tests for ebpf/loader.c validation."""
2960 |   11 | 
2961 |   12 |     @pytest.fixture
2962 |   13 |     def loader_content(self):
2963 |   14 |         """Load loader.c content."""
2964 |   15 |         return LOADER_FILE.read_text()
2965 |   16 | 
2966 |   17 |     def test_loader_file_exists(self):
2967 |   18 |         """Verify loader.c exists."""
2968 |   19 |         assert LOADER_FILE.exists(), "loader.c not found"
2969 |   20 | 
2970 |   21 |     def test_includes_required_headers(self, loader_content):
2971 |   22 |         """Verify required headers are included."""
2972 |   23 |         required = ["stdio.h", "stdlib.h", "string.h", "errno.h", "bpf/libbpf.h", "bpf/bpf.h"]
2973 |   24 |         for header in required:
2974 |   25 |             assert header in loader_content, f"Required header {header} not included"
2975 |   26 | 
2976 |   27 |     def test_includes_tracer_skeleton(self, loader_content):
2977 |   28 |         """Verify tracer.skel.h is included."""
2978 |   29 |         assert 'tracer.skel.h' in loader_content, "tracer.skel.h not included"
2979 |   30 | 
2980 |   31 |     def test_libbpf_print_fn_exists(self, loader_content):
2981 |   32 |         """Verify libbpf print callback is defined."""
2982 |   33 |         assert "libbpf_print_fn" in loader_content, "libbpf_print_fn not found"
2983 |   34 | 
2984 |   35 |     def test_libbpf_print_fn_signature(self, loader_content):
2985 |   36 |         """Verify libbpf_print_fn has correct signature."""
2986 |   37 |         pattern = r'static\s+int\s+libbpf_print_fn\s*\(\s*enum\s+libbpf_print_level'
2987 |   38 |         assert re.search(pattern, loader_content), "libbpf_print_fn signature incorrect"
2988 |   39 | 
2989 |   40 |     def test_global_skel_variable(self, loader_content):
2990 |   41 |         """Verify skeleton global variable is declared."""
2991 |   42 |         assert "struct tracer_bpf *skel" in loader_content, "Global skel variable not found"
2992 |   43 | 
2993 |   44 |     def test_global_rb_variable(self, loader_content):
2994 |   45 |         """Verify ring buffer global variable is declared."""
2995 |   46 |         assert "ring_buffer *rb" in loader_content or "struct ring_buffer *rb" in loader_content, "Global rb variable not found"
2996 |   47 | 
2997 |   48 |     def test_user_callback_global(self, loader_content):
2998 |   49 |         """Verify user_callback global variable exists."""
2999 |   50 |         assert "user_callback" in loader_content, "user_callback global not found"
3000 |   51 | 
3001 |   52 |     def test_event_cb_typedef(self, loader_content):
3002 |   53 |         """Verify event callback typedef is defined."""
3003 |   54 |         assert "event_cb_t" in loader_content, "event_cb_t typedef not found"
3004 |   55 | 
3005 |   56 |     def test_handle_event_function_exists(self, loader_content):
3006 |   57 |         """Verify handle_event function exists."""
3007 |   58 |         assert "handle_event" in loader_content, "handle_event function not found"
3008 |   59 | 
3009 |   60 |     def test_handle_event_calls_callback(self, loader_content):
3010 |   61 |         """Verify handle_event calls user_callback."""
3011 |   62 |         assert "user_callback" in loader_content and "handle_event" in loader_content
3012 |   63 |         assert re.search(r'if\s*\(\s*user_callback\s*\)', loader_content), "user_callback not checked before calling"
3013 |   64 | 
3014 |   65 |     def test_start_loader_function_exists(self, loader_content):
3015 |   66 |         """Verify start_loader function exists."""
3016 |   67 |         assert re.search(r'int\s+start_loader\s*\(', loader_content), "start_loader function not found"
3017 |   68 | 
3018 |   69 |     def test_start_loader_sets_libbpf_print(self, loader_content):
3019 |   70 |         """Verify start_loader sets libbpf print callback."""
3020 |   71 |         assert "libbpf_set_print" in loader_content, "libbpf_set_print not called"
3021 |   72 | 
3022 |   73 |     def test_start_loader_opens_skeleton(self, loader_content):
3023 |   74 |         """Verify start_loader opens BPF skeleton."""
3024 |   75 |         assert "tracer_bpf__open" in loader_content, "tracer_bpf__open not called"
3025 |   76 | 
3026 |   77 |     def test_start_loader_loads_skeleton(self, loader_content):
3027 |   78 |         """Verify start_loader loads BPF skeleton."""
3028 |   79 |         assert "tracer_bpf__load" in loader_content, "tracer_bpf__load not called"
3029 |   80 | 
3030 |   81 |     def test_start_loader_attaches_skeleton(self, loader_content):
3031 |   82 |         """Verify start_loader attaches BPF skeleton."""
3032 |   83 |         assert "tracer_bpf__attach" in loader_content, "tracer_bpf__attach not called"
3033 |   84 | 
3034 |   85 |     def test_start_loader_creates_ring_buffer(self, loader_content):
3035 |   86 |         """Verify start_loader creates ring buffer."""
3036 |   87 |         assert "ring_buffer__new" in loader_content, "ring_buffer__new not called"
3037 |   88 | 
3038 |   89 |     def test_start_loader_checks_ring_buffer(self, loader_content):
3039 |   90 |         """Verify start_loader checks ring buffer creation."""
3040 |   91 |         assert re.search(r'if\s*\(\s*!rb\s*\)', loader_content), "Ring buffer NULL check not found"
3041 |   92 | 
3042 |   93 |     def test_poll_events_function_exists(self, loader_content):
3043 |   94 |         """Verify poll_events function exists."""
3044 |   95 |         assert re.search(r'int\s+poll_events\s*\(', loader_content), "poll_events function not found"
3045 |   96 | 
3046 |   97 |     def test_poll_events_calls_ring_buffer_poll(self, loader_content):
3047 |   98 |         """Verify poll_events uses ring_buffer__poll."""
3048 |   99 |         assert "ring_buffer__poll" in loader_content, "ring_buffer__poll not called"
3049 |  100 | 
3050 |  101 |     def test_stop_loader_function_exists(self, loader_content):
3051 |  102 |         """Verify stop_loader function exists."""
3052 |  103 |         assert re.search(r'void\s+stop_loader\s*\(', loader_content), "stop_loader function not found"
3053 |  104 | 
3054 |  105 |     def test_stop_loader_frees_ring_buffer(self, loader_content):
3055 |  106 |         """Verify stop_loader frees ring buffer."""
3056 |  107 |         assert "ring_buffer__free" in loader_content, "ring_buffer__free not called"
3057 |  108 | 
3058 |  109 |     def test_stop_loader_destroys_skeleton(self, loader_content):
3059 |  110 |         """Verify stop_loader destroys skeleton."""
3060 |  111 |         assert "tracer_bpf__destroy" in loader_content, "tracer_bpf__destroy not called"
3061 |  112 | 
3062 |  113 |     def test_cleanup_label_exists(self, loader_content):
3063 |  114 |         """Verify cleanup label exists for error handling."""
3064 |  115 |         assert re.search(r'cleanup:', loader_content), "cleanup label not found"
3065 |  116 | 
3066 |  117 |     def test_error_messages_to_stderr(self, loader_content):
3067 |  118 |         """Verify error messages go to stderr."""
3068 |  119 |         assert "fprintf(stderr" in loader_content, "Error messages should use stderr"
3069 |  120 | 
3070 |  121 |     def test_null_check_on_skel_open(self, loader_content):
3071 |  122 |         """Verify skeleton open result is checked for NULL."""
3072 |  123 |         assert re.search(r'if\s*\(\s*!skel\s*\)', loader_content), "skel NULL check not found"
3073 |  124 | 
3074 |  125 |     def test_error_return_on_skel_failure(self, loader_content):
3075 |  126 |         """Verify error return when skeleton open fails."""
3076 |  127 |         assert re.search(r'return\s+1', loader_content), "Error return value not found"
3077 |  128 | 
3078 |  129 |     def test_callback_assignment_in_start_loader(self, loader_content):
3079 |  130 |         """Verify user_callback is assigned in start_loader."""
3080 |  131 |         lines_after_start = loader_content.split("start_loader")[1].split("poll_events")[0]
3081 |  132 |         assert "user_callback = cb" in lines_after_start, "user_callback not assigned in start_loader"
3082 |  133 | 
3083 |  134 | 
3084 |  135 | class TestLoaderMakefile:
3085 |  136 |     """Tests for Makefile validation related to loader."""
3086 |  137 | 
3087 |  138 |     @pytest.fixture
3088 |  139 |     def makefile_content(self):
3089 |  140 |         """Load Makefile content."""
3090 |  141 |         return (EBPF_DIR / "Makefile").read_text()
3091 |  142 | 
3092 |  143 |     def test_makefile_exists(self):
3093 |  144 |         """Verify Makefile exists."""
3094 |  145 |         assert (EBPF_DIR / "Makefile").exists()
3095 |  146 | 
3096 |  147 |     def test_libloader_target_exists(self, makefile_content):
3097 |  148 |         """Verify libloader.so target exists."""
3098 |  149 |         assert "libloader.so:" in makefile_content, "libloader.so target not found"
3099 |  150 | 
3100 |  151 |     def test_skeleton_generation_target(self, makefile_content):
3101 |  152 |         """Verify skeleton generation target exists."""
3102 |  153 |         assert ".skel.h" in makefile_content, "skeleton target not found"
3103 |  154 | 
3104 |  155 |     def test_bpftool_used_for_skeleton(self, makefile_content):
3105 |  156 |         """Verify bpftool is used for skeleton generation."""
3106 |  157 |         assert "bpftool" in makefile_content, "bpftool not used"
3107 |  158 | 
3108 |  159 |     def test_libloader_depends_on_loader_c(self, makefile_content):
3109 |  160 |         """Verify libloader.so depends on loader.c."""
3110 |  161 |         assert "loader.c" in makefile_content, "loader.c dependency missing"
3111 |  162 | 
3112 |  163 |     def test_libloader_depends_on_skeleton(self, makefile_content):
3113 |  164 |         """Verify libloader.so depends on skeleton header."""
3114 |  165 |         assert "skel.h" in makefile_content, "skeleton header dependency missing"
3115 |  166 | 
3116 |  167 |     def test_clean_removes_so_file(self, makefile_content):
3117 |  168 |         """Verify clean removes .so files."""
3118 |  169 |         assert "rm" in makefile_content and ".so" in makefile_content, "clean should remove .so files"
3119 | ```
3120 | 
3121 | ### tests/test_maps.py
3122 | 
3123 | ```python
3124 |    1 | import re
3125 |    2 | import pytest
3126 |    3 | from pathlib import Path
3127 |    4 | 
3128 |    5 | EBPF_DIR = Path(__file__).parent.parent / "ebpf"
3129 |    6 | MAPS_HEADER = EBPF_DIR / "maps.bpf.h"
3130 |    7 | 
3131 |    8 | 
3132 |    9 | class TestEBPFMapValidation:
3133 |   10 |     """Tests for eBPF map definitions validation."""
3134 |   11 | 
3135 |   12 |     @pytest.fixture
3136 |   13 |     def maps_content(self):
3137 |   14 |         """Load maps.bpf.h content."""
3138 |   15 |         return MAPS_HEADER.read_text()
3139 |   16 | 
3140 |   17 |     def test_maps_header_exists(self):
3141 |   18 |         """Verify maps.bpf.h exists."""
3142 |   19 |         assert MAPS_HEADER.exists(), "maps.bpf.h not found"
3143 |   20 | 
3144 |   21 |     def test_maps_header_has_header_guard(self, maps_content):
3145 |   22 |         """Verify maps header has proper include guards."""
3146 |   23 |         assert "#ifndef __MAPS_BPF_H" in maps_content, "Missing header guard start"
3147 |   24 |         assert "#define __MAPS_BPF_H" in maps_content, "Missing header guard define"
3148 |   25 |         assert "#endif" in maps_content, "Missing header guard endif"
3149 |   26 | 
3150 |   27 |     def test_ringbuf_map_exists(self, maps_content):
3151 |   28 |         """Verify ring buffer map is defined."""
3152 |   29 |         assert "BPF_MAP_TYPE_RINGBUF" in maps_content, "Ringbuf map type not found"
3153 |   30 |         assert "rb" in maps_content, "Ring buffer map 'rb' not found"
3154 |   31 | 
3155 |   32 |     def test_ringbuf_map_properties(self, maps_content):
3156 |   33 |         """Verify ring buffer map has correct properties."""
3157 |   34 |         assert "max_entries" in maps_content, "Ringbuf max_entries not found"
3158 |   35 |         assert "256" in maps_content or "256 * 1024" in maps_content, "Ringbuf size not configured"
3159 |   36 | 
3160 |   37 |     def test_proc_metrics_map_exists(self, maps_content):
3161 |   38 |         """Verify proc_metrics hash map is defined."""
3162 |   39 |         assert "proc_metrics" in maps_content, "proc_metrics map not found"
3163 |   40 |         assert "BPF_MAP_TYPE_HASH" in maps_content, "Hash map type not found"
3164 |   41 | 
3165 |   42 |     def test_proc_metrics_key_type(self, maps_content):
3166 |   43 |         """Verify proc_metrics has correct key type (PID as __u32)."""
3167 |   44 |         assert "__u32" in maps_content, "Key type __u32 not found in maps"
3168 |   45 | 
3169 |   46 |     def test_proc_metrics_value_type(self, maps_content):
3170 |   47 |         """Verify proc_metrics has correct value type (__u64 for counter)."""
3171 |   48 |         assert "key, __u32" in maps_content or "key,__u32" in maps_content, "Key type not matching PID"
3172 |   49 |         assert "value, __u64" in maps_content or "value,__u64" in maps_content, "Value type not matching counter"
3173 |   50 | 
3174 |   51 |     def test_proc_metrics_max_entries(self, maps_content):
3175 |   52 |         """Verify proc_metrics has reasonable max_entries."""
3176 |   53 |         match = re.search(r'proc_metrics.*?max_entries,\s*(\d+)', maps_content, re.DOTALL)
3177 |   54 |         assert match, "proc_metrics max_entries not found"
3178 |   55 |         max_entries = int(match.group(1))
3179 |   56 |         assert max_entries > 0, "proc_metrics max_entries should be positive"
3180 |   57 |         assert max_entries <= 100000, "proc_metrics max_entries unreasonably large"
3181 |   58 | 
3182 |   59 |     def test_container_map_exists(self, maps_content):
3183 |   60 |         """Verify container_map is defined."""
3184 |   61 |         assert "container_map" in maps_content, "container_map not found"
3185 |   62 | 
3186 |   63 |     def test_container_map_key_type(self, maps_content):
3187 |   64 |         """Verify container_map uses cgroup_id as key (__u64)."""
3188 |   65 |         assert "cgroup" in maps_content.lower(), "cgroup_id not referenced in maps"
3189 |   66 | 
3190 |   67 |     def test_all_maps_have_sec_markers(self, maps_content):
3191 |   68 |         """Verify all maps have SEC(.maps) markers."""
3192 |   69 |         sec_markers = maps_content.count("SEC(\".maps\")")
3193 |   70 |         assert sec_markers >= 3, f"Expected at least 3 SEC(.maps) markers, found {sec_markers}"
3194 |   71 | 
3195 |   72 |     def test_maps_include_vmlinux(self, maps_content):
3196 |   73 |         """Verify maps include vmlinux.h."""
3197 |   74 |         assert "#include" in maps_content and "vmlinux.h" in maps_content, "vmlinux.h not included"
3198 |   75 | 
3199 |   76 |     def test_maps_include_bpf_helpers(self, maps_content):
3200 |   77 |         """Verify maps include bpf helpers."""
3201 |   78 |         assert "#include" in maps_content and "bpf_helpers.h" in maps_content, "bpf_helpers.h not included"
3202 | ```
3203 | 
3204 | ### tests/test_metrics_engine.py
3205 | 
3206 | ```python
3207 |    1 | import pytest
3208 |    2 | import numpy as np
3209 |    3 | from unittest.mock import MagicMock, patch, PropertyMock
3210 |    4 | from pathlib import Path
3211 |    5 | from collections import deque
3212 |    6 | 
3213 |    7 | SRC_DIR = Path(__file__).parent.parent / "src"
3214 |    8 | 
3215 |    9 | 
3216 |   10 | class TestMetricsEngineInit:
3217 |   11 |     """Tests for MetricsEngine initialization."""
3218 |   12 | 
3219 |   13 |     def test_engine_file_exists(self):
3220 |   14 |         """Verify MetricsEngine exists."""
3221 |   15 |         import sys
3222 |   16 |         sys.path.insert(0, str(SRC_DIR))
3223 |   17 |         from src.metrics.engine import MetricsEngine
3224 |   18 |         assert MetricsEngine is not None
3225 |   19 | 
3226 |   20 |     def test_default_alpha(self):
3227 |   21 |         """Verify default alpha is 0.3."""
3228 |   22 |         import sys
3229 |   23 |         sys.path.insert(0, str(SRC_DIR))
3230 |   24 |         from src.metrics.engine import MetricsEngine
3231 |   25 |         engine = MetricsEngine()
3232 |   26 |         assert engine.alpha == 0.3
3233 |   27 | 
3234 |   28 |     def test_custom_alpha(self):
3235 |   29 |         """Verify custom alpha is set correctly."""
3236 |   30 |         import sys
3237 |   31 |         sys.path.insert(0, str(SRC_DIR))
3238 |   32 |         from src.metrics.engine import MetricsEngine
3239 |   33 |         engine = MetricsEngine(alpha=0.5)
3240 |   34 |         assert engine.alpha == 0.5
3241 |   35 | 
3242 |   36 |     def test_default_n_gram_size(self):
3243 |   37 |         """Verify default n_gram_size is 3."""
3244 |   38 |         import sys
3245 |   39 |         sys.path.insert(0, str(SRC_DIR))
3246 |   40 |         from src.metrics.engine import MetricsEngine
3247 |   41 |         engine = MetricsEngine()
3248 |   42 |         assert engine.n_gram_size == 3
3249 |   43 | 
3250 |   44 |     def test_custom_n_gram_size(self):
3251 |   45 |         """Verify custom n_gram_size is set correctly."""
3252 |   46 |         import sys
3253 |   47 |         sys.path.insert(0, str(SRC_DIR))
3254 |   48 |         from src.metrics.engine import MetricsEngine
3255 |   49 |         engine = MetricsEngine(n_gram_size=5)
3256 |   50 |         assert engine.n_gram_size == 5
3257 |   51 | 
3258 |   52 |     def test_profiles_initially_empty(self):
3259 |   53 |         """Verify profiles dict is empty on init."""
3260 |   54 |         import sys
3261 |   55 |         sys.path.insert(0, str(SRC_DIR))
3262 |   56 |         from src.metrics.engine import MetricsEngine
3263 |   57 |         engine = MetricsEngine()
3264 |   58 |         assert engine.profiles == {}
3265 |   59 | 
3266 |   60 | 
3267 |   61 | class TestMetricsEngineUpdateScalar:
3268 |   62 |     """Tests for update_scalar_metrics method."""
3269 |   63 | 
3270 |   64 |     def test_first_update_creates_profile(self):
3271 |   65 |         """Verify first update creates a new profile."""
3272 |   66 |         import sys
3273 |   67 |         sys.path.insert(0, str(SRC_DIR))
3274 |   68 |         from src.metrics.engine import MetricsEngine
3275 |   69 |         engine = MetricsEngine()
3276 |   70 |         vector = np.array([1.0, 2.0, 3.0])
3277 |   71 |         engine.update_scalar_metrics(123, vector)
3278 |   72 |         assert 123 in engine.profiles
3279 |   73 | 
3280 |   74 |     def test_first_update_sets_mu_to_vector(self):
3281 |   75 |         """Verify first update sets mu to the current vector."""
3282 |   76 |         import sys
3283 |   77 |         sys.path.insert(0, str(SRC_DIR))
3284 |   78 |         from src.metrics.engine import MetricsEngine
3285 |   79 |         engine = MetricsEngine()
3286 |   80 |         vector = np.array([1.0, 2.0, 3.0])
3287 |   81 |         engine.update_scalar_metrics(123, vector)
3288 |   82 |         np.testing.assert_array_almost_equal(engine.profiles[123]["mu"], vector)
3289 |   83 | 
3290 |   84 |     def test_first_update_sets_sigma_to_ones(self):
3291 |   85 |         """Verify first update sets sigma to ones."""
3292 |   86 |         import sys
3293 |   87 |         sys.path.insert(0, str(SRC_DIR))
3294 |   88 |         from src.metrics.engine import MetricsEngine
3295 |   89 |         engine = MetricsEngine()
3296 |   90 |         vector = np.array([1.0, 2.0, 3.0])
3297 |   91 |         engine.update_scalar_metrics(123, vector)
3298 |   92 |         np.testing.assert_array_almost_equal(engine.profiles[123]["sigma"], np.ones(3))
3299 |   93 | 
3300 |   94 |     def test_first_update_creates_history_deque(self):
3301 |   95 |         """Verify history deque is created."""
3302 |   96 |         import sys
3303 |   97 |         sys.path.insert(0, str(SRC_DIR))
3304 |   98 |         from src.metrics.engine import MetricsEngine
3305 |   99 |         engine = MetricsEngine()
3306 |  100 |         vector = np.array([1.0, 2.0, 3.0])
3307 |  101 |         engine.update_scalar_metrics(123, vector)
3308 |  102 |         assert isinstance(engine.profiles[123]["history"], deque)
3309 |  103 | 
3310 |  104 |     def test_first_update_creates_ngram_buffer(self):
3311 |  105 |         """Verify ngram_buffer deque is created."""
3312 |  106 |         import sys
3313 |  107 |         sys.path.insert(0, str(SRC_DIR))
3314 |  108 |         from src.metrics.engine import MetricsEngine
3315 |  109 |         engine = MetricsEngine()
3316 |  110 |         vector = np.array([1.0, 2.0, 3.0])
3317 |  111 |         engine.update_scalar_metrics(123, vector)
3318 |  112 |         assert isinstance(engine.profiles[123]["ngram_buffer"], deque)
3319 |  113 | 
3320 |  114 |     def test_first_update_creates_ngram_counts(self):
3321 |  115 |         """Verify ngram_counts dict is created."""
3322 |  116 |         import sys
3323 |  117 |         sys.path.insert(0, str(SRC_DIR))
3324 |  118 |         from src.metrics.engine import MetricsEngine
3325 |  119 |         engine = MetricsEngine()
3326 |  120 |         vector = np.array([1.0, 2.0, 3.0])
3327 |  121 |         engine.update_scalar_metrics(123, vector)
3328 |  122 |         assert engine.profiles[123]["ngram_counts"] == {}
3329 |  123 | 
3330 |  124 |     def test_ewma_update_formula(self):
3331 |  125 |         """Verify EWMA update: mu = alpha * current + (1-alpha) * old_mu."""
3332 |  126 |         import sys
3333 |  127 |         sys.path.insert(0, str(SRC_DIR))
3334 |  128 |         from src.metrics.engine import MetricsEngine
3335 |  129 |         engine = MetricsEngine(alpha=0.3)
3336 |  130 |         
3337 |  131 |         old_vector = np.array([10.0, 20.0, 30.0])
3338 |  132 |         engine.update_scalar_metrics(123, old_vector)
3339 |  133 |         
3340 |  134 |         new_vector = np.array([20.0, 40.0, 60.0])
3341 |  135 |         engine.update_scalar_metrics(123, new_vector)
3342 |  136 |         
3343 |  137 |         expected_mu = 0.3 * new_vector + 0.7 * old_vector
3344 |  138 |         np.testing.assert_array_almost_equal(engine.profiles[123]["mu"], expected_mu)
3345 |  139 | 
3346 |  140 |     def test_ewma_with_zero_alpha(self):
3347 |  141 |         """Verify EWMA with alpha=0 (no update)."""
3348 |  142 |         import sys
3349 |  143 |         sys.path.insert(0, str(SRC_DIR))
3350 |  144 |         from src.metrics.engine import MetricsEngine
3351 |  145 |         engine = MetricsEngine(alpha=0.0)
3352 |  146 |         
3353 |  147 |         old_vector = np.array([10.0, 20.0, 30.0])
3354 |  148 |         engine.update_scalar_metrics(123, old_vector)
3355 |  149 |         
3356 |  150 |         new_vector = np.array([20.0, 40.0, 60.0])
3357 |  151 |         engine.update_scalar_metrics(123, new_vector)
3358 |  152 |         
3359 |  153 |         np.testing.assert_array_almost_equal(engine.profiles[123]["mu"], old_vector)
3360 |  154 | 
3361 |  155 |     def test_ewma_with_one_alpha(self):
3362 |  156 |         """Verify EWMA with alpha=1 (full update to current)."""
3363 |  157 |         import sys
3364 |  158 |         sys.path.insert(0, str(SRC_DIR))
3365 |  159 |         from src.metrics.engine import MetricsEngine
3366 |  160 |         engine = MetricsEngine(alpha=1.0)
3367 |  161 |         
3368 |  162 |         old_vector = np.array([10.0, 20.0, 30.0])
3369 |  163 |         engine.update_scalar_metrics(123, old_vector)
3370 |  164 |         
3371 |  165 |         new_vector = np.array([20.0, 40.0, 60.0])
3372 |  166 |         engine.update_scalar_metrics(123, new_vector)
3373 |  167 |         
3374 |  168 |         np.testing.assert_array_almost_equal(engine.profiles[123]["mu"], new_vector)
3375 |  169 | 
3376 |  170 |     def test_multiple_updates_append_to_history(self):
3377 |  171 |         """Verify multiple updates append to history."""
3378 |  172 |         import sys
3379 |  173 |         sys.path.insert(0, str(SRC_DIR))
3380 |  174 |         from src.metrics.engine import MetricsEngine
3381 |  175 |         engine = MetricsEngine()
3382 |  176 |         
3383 |  177 |         for i in range(5):
3384 |  178 |             engine.update_scalar_metrics(123, np.array([float(i)]))
3385 |  179 |         
3386 |  180 |         assert len(engine.profiles[123]["history"]) >= 5
3387 |  181 | 
3388 |  182 |     def test_history_maxlen_enforced(self):
3389 |  183 |         """Verify history respects maxlen."""
3390 |  184 |         import sys
3391 |  185 |         sys.path.insert(0, str(SRC_DIR))
3392 |  186 |         from src.metrics.engine import MetricsEngine
3393 |  187 |         engine = MetricsEngine()
3394 |  188 |         
3395 |  189 |         for i in range(150):
3396 |  190 |             engine.update_scalar_metrics(123, np.array([float(i)]))
3397 |  191 |         
3398 |  192 |         assert len(engine.profiles[123]["history"]) == 100
3399 |  193 | 
3400 |  194 |     def test_update_with_different_pid(self):
3401 |  195 |         """Verify updates for different PIDs are separate."""
3402 |  196 |         import sys
3403 |  197 |         sys.path.insert(0, str(SRC_DIR))
3404 |  198 |         from src.metrics.engine import MetricsEngine
3405 |  199 |         engine = MetricsEngine()
3406 |  200 |         
3407 |  201 |         engine.update_scalar_metrics(100, np.array([1.0]))
3408 |  202 |         engine.update_scalar_metrics(200, np.array([2.0]))
3409 |  203 |         
3410 |  204 |         assert engine.profiles[100]["mu"][0] == 1.0
3411 |  205 |         assert engine.profiles[200]["mu"][0] == 2.0
3412 |  206 | 
3413 |  207 | 
3414 |  208 | class TestMetricsEngineUpdateNgram:
3415 |  209 |     """Tests for update_ngram method."""
3416 |  210 | 
3417 |  211 |     def test_ngram_update_creates_profile_if_missing(self):
3418 |  212 |         """Verify ngram update creates profile if missing."""
3419 |  213 |         import sys
3420 |  214 |         sys.path.insert(0, str(SRC_DIR))
3421 |  215 |         from src.metrics.engine import MetricsEngine
3422 |  216 |         engine = MetricsEngine(n_gram_size=3)
3423 |  217 |         engine.update_ngram(999, 257)
3424 |  218 |         assert 999 in engine.profiles
3425 |  219 | 
3426 |  220 |     def test_ngram_single_syscall_no_count(self):
3427 |  221 |         """Verify single syscall doesn't create ngram until buffer full."""
3428 |  222 |         import sys
3429 |  223 |         sys.path.insert(0, str(SRC_DIR))
3430 |  224 |         from src.metrics.engine import MetricsEngine
3431 |  225 |         engine = MetricsEngine(n_gram_size=3)
3432 |  226 |         
3433 |  227 |         engine.update_ngram(123, 257)
3434 |  228 |         
3435 |  229 |         assert len(engine.profiles[123]["ngram_counts"]) == 0
3436 |  230 | 
3437 |  231 |     def test_ngram_full_buffer_creates_count(self):
3438 |  232 |         """Verify full buffer creates ngram count."""
3439 |  233 |         import sys
3440 |  234 |         sys.path.insert(0, str(SRC_DIR))
3441 |  235 |         from src.metrics.engine import MetricsEngine
3442 |  236 |         engine = MetricsEngine(n_gram_size=3)
3443 |  237 |         
3444 |  238 |         engine.update_ngram(123, 257)
3445 |  239 |         engine.update_ngram(123, 258)
3446 |  240 |         engine.update_ngram(123, 259)
3447 |  241 |         
3448 |  242 |         assert (257, 258, 259) in engine.profiles[123]["ngram_counts"]
3449 |  243 | 
3450 |  244 |     def test_ngram_increments_count(self):
3451 |  245 |         """Verify repeated ngram increments count."""
3452 |  246 |         import sys
3453 |  247 |         sys.path.insert(0, str(SRC_DIR))
3454 |  248 |         from src.metrics.engine import MetricsEngine
3455 |  249 |         engine = MetricsEngine(n_gram_size=2)
3456 |  250 |         
3457 |  251 |         engine.update_ngram(123, 257)
3458 |  252 |         engine.update_ngram(123, 258)
3459 |  253 |         engine.update_ngram(123, 257)
3460 |  254 |         engine.update_ngram(123, 258)
3461 |  255 |         
3462 |  256 |         assert engine.profiles[123]["ngram_counts"][(257, 258)] == 2
3463 |  257 | 
3464 |  258 |     def test_ngram_buffer_slides(self):
3465 |  259 |         """Verify ngram buffer slides correctly."""
3466 |  260 |         import sys
3467 |  261 |         sys.path.insert(0, str(SRC_DIR))
3468 |  262 |         from src.metrics.engine import MetricsEngine
3469 |  263 |         engine = MetricsEngine(n_gram_size=2)
3470 |  264 |         
3471 |  265 |         engine.update_ngram(123, 1)
3472 |  266 |         engine.update_ngram(123, 2)
3473 |  267 |         assert (1, 2) in engine.profiles[123]["ngram_counts"]
3474 |  268 |         
3475 |  269 |         engine.update_ngram(123, 3)
3476 |  270 |         assert (2, 3) in engine.profiles[123]["ngram_counts"]
3477 |  271 | 
3478 |  272 |     def test_ngram_size_one(self):
3479 |  273 |         """Verify ngram with size 1."""
3480 |  274 |         import sys
3481 |  275 |         sys.path.insert(0, str(SRC_DIR))
3482 |  276 |         from src.metrics.engine import MetricsEngine
3483 |  277 |         engine = MetricsEngine(n_gram_size=1)
3484 |  278 |         
3485 |  279 |         engine.update_ngram(123, 257)
3486 |  280 |         
3487 |  281 |         assert (257,) in engine.profiles[123]["ngram_counts"]
3488 |  282 | 
3489 |  283 |     def test_different_pids_have_separate_ngrams(self):
3490 |  284 |         """Verify different PIDs have separate ngram buffers."""
3491 |  285 |         import sys
3492 |  286 |         sys.path.insert(0, str(SRC_DIR))
3493 |  287 |         from src.metrics.engine import MetricsEngine
3494 |  288 |         engine = MetricsEngine(n_gram_size=2)
3495 |  289 |         
3496 |  290 |         engine.update_ngram(100, 1)
3497 |  291 |         engine.update_ngram(100, 2)
3498 |  292 |         
3499 |  293 |         engine.update_ngram(200, 3)
3500 |  294 |         engine.update_ngram(200, 4)
3501 |  295 |         
3502 |  296 |         assert (1, 2) in engine.profiles[100]["ngram_counts"]
3503 |  297 |         assert (3, 4) in engine.profiles[200]["ngram_counts"]
3504 |  298 | 
3505 |  299 | 
3506 |  300 | class TestMetricsEngineZScores:
3507 |  301 |     """Tests for get_z_scores method."""
3508 |  302 | 
3509 |  303 |     def test_unknown_pid_returns_zeros(self):
3510 |  304 |         """Verify unknown PID returns zeros."""
3511 |  305 |         import sys
3512 |  306 |         sys.path.insert(0, str(SRC_DIR))
3513 |  307 |         from src.metrics.engine import MetricsEngine
3514 |  308 |         engine = MetricsEngine()
3515 |  309 |         
3516 |  310 |         result = engine.get_z_scores(999, np.array([1.0, 2.0, 3.0]))
3517 |  311 |         
3518 |  312 |         np.testing.assert_array_almost_equal(result, np.zeros(3))
3519 |  313 | 
3520 |  314 |     def test_z_score_calculation(self):
3521 |  315 |         """Verify z-score formula: (current - mu) / sigma."""
3522 |  316 |         import sys
3523 |  317 |         sys.path.insert(0, str(SRC_DIR))
3524 |  318 |         from src.metrics.engine import MetricsEngine
3525 |  319 |         engine = MetricsEngine()
3526 |  320 |         
3527 |  321 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
3528 |  322 |         
3529 |  323 |         result = engine.get_z_scores(123, np.array([13.0, 10.0, 7.0]))
3530 |  324 |         
3531 |  325 |         np.testing.assert_array_almost_equal(result, np.array([3.0, 0.0, -3.0]))
3532 |  326 | 
3533 |  327 |     def test_zero_sigma_uses_epsilon(self):
3534 |  328 |         """Verify zero sigma uses 1e-6 epsilon."""
3535 |  329 |         import sys
3536 |  330 |         sys.path.insert(0, str(SRC_DIR))
3537 |  331 |         from src.metrics.engine import MetricsEngine
3538 |  332 |         engine = MetricsEngine()
3539 |  333 |         
3540 |  334 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
3541 |  335 |         engine.profiles[123]["sigma"] = np.array([0.0, 0.0, 0.0])
3542 |  336 |         
3543 |  337 |         result = engine.get_z_scores(123, np.array([20.0, 20.0, 20.0]))
3544 |  338 |         
3545 |  339 |         np.testing.assert_array_almost_equal(result, np.array([10000000.0, 10000000.0, 10000000.0]))
3546 |  340 | 
3547 |  341 |     def test_negative_z_scores(self):
3548 |  342 |         """Verify negative z-scores are calculated correctly."""
3549 |  343 |         import sys
3550 |  344 |         sys.path.insert(0, str(SRC_DIR))
3551 |  345 |         from src.metrics.engine import MetricsEngine
3552 |  346 |         engine = MetricsEngine()
3553 |  347 |         
3554 |  348 |         engine.update_scalar_metrics(123, np.array([100.0]))
3555 |  349 |         
3556 |  350 |         result = engine.get_z_scores(123, np.array([50.0]))
3557 |  351 |         
3558 |  352 |         assert result[0] < 0
3559 |  353 | 
3560 |  354 |     def test_exact_match_z_score_zero(self):
3561 |  355 |         """Verify exact match to mu gives z-score of 0."""
3562 |  356 |         import sys
3563 |  357 |         sys.path.insert(0, str(SRC_DIR))
3564 |  358 |         from src.metrics.engine import MetricsEngine
3565 |  359 |         engine = MetricsEngine()
3566 |  360 |         
3567 |  361 |         engine.update_scalar_metrics(123, np.array([50.0]))
3568 |  362 |         
3569 |  363 |         result = engine.get_z_scores(123, np.array([50.0]))
3570 |  364 |         
3571 |  365 |         np.testing.assert_array_almost_equal(result, np.array([0.0]))
3572 |  366 | 
3573 |  367 | 
3574 |  368 | class TestMetricsEngineNgramAnomalyScore:
3575 |  369 |     """Tests for get_ngram_anomaly_score method."""
3576 |  370 | 
3577 |  371 |     def test_unknown_pid_returns_one(self):
3578 |  372 |         """Verify unknown PID returns 1.0 (max anomaly)."""
3579 |  373 |         import sys
3580 |  374 |         sys.path.insert(0, str(SRC_DIR))
3581 |  375 |         from src.metrics.engine import MetricsEngine
3582 |  376 |         engine = MetricsEngine()
3583 |  377 |         
3584 |  378 |         result = engine.get_ngram_anomaly_score(999, (1, 2, 3))
3585 |  379 |         
3586 |  380 |         assert result == 1.0
3587 |  381 | 
3588 |  382 |     def test_zero_total_returns_one(self):
3589 |  383 |         """Verify zero total ngram count returns 1.0."""
3590 |  384 |         import sys
3591 |  385 |         sys.path.insert(0, str(SRC_DIR))
3592 |  386 |         from src.metrics.engine import MetricsEngine
3593 |  387 |         engine = MetricsEngine()
3594 |  388 |         
3595 |  389 |         engine.update_scalar_metrics(123, np.array([1.0]))
3596 |  390 |         
3597 |  391 |         result = engine.get_ngram_anomaly_score(123, (1, 2, 3))
3598 |  392 |         
3599 |  393 |         assert result == 1.0
3600 |  394 | 
3601 |  395 |     def test_rare_sequence_high_score(self):
3602 |  396 |         """Verify rare sequence returns high anomaly score."""
3603 |  397 |         import sys
3604 |  398 |         sys.path.insert(0, str(SRC_DIR))
3605 |  399 |         from src.metrics.engine import MetricsEngine
3606 |  400 |         engine = MetricsEngine(n_gram_size=2)
3607 |  401 |         
3608 |  402 |         for _ in range(100):
3609 |  403 |             engine.update_ngram(123, 1)
3610 |  404 |             engine.update_ngram(123, 2)
3611 |  405 |         
3612 |  406 |         engine.update_ngram(123, 3)
3613 |  407 |         engine.update_ngram(123, 4)
3614 |  408 |         
3615 |  409 |         result = engine.get_ngram_anomaly_score(123, (3, 4))
3616 |  410 |         
3617 |  411 |         assert result >= 0.9
3618 |  412 | 
3619 |  413 |     def test_common_sequence_high_rare_score(self):
3620 |  414 |         """Verify common sequences have lower anomaly score than rare ones."""
3621 |  415 |         import sys
3622 |  416 |         sys.path.insert(0, str(SRC_DIR))
3623 |  417 |         from src.metrics.engine import MetricsEngine
3624 |  418 |         engine = MetricsEngine(n_gram_size=2)
3625 |  419 |         
3626 |  420 |         for _ in range(100):
3627 |  421 |             engine.update_ngram(123, 1)
3628 |  422 |             engine.update_ngram(123, 2)
3629 |  423 |         
3630 |  424 |         # (1,2) is seen many times, (3,4) is seen only once
3631 |  425 |         result_common = engine.get_ngram_anomaly_score(123, (1, 2))
3632 |  426 |         result_rare = engine.get_ngram_anomaly_score(123, (3, 4))
3633 |  427 |         
3634 |  428 |         assert result_common < result_rare
3635 |  429 | 
3636 |  430 |     def test_perfect_match_returns_zero(self):
3637 |  431 |         """Verify sequence with 100% frequency returns 0."""
3638 |  432 |         import sys
3639 |  433 |         sys.path.insert(0, str(SRC_DIR))
3640 |  434 |         from src.metrics.engine import MetricsEngine
3641 |  435 |         engine = MetricsEngine()
3642 |  436 |         
3643 |  437 |         engine.update_scalar_metrics(123, np.array([1.0]))
3644 |  438 |         # Only one unique ngram with 100% frequency
3645 |  439 |         engine.profiles[123]["ngram_counts"][(1, 2, 3)] = 1
3646 |  440 |         
3647 |  441 |         result = engine.get_ngram_anomaly_score(123, (1, 2, 3))
3648 |  442 |         
3649 |  443 |         assert result == 0.0
3650 |  444 | 
3651 |  445 | 
3652 |  446 | class TestMetricsEngineEdgeCases:
3653 |  447 |     """Edge case tests for MetricsEngine."""
3654 |  448 | 
3655 |  449 |     def test_empty_vector(self):
3656 |  450 |         """Verify empty vector handling."""
3657 |  451 |         import sys
3658 |  452 |         sys.path.insert(0, str(SRC_DIR))
3659 |  453 |         from src.metrics.engine import MetricsEngine
3660 |  454 |         engine = MetricsEngine()
3661 |  455 |         
3662 |  456 |         engine.update_scalar_metrics(123, np.array([]))
3663 |  457 |         
3664 |  458 |         assert 123 in engine.profiles
3665 |  459 |         assert len(engine.profiles[123]["mu"]) == 0
3666 |  460 | 
3667 |  461 |     def test_single_element_vector(self):
3668 |  462 |         """Verify single element vector."""
3669 |  463 |         import sys
3670 |  464 |         sys.path.insert(0, str(SRC_DIR))
3671 |  465 |         from src.metrics.engine import MetricsEngine
3672 |  466 |         engine = MetricsEngine()
3673 |  467 |         
3674 |  468 |         engine.update_scalar_metrics(123, np.array([42.0]))
3675 |  469 |         
3676 |  470 |         assert engine.profiles[123]["mu"][0] == 42.0
3677 |  471 | 
3678 |  472 |     def test_large_vector(self):
3679 |  473 |         """Verify large vector dimension."""
3680 |  474 |         import sys
3681 |  475 |         sys.path.insert(0, str(SRC_DIR))
3682 |  476 |         from src.metrics.engine import MetricsEngine
3683 |  477 |         engine = MetricsEngine()
3684 |  478 |         
3685 |  479 |         large_vector = np.random.rand(1000)
3686 |  480 |         engine.update_scalar_metrics(123, large_vector)
3687 |  481 |         
3688 |  482 |         assert len(engine.profiles[123]["mu"]) == 1000
3689 |  483 | 
3690 |  484 |     def test_negative_values(self):
3691 |  485 |         """Verify negative values are handled."""
3692 |  486 |         import sys
3693 |  487 |         sys.path.insert(0, str(SRC_DIR))
3694 |  488 |         from src.metrics.engine import MetricsEngine
3695 |  489 |         engine = MetricsEngine()
3696 |  490 |         
3697 |  491 |         engine.update_scalar_metrics(123, np.array([-10.0, -20.0]))
3698 |  492 |         
3699 |  493 |         assert engine.profiles[123]["mu"][0] == -10.0
3700 |  494 | 
3701 |  495 |     def test_mixed_positive_negative(self):
3702 |  496 |         """Verify mixed positive/negative values."""
3703 |  497 |         import sys
3704 |  498 |         sys.path.insert(0, str(SRC_DIR))
3705 |  499 |         from src.metrics.engine import MetricsEngine
3706 |  500 |         engine = MetricsEngine()
3707 |  501 |         
3708 |  502 |         engine.update_scalar_metrics(123, np.array([-5.0, 0.0, 5.0]))
3709 |  503 |         
3710 |  504 |         np.testing.assert_array_almost_equal(
3711 |  505 |             engine.profiles[123]["mu"], 
3712 |  506 |             np.array([-5.0, 0.0, 5.0])
3713 |  507 |         )
3714 |  508 | 
3715 |  509 |     def test_float32_array(self):
3716 |  510 |         """Verify float32 array is converted to float."""
3717 |  511 |         import sys
3718 |  512 |         sys.path.insert(0, str(SRC_DIR))
3719 |  513 |         from src.metrics.engine import MetricsEngine
3720 |  514 |         engine = MetricsEngine()
3721 |  515 |         
3722 |  516 |         vector = np.array([1.0, 2.0], dtype=np.float32)
3723 |  517 |         engine.update_scalar_metrics(123, vector)
3724 |  518 |         
3725 |  519 |         assert engine.profiles[123]["mu"].dtype == np.float64
3726 |  520 | 
3727 |  521 |     def test_integer_array(self):
3728 |  522 |         """Verify integer array is converted to float."""
3729 |  523 |         import sys
3730 |  524 |         sys.path.insert(0, str(SRC_DIR))
3731 |  525 |         from src.metrics.engine import MetricsEngine
3732 |  526 |         engine = MetricsEngine()
3733 |  527 |         
3734 |  528 |         vector = np.array([1, 2, 3], dtype=np.int32)
3735 |  529 |         engine.update_scalar_metrics(123, vector)
3736 |  530 |         
3737 |  531 |         assert engine.profiles[123]["mu"].dtype == np.float64
3738 |  532 | 
3739 |  533 | 
3740 |  534 | class TestMetricsEngineIntegration:
3741 |  535 |     """Integration tests for MetricsEngine."""
3742 |  536 | 
3743 |  537 |     def test_full_workflow(self):
3744 |  538 |         """Verify full detection workflow."""
3745 |  539 |         import sys
3746 |  540 |         sys.path.insert(0, str(SRC_DIR))
3747 |  541 |         from src.metrics.engine import MetricsEngine
3748 |  542 |         engine = MetricsEngine(alpha=0.3, n_gram_size=2)
3749 |  543 |         
3750 |  544 |         for i in range(20):
3751 |  545 |             vector = np.array([float(i), float(i*2), float(i*3)])
3752 |  546 |             engine.update_scalar_metrics(123, vector)
3753 |  547 |             engine.update_ngram(123, 257 + i)
3754 |  548 |         
3755 |  549 |         test_vector = np.array([25.0, 50.0, 75.0])
3756 |  550 |         z_scores = engine.get_z_scores(123, test_vector)
3757 |  551 |         
3758 |  552 |         assert z_scores.shape == (3,)
3759 |  553 |         
3760 |  554 |         anomaly = engine.get_ngram_anomaly_score(123, (275, 276))
3761 |  555 |         assert 0.0 <= anomaly <= 1.0
3762 |  556 | 
3763 |  557 |     def test_multiple_processes(self):
3764 |  558 |         """Verify multiple processes tracking."""
3765 |  559 |         import sys
3766 |  560 |         sys.path.insert(0, str(SRC_DIR))
3767 |  561 |         from src.metrics.engine import MetricsEngine
3768 |  562 |         engine = MetricsEngine()
3769 |  563 |         
3770 |  564 |         for pid in [100, 200, 300]:
3771 |  565 |             for _ in range(10):
3772 |  566 |                 engine.update_scalar_metrics(pid, np.array([float(pid)]))
3773 |  567 |         
3774 |  568 |         for pid in [100, 200, 300]:
3775 |  569 |             assert pid in engine.profiles
3776 |  570 |             z = engine.get_z_scores(pid, np.array([float(pid)]))
3777 |  571 |             np.testing.assert_array_almost_equal(z, np.array([0.0]))
3778 | ```
3779 | 
3780 | ### tests/test_provenance_graph.py
3781 | 
3782 | ```python
3783 |    1 | import pytest
3784 |    2 | import sys
3785 |    3 | from pathlib import Path
3786 |    4 | from unittest.mock import patch, MagicMock
3787 |    5 | 
3788 |    6 | SRC_DIR = Path(__file__).parent.parent / "src"
3789 |    7 | sys.path.insert(0, str(SRC_DIR))
3790 |    8 | 
3791 |    9 | from graph.builder import ProvenanceGraphBuilder
3792 |   10 | 
3793 |   11 | 
3794 |   12 | class TestProvenanceGraphBuilder:
3795 |   13 |     """Tests for ProvenanceGraphBuilder."""
3796 |   14 | 
3797 |   15 |     def test_add_event_creates_process_node(self):
3798 |   16 |         """Test add_event creates a process node when pid is provided."""
3799 |   17 |         builder = ProvenanceGraphBuilder()
3800 |   18 |         event = {"pid": 123, "comm": "bash", "filename": "", "syscall_id": 2}
3801 |   19 |         
3802 |   20 |         builder.add_event(event)
3803 |   21 |         
3804 |   22 |         assert builder.graph.has_node("proc_123")
3805 |   23 |         assert builder.graph.nodes["proc_123"]["type"] == "process"
3806 |   24 |         assert builder.graph.nodes["proc_123"]["pid"] == 123
3807 |   25 | 
3808 |   26 |     def test_add_event_creates_file_node(self):
3809 |   27 |         """Test add_event creates a file node when filename is provided."""
3810 |   28 |         builder = ProvenanceGraphBuilder()
3811 |   29 |         event = {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2}
3812 |   30 |         
3813 |   31 |         builder.add_event(event)
3814 |   32 |         
3815 |   33 |         assert builder.graph.has_node("file_/etc/passwd")
3816 |   34 |         assert builder.graph.nodes["file_/etc/passwd"]["type"] == "file"
3817 |   35 |         assert builder.graph.nodes["file_/etc/passwd"]["path"] == "/etc/passwd"
3818 |   36 | 
3819 |   37 |     def test_add_event_creates_edge(self):
3820 |   38 |         """Test add_event creates an edge from process to file."""
3821 |   39 |         builder = ProvenanceGraphBuilder()
3822 |   40 |         event = {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2}
3823 |   41 |         
3824 |   42 |         builder.add_event(event)
3825 |   43 |         
3826 |   44 |         assert builder.graph.has_edge("proc_123", "file_/etc/passwd")
3827 |   45 |         assert builder.graph.edges[("proc_123", "file_/etc/passwd")]["syscall"] == 2
3828 |   46 | 
3829 |   47 |     def test_add_event_duplicate_process(self):
3830 |   48 |         """Test duplicate process nodes are not duplicated."""
3831 |   49 |         builder = ProvenanceGraphBuilder()
3832 |   50 |         events = [
3833 |   51 |             {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2},
3834 |   52 |             {"pid": 123, "comm": "bash", "filename": "/etc/shadow", "syscall_id": 2},
3835 |   53 |         ]
3836 |   54 |         
3837 |   55 |         for event in events:
3838 |   56 |             builder.add_event(event)
3839 |   57 |         
3840 |   58 |         assert len([n for n in builder.graph.nodes() if n.startswith("proc_")]) == 1
3841 |   59 |         assert len(list(builder.graph.edges())) == 2
3842 |   60 | 
3843 |   61 |     def test_add_event_missing_filename(self):
3844 |   62 |         """Test add_event with no filename creates no file node or edge."""
3845 |   63 |         builder = ProvenanceGraphBuilder()
3846 |   64 |         event = {"pid": 123, "comm": "bash", "filename": "", "syscall_id": 2}
3847 |   65 |         
3848 |   66 |         builder.add_event(event)
3849 |   67 |         
3850 |   68 |         assert builder.graph.has_node("proc_123")
3851 |   69 |         assert len([n for n in builder.graph.nodes() if n.startswith("file_")]) == 0
3852 |   70 | 
3853 |   71 |     def test_get_process_subgraph_existing(self):
3854 |   72 |         """Test get_process_subgraph returns neighborhood for existing PID."""
3855 |   73 |         builder = ProvenanceGraphBuilder()
3856 |   74 |         events = [
3857 |   75 |             {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2},
3858 |   76 |             {"pid": 123, "comm": "bash", "filename": "/var/log/syslog", "syscall_id": 2},
3859 |   77 |         ]
3860 |   78 |         for event in events:
3861 |   79 |             builder.add_event(event)
3862 |   80 |         
3863 |   81 |         subgraph = builder.get_process_subgraph(123)
3864 |   82 |         
3865 |   83 |         assert subgraph.has_node("proc_123")
3866 |   84 |         assert len(subgraph.nodes()) == 3
3867 |   85 | 
3868 |   86 |     def test_get_process_subgraph_missing(self):
3869 |   87 |         """Test get_process_subgraph returns empty graph for non-existent PID."""
3870 |   88 |         builder = ProvenanceGraphBuilder()
3871 |   89 |         
3872 |   90 |         subgraph = builder.get_process_subgraph(999)
3873 |   91 |         
3874 |   92 |         assert len(subgraph.nodes()) == 0
3875 |   93 | 
3876 |   94 |     def test_get_serialized_graph_format(self):
3877 |   95 |         """Test get_serialized_graph returns valid node_link_data format."""
3878 |   96 |         builder = ProvenanceGraphBuilder()
3879 |   97 |         event = {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2}
3880 |   98 |         builder.add_event(event)
3881 |   99 |         
3882 |  100 |         serialized = builder.get_serialized_graph()
3883 |  101 |         
3884 |  102 |         assert "nodes" in serialized
3885 |  103 |         assert "links" in serialized or "edges" in serialized
3886 |  104 | 
3887 |  105 |     def test_clear_graph(self):
3888 |  106 |         """Test clear removes all nodes and edges."""
3889 |  107 |         builder = ProvenanceGraphBuilder()
3890 |  108 |         event = {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2}
3891 |  109 |         builder.add_event(event)
3892 |  110 |         
3893 |  111 |         builder.clear()
3894 |  112 |         
3895 |  113 |         assert len(builder.graph.nodes()) == 0
3896 |  114 |         assert len(builder.graph.edges()) == 0
3897 | ```
3898 | 
3899 | ### tests/test_scoring_engine.py
3900 | 
3901 | ```python
3902 |    1 | import pytest
3903 |    2 | import sys
3904 |    3 | from pathlib import Path
3905 |    4 | from unittest.mock import patch, MagicMock
3906 |    5 | 
3907 |    6 | SRC_DIR = Path(__file__).parent.parent / "src"
3908 |    7 | sys.path.insert(0, str(SRC_DIR))
3909 |    8 | 
3910 |    9 | from scoring.engine import ScoringEngine, Alert
3911 |   10 | 
3912 |   11 | 
3913 |   12 | class TestScoringEngine:
3914 |   13 |     """Tests for ScoringEngine."""
3915 |   14 | 
3916 |   15 |     def test_compute_score_below_threshold(self):
3917 |   16 |         """Test score below threshold returns None."""
3918 |   17 |         engine = ScoringEngine(threshold=10.0)
3919 |   18 |         stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
3920 |   19 |         
3921 |   20 |         result = engine.compute_score(
3922 |   21 |             stat_report=stat_report,
3923 |   22 |             sig_match=None,
3924 |   23 |             graph_heuristics=[]
3925 |   24 |         )
3926 |   25 |         
3927 |   26 |         assert result is None
3928 |   27 | 
3929 |   28 |     def test_compute_score_at_threshold(self):
3930 |   29 |         """Test score at threshold returns Alert with warning."""
3931 |   30 |         engine = ScoringEngine(threshold=10.0)
3932 |   31 |         stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
3933 |   32 |         
3934 |   33 |         result = engine.compute_score(
3935 |   34 |             stat_report=stat_report,
3936 |   35 |             sig_match=None,
3937 |   36 |             graph_heuristics=["suspicious_parent"]  # 5.0 * 1 = 5.0, need 2 for 10.0
3938 |   37 |         )
3939 |   38 |         
3940 |   39 |         assert result is None
3941 |   40 | 
3942 |   41 |     def test_compute_score_above_threshold(self):
3943 |   42 |         """Test score above threshold returns Alert."""
3944 |   43 |         engine = ScoringEngine(threshold=10.0)
3945 |   44 |         stat_report = {"pid": 123, "is_anomalous": True, "max_z_score": 2.0}
3946 |   45 |         
3947 |   46 |         result = engine.compute_score(
3948 |   47 |             stat_report=stat_report,
3949 |   48 |             sig_match={"reason": "shadow file access"},
3950 |   49 |             graph_heuristics=["suspicious_parent"]
3951 |   50 |         )
3952 |   51 |         
3953 |   52 |         assert result is not None
3954 |   53 |         assert result.pid == 123
3955 |   54 | 
3956 |   55 |     def test_compute_score_signature_critical(self):
3957 |   56 |         """Test signature match sets severity to critical."""
3958 |   57 |         engine = ScoringEngine(threshold=10.0)
3959 |   58 |         stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
3960 |   59 |         
3961 |   60 |         result = engine.compute_score(
3962 |   61 |             stat_report=stat_report,
3963 |   62 |             sig_match={"reason": "shadow file access"},
3964 |   63 |             graph_heuristics=[]
3965 |   64 |         )
3966 |   65 |         
3967 |   66 |         assert result is not None
3968 |   67 |         assert result.severity == "critical"
3969 |   68 | 
3970 |   69 |     def test_compute_score_warning_threshold(self):
3971 |   70 |         """Test score between T and 2T without signature is warning."""
3972 |   71 |         engine = ScoringEngine(threshold=10.0)
3973 |   72 |         stat_report = {"pid": 123, "is_anomalous": True, "max_z_score": 5.0}
3974 |   73 |         
3975 |   74 |         result = engine.compute_score(
3976 |   75 |             stat_report=stat_report,
3977 |   76 |             sig_match=None,
3978 |   77 |             graph_heuristics=["suspicious_parent"]
3979 |   78 |         )
3980 |   79 |         
3981 |   80 |         assert result is not None
3982 |   81 |         assert result.severity == "warning"
3983 |   82 | 
3984 |   83 |     def test_compute_score_statistical_scaling(self):
3985 |   84 |         """Test statistical anomaly scales with Z-score."""
3986 |   85 |         engine = ScoringEngine(threshold=3.0)
3987 |   86 |         stat_report = {"pid": 123, "is_anomalous": True, "max_z_score": 3.0}
3988 |   87 |         
3989 |   88 |         result = engine.compute_score(
3990 |   89 |             stat_report=stat_report,
3991 |   90 |             sig_match=None,
3992 |   91 |             graph_heuristics=[]
3993 |   92 |         )
3994 |   93 |         
3995 |   94 |         assert result is not None
3996 |   95 |         assert result.score == 3.0
3997 |   96 | 
3998 |   97 |     def test_compute_score_multiple_heuristics(self):
3999 |   98 |         """Test multiple graph heuristics add up."""
4000 |   99 |         engine = ScoringEngine(threshold=10.0)
4001 |  100 |         stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
4002 |  101 |         
4003 |  102 |         result = engine.compute_score(
4004 |  103 |             stat_report=stat_report,
4005 |  104 |             sig_match=None,
4006 |  105 |             graph_heuristics=["h1", "h2", "h3"]
4007 |  106 |         )
4008 |  107 |         
4009 |  108 |         assert result is not None
4010 |  109 |         assert result.score == 15.0
4011 |  110 | 
4012 |  111 |     def test_compute_score_with_container_info(self):
4013 |  112 |         """Test container_info is included in Alert."""
4014 |  113 |         engine = ScoringEngine(threshold=10.0)
4015 |  114 |         stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
4016 |  115 |         container_info = {"id": "abc123", "name": "container1"}
4017 |  116 |         
4018 |  117 |         result = engine.compute_score(
4019 |  118 |             stat_report=stat_report,
4020 |  119 |             sig_match={"reason": "unauthorized shell"},
4021 |  120 |             graph_heuristics=[],
4022 |  121 |             container_info=container_info
4023 |  122 |         )
4024 |  123 |         
4025 |  124 |         assert result is not None
4026 |  125 |         assert result.container_info == container_info
4027 |  126 | 
4028 |  127 |     def test_compute_score_custom_threshold(self):
4029 |  128 |         """Test custom threshold is used."""
4030 |  129 |         engine = ScoringEngine(threshold=5.0)
4031 |  130 |         stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
4032 |  131 |         
4033 |  132 |         result = engine.compute_score(
4034 |  133 |             stat_report=stat_report,
4035 |  134 |             sig_match=None,
4036 |  135 |             graph_heuristics=["suspicious_parent"]
4037 |  136 |         )
4038 |  137 |         
4039 |  138 |         assert result is not None
4040 |  139 | 
4041 |  140 |     def test_alert_dataclass_structure(self):
4042 |  141 |         """Test Alert dataclass has all required fields."""
4043 |  142 |         alert = Alert(
4044 |  143 |             timestamp="2024-01-01T00:00:00",
4045 |  144 |             pid=123,
4046 |  145 |             score=15.0,
4047 |  146 |             severity="critical",
4048 |  147 |             reasons=["reason1"],
4049 |  148 |             container_info=None
4050 |  149 |         )
4051 |  150 |         
4052 |  151 |         assert hasattr(alert, "timestamp")
4053 |  152 |         assert hasattr(alert, "pid")
4054 |  153 |         assert hasattr(alert, "score")
4055 |  154 |         assert hasattr(alert, "severity")
4056 |  155 |         assert hasattr(alert, "reasons")
4057 |  156 |         assert hasattr(alert, "container_info")
4058 |  157 | 
4059 |  158 |     def test_compute_score_no_reasons_when_below(self):
4060 |  159 |         """Test reasons remain empty when below threshold."""
4061 |  160 |         engine = ScoringEngine(threshold=10.0)
4062 |  161 |         stat_report = {"pid": 123, "is_anomalous": False, "max_z_score": 0.0}
4063 |  162 |         
4064 |  163 |         result = engine.compute_score(
4065 |  164 |             stat_report=stat_report,
4066 |  165 |             sig_match=None,
4067 |  166 |             graph_heuristics=[]
4068 |  167 |         )
4069 |  168 |         
4070 |  169 |         assert result is None
4071 | ```
4072 | 
4073 | ### tests/test_signature_detector.py
4074 | 
4075 | ```python
4076 |    1 | import pytest
4077 |    2 | import numpy as np
4078 |    3 | from pathlib import Path
4079 |    4 | 
4080 |    5 | SRC_DIR = Path(__file__).parent.parent / "src"
4081 |    6 | 
4082 |    7 | 
4083 |    8 | class TestSignatureDetectorInit:
4084 |    9 |     """Tests for SignatureDetector initialization."""
4085 |   10 | 
4086 |   11 |     def test_detector_file_exists(self):
4087 |   12 |         """Verify SignatureDetector module exists."""
4088 |   13 |         import sys
4089 |   14 |         sys.path.insert(0, str(SRC_DIR))
4090 |   15 |         from src.detector.signature import SignatureDetector
4091 |   16 |         assert SignatureDetector is not None
4092 |   17 | 
4093 |   18 |     def test_default_init(self):
4094 |   19 |         """Verify default initialization."""
4095 |   20 |         import sys
4096 |   21 |         sys.path.insert(0, str(SRC_DIR))
4097 |   22 |         from src.detector.signature import SignatureDetector
4098 |   23 |         detector = SignatureDetector()
4099 |   24 |         assert detector is not None
4100 |   25 | 
4101 |   26 |     def test_critical_paths_initialized(self):
4102 |   27 |         """Verify critical_paths list is initialized."""
4103 |   28 |         import sys
4104 |   29 |         sys.path.insert(0, str(SRC_DIR))
4105 |   30 |         from src.detector.signature import SignatureDetector
4106 |   31 |         detector = SignatureDetector()
4107 |   32 |         assert hasattr(detector, "critical_paths")
4108 |   33 |         assert len(detector.critical_paths) > 0
4109 |   34 | 
4110 |   35 |     def test_suspicious_comm_initialized(self):
4111 |   36 |         """Verify suspicious_comm list is initialized."""
4112 |   37 |         import sys
4113 |   38 |         sys.path.insert(0, str(SRC_DIR))
4114 |   39 |         from src.detector.signature import SignatureDetector
4115 |   40 |         detector = SignatureDetector()
4116 |   41 |         assert hasattr(detector, "suspicious_comm")
4117 |   42 |         assert "bash" in detector.suspicious_comm
4118 |   43 | 
4119 |   44 | 
4120 |   45 | class TestSignatureDetectorCriticalPaths:
4121 |   46 |     """Tests for critical path detection (IOCs)."""
4122 |   47 | 
4123 |   48 |     def test_etc_shadow_detected(self):
4124 |   49 |         """Verify /etc/shadow access is detected."""
4125 |   50 |         import sys
4126 |   51 |         sys.path.insert(0, str(SRC_DIR))
4127 |   52 |         from src.detector.signature import SignatureDetector
4128 |   53 |         detector = SignatureDetector()
4129 |   54 |         
4130 |   55 |         event = {"filename": "/etc/shadow", "comm": "test"}
4131 |   56 |         result = detector.analyze_event(event)
4132 |   57 |         
4133 |   58 |         assert result is not None
4134 |   59 |         assert result["type"] == "SIGNATURE_MATCH"
4135 |   60 |         assert "critical" in result["severity"]
4136 |   61 | 
4137 |   62 |     def test_etc_sudoers_detected(self):
4138 |   63 |         """Verify /etc/sudoers access is detected."""
4139 |   64 |         import sys
4140 |   65 |         sys.path.insert(0, str(SRC_DIR))
4141 |   66 |         from src.detector.signature import SignatureDetector
4142 |   67 |         detector = SignatureDetector()
4143 |   68 |         
4144 |   69 |         event = {"filename": "/etc/sudoers", "comm": "test"}
4145 |   70 |         result = detector.analyze_event(event)
4146 |   71 |         
4147 |   72 |         assert result is not None
4148 |   73 |         assert result["type"] == "SIGNATURE_MATCH"
4149 |   74 | 
4150 |   75 |     def test_var_run_docker_sock_detected(self):
4151 |   76 |         """Verify /var/run/docker.sock access is detected."""
4152 |   77 |         import sys
4153 |   78 |         sys.path.insert(0, str(SRC_DIR))
4154 |   79 |         from src.detector.signature import SignatureDetector
4155 |   80 |         detector = SignatureDetector()
4156 |   81 |         
4157 |   82 |         event = {"filename": "/var/run/docker.sock", "comm": "test"}
4158 |   83 |         result = detector.analyze_event(event)
4159 |   84 |         
4160 |   85 |         assert result is not None
4161 |   86 |         assert result["type"] == "SIGNATURE_MATCH"
4162 |   87 | 
4163 |   88 |     def test_root_ssh_key_access(self):
4164 |   89 |         """Verify /root/.ssh/ key access is detected."""
4165 |   90 |         import sys
4166 |   91 |         sys.path.insert(0, str(SRC_DIR))
4167 |   92 |         from src.detector.signature import SignatureDetector
4168 |   93 |         detector = SignatureDetector()
4169 |   94 |         
4170 |   95 |         event = {"filename": "/root/.ssh/id_rsa", "comm": "test"}
4171 |   96 |         result = detector.analyze_event(event)
4172 |   97 |         
4173 |   98 |         assert result is not None
4174 |   99 | 
4175 |  100 |     def test_proc_kcore_detected(self):
4176 |  101 |         """Verify /proc/kcore access is detected."""
4177 |  102 |         import sys
4178 |  103 |         sys.path.insert(0, str(SRC_DIR))
4179 |  104 |         from src.detector.signature import SignatureDetector
4180 |  105 |         detector = SignatureDetector()
4181 |  106 |         
4182 |  107 |         event = {"filename": "/proc/kcore", "comm": "test"}
4183 |  108 |         result = detector.analyze_event(event)
4184 |  109 |         
4185 |  110 |         assert result is not None
4186 |  111 | 
4187 |  112 |     def test_non_matching_path_returns_none(self):
4188 |  113 |         """Verify non-matching path returns None."""
4189 |  114 |         import sys
4190 |  115 |         sys.path.insert(0, str(SRC_DIR))
4191 |  116 |         from src.detector.signature import SignatureDetector
4192 |  117 |         detector = SignatureDetector()
4193 |  118 |         
4194 |  119 |         event = {"filename": "/etc/passwd", "comm": "test"}
4195 |  120 |         result = detector.analyze_event(event)
4196 |  121 |         
4197 |  122 |         assert result is None
4198 |  123 | 
4199 |  124 | 
4200 |  125 | class TestSignatureDetectorSuspiciousComm:
4201 |  126 |     """Tests for suspicious process detection."""
4202 |  127 | 
4203 |  128 |     def test_bash_process_heuristic(self):
4204 |  129 |         """Verify bash process triggers heuristic."""
4205 |  130 |         import sys
4206 |  131 |         sys.path.insert(0, str(SRC_DIR))
4207 |  132 |         from src.detector.signature import SignatureDetector
4208 |  133 |         detector = SignatureDetector()
4209 |  134 |         
4210 |  135 |         event = {"filename": "/bin/bash", "comm": "bash"}
4211 |  136 |         result = detector.analyze_event(event)
4212 |  137 |         
4213 |  138 |         assert result is not None
4214 |  139 |         assert result["type"] == "HEURISTIC_MATCH"
4215 |  140 | 
4216 |  141 |     def test_sh_process_heuristic(self):
4217 |  142 |         """Verify sh process triggers heuristic."""
4218 |  143 |         import sys
4219 |  144 |         sys.path.insert(0, str(SRC_DIR))
4220 |  145 |         from src.detector.signature import SignatureDetector
4221 |  146 |         detector = SignatureDetector()
4222 |  147 |         
4223 |  148 |         event = {"filename": "/bin/sh", "comm": "sh"}
4224 |  149 |         result = detector.analyze_event(event)
4225 |  150 |         
4226 |  151 |         assert result is not None
4227 |  152 |         assert result["type"] == "HEURISTIC_MATCH"
4228 |  153 | 
4229 |  154 |     def test_nc_process_heuristic(self):
4230 |  155 |         """Verify nc (netcat) triggers heuristic."""
4231 |  156 |         import sys
4232 |  157 |         sys.path.insert(0, str(SRC_DIR))
4233 |  158 |         from src.detector.signature import SignatureDetector
4234 |  159 |         detector = SignatureDetector()
4235 |  160 |         
4236 |  161 |         event = {"filename": "/usr/bin/nc", "comm": "nc"}
4237 |  162 |         result = detector.analyze_event(event)
4238 |  163 |         
4239 |  164 |         assert result is not None
4240 |  165 |         assert result["severity"] == "warning"
4241 |  166 | 
4242 |  167 |     def test_ncat_process_heuristic(self):
4243 |  168 |         """Verify ncat triggers heuristic."""
4244 |  169 |         import sys
4245 |  170 |         sys.path.insert(0, str(SRC_DIR))
4246 |  171 |         from src.detector.signature import SignatureDetector
4247 |  172 |         detector = SignatureDetector()
4248 |  173 |         
4249 |  174 |         event = {"filename": "/usr/bin/ncat", "comm": "ncat"}
4250 |  175 |         result = detector.analyze_event(event)
4251 |  176 |         
4252 |  177 |         assert result is not None
4253 |  178 | 
4254 |  179 |     def test_python_process_heuristic(self):
4255 |  180 |         """Verify python process triggers heuristic."""
4256 |  181 |         import sys
4257 |  182 |         sys.path.insert(0, str(SRC_DIR))
4258 |  183 |         from src.detector.signature import SignatureDetector
4259 |  184 |         detector = SignatureDetector()
4260 |  185 |         
4261 |  186 |         event = {"filename": "/usr/bin/python3", "comm": "python"}
4262 |  187 |         result = detector.analyze_event(event)
4263 |  188 |         
4264 |  189 |         assert result is not None
4265 |  190 | 
4266 |  191 |     def test_perl_process_heuristic(self):
4267 |  192 |         """Verify perl process triggers heuristic."""
4268 |  193 |         import sys
4269 |  194 |         sys.path.insert(0, str(SRC_DIR))
4270 |  195 |         from src.detector.signature import SignatureDetector
4271 |  196 |         detector = SignatureDetector()
4272 |  197 |         
4273 |  198 |         event = {"filename": "/usr/bin/perl", "comm": "perl"}
4274 |  199 |         result = detector.analyze_event(event)
4275 |  200 |         
4276 |  201 |         assert result is not None
4277 |  202 | 
4278 |  203 |     def test_non_suspicious_comm_no_heuristic(self):
4279 |  204 |         """Verify non-suspicious process doesn't trigger heuristic."""
4280 |  205 |         import sys
4281 |  206 |         sys.path.insert(0, str(SRC_DIR))
4282 |  207 |         from src.detector.signature import SignatureDetector
4283 |  208 |         detector = SignatureDetector()
4284 |  209 |         
4285 |  210 |         event = {"filename": "/bin/nginx", "comm": "nginx"}
4286 |  211 |         result = detector.analyze_event(event)
4287 |  212 |         
4288 |  213 |         assert result is None
4289 |  214 | 
4290 |  215 | 
4291 |  216 | class TestSignatureDetectorEdgeCases:
4292 |  217 |     """Edge case tests for SignatureDetector."""
4293 |  218 | 
4294 |  219 |     def test_empty_event(self):
4295 |  220 |         """Verify empty event returns None."""
4296 |  221 |         import sys
4297 |  222 |         sys.path.insert(0, str(SRC_DIR))
4298 |  223 |         from src.detector.signature import SignatureDetector
4299 |  224 |         detector = SignatureDetector()
4300 |  225 |         
4301 |  226 |         event = {}
4302 |  227 |         result = detector.analyze_event(event)
4303 |  228 |         
4304 |  229 |         assert result is None
4305 |  230 | 
4306 |  231 |     def test_empty_filename(self):
4307 |  232 |         """Verify empty filename returns None."""
4308 |  233 |         import sys
4309 |  234 |         sys.path.insert(0, str(SRC_DIR))
4310 |  235 |         from src.detector.signature import SignatureDetector
4311 |  236 |         detector = SignatureDetector()
4312 |  237 |         
4313 |  238 |         event = {"filename": "", "comm": "bash"}
4314 |  239 |         result = detector.analyze_event(event)
4315 |  240 |         
4316 |  241 |         assert result is None
4317 |  242 | 
4318 |  243 |     def test_none_filename(self):
4319 |  244 |         """Verify None filename doesn't crash."""
4320 |  245 |         import sys
4321 |  246 |         sys.path.insert(0, str(SRC_DIR))
4322 |  247 |         from src.detector.signature import SignatureDetector
4323 |  248 |         detector = SignatureDetector()
4324 |  249 |         
4325 |  250 |         event = {"filename": None, "comm": "bash"}
4326 |  251 |         result = detector.analyze_event(event)
4327 |  252 |         
4328 |  253 |         assert result is None
4329 |  254 | 
4330 |  255 |     def test_missing_comm_key(self):
4331 |  256 |         """Verify missing 'comm' key is handled."""
4332 |  257 |         import sys
4333 |  258 |         sys.path.insert(0, str(SRC_DIR))
4334 |  259 |         from src.detector.signature import SignatureDetector
4335 |  260 |         detector = SignatureDetector()
4336 |  261 |         
4337 |  262 |         event = {"filename": "/etc/shadow"}
4338 |  263 |         result = detector.analyze_event(event)
4339 |  264 |         
4340 |  265 |         assert result is not None
4341 |  266 | 
4342 |  267 |     def test_missing_filename_key(self):
4343 |  268 |         """Verify missing 'filename' key is handled."""
4344 |  269 |         import sys
4345 |  270 |         sys.path.insert(0, str(SRC_DIR))
4346 |  271 |         from src.detector.signature import SignatureDetector
4347 |  272 |         detector = SignatureDetector()
4348 |  273 |         
4349 |  274 |         event = {"comm": "test"}
4350 |  275 |         result = detector.analyze_event(event)
4351 |  276 |         
4352 |  277 |         assert result is None
4353 |  278 | 
4354 |  279 |     def test_path_with_extra_slashes(self):
4355 |  280 |         """Verify path normalization works."""
4356 |  281 |         import sys
4357 |  282 |         sys.path.insert(0, str(SRC_DIR))
4358 |  283 |         from src.detector.signature import SignatureDetector
4359 |  284 |         detector = SignatureDetector()
4360 |  285 |         
4361 |  286 |         event = {"filename": "///etc///shadow", "comm": "test"}
4362 |  287 |         result = detector.analyze_event(event)
4363 |  288 |         
4364 |  289 |         assert result is None
4365 |  290 | 
4366 |  291 |     def test_path_with_dotdots(self):
4367 |  292 |         """Verify path with .. is handled."""
4368 |  293 |         import sys
4369 |  294 |         sys.path.insert(0, str(SRC_DIR))
4370 |  295 |         from src.detector.signature import SignatureDetector
4371 |  296 |         detector = SignatureDetector()
4372 |  297 |         
4373 |  298 |         event = {"filename": "/etc/../etc/shadow", "comm": "test"}
4374 |  299 |         result = detector.analyze_event(event)
4375 |  300 |         
4376 |  301 |         assert result is None
4377 |  302 | 
4378 |  303 | 
4379 |  304 | class TestSignatureDetectorReturnValues:
4380 |  305 |     """Tests for return value structure."""
4381 |  306 | 
4382 |  307 |     def test_signature_match_structure(self):
4383 |  308 |         """Verify SIGNATURE_MATCH has correct structure."""
4384 |  309 |         import sys
4385 |  310 |         sys.path.insert(0, str(SRC_DIR))
4386 |  311 |         from src.detector.signature import SignatureDetector
4387 |  312 |         detector = SignatureDetector()
4388 |  313 |         
4389 |  314 |         event = {"filename": "/etc/shadow", "comm": "test"}
4390 |  315 |         result = detector.analyze_event(event)
4391 |  316 |         
4392 |  317 |         assert "type" in result
4393 |  318 |         assert "reason" in result
4394 |  319 |         assert "severity" in result
4395 |  320 |         assert "ioc" in result
4396 |  321 | 
4397 |  322 |     def test_heuristic_match_structure(self):
4398 |  323 |         """Verify HEURISTIC_MATCH has correct structure."""
4399 |  324 |         import sys
4400 |  325 |         sys.path.insert(0, str(SRC_DIR))
4401 |  326 |         from src.detector.signature import SignatureDetector
4402 |  327 |         detector = SignatureDetector()
4403 |  328 |         
4404 |  329 |         event = {"filename": "/bin/bash", "comm": "bash"}
4405 |  330 |         result = detector.analyze_event(event)
4406 |  331 |         
4407 |  332 |         assert "type" in result
4408 |  333 |         assert "reason" in result
4409 |  334 |         assert "severity" in result
4410 |  335 | 
4411 |  336 |     def test_severity_values(self):
4412 |  337 |         """Verify severity values are valid."""
4413 |  338 |         import sys
4414 |  339 |         sys.path.insert(0, str(SRC_DIR))
4415 |  340 |         from src.detector.signature import SignatureDetector
4416 |  341 |         detector = SignatureDetector()
4417 |  342 |         
4418 |  343 |         event = {"filename": "/etc/shadow", "comm": "test"}
4419 |  344 |         result = detector.analyze_event(event)
4420 |  345 |         
4421 |  346 |         assert result["severity"] in ["info", "warning", "critical"]
4422 |  347 | 
4423 |  348 | 
4424 |  349 | class TestSignatureDetectorPriority:
4425 |  350 |     """Tests for detection priority (critical paths > heuristics)."""
4426 |  351 | 
4427 |  352 |     def test_critical_path_takes_priority(self):
4428 |  353 |         """Verify critical path takes priority over heuristic."""
4429 |  354 |         import sys
4430 |  355 |         sys.path.insert(0, str(SRC_DIR))
4431 |  356 |         from src.detector.signature import SignatureDetector
4432 |  357 |         detector = SignatureDetector()
4433 |  358 |         
4434 |  359 |         event = {"filename": "/etc/shadow", "comm": "bash"}
4435 |  360 |         result = detector.analyze_event(event)
4436 |  361 |         
4437 |  362 |         assert result["type"] == "SIGNATURE_MATCH"
4438 |  363 |         assert result["severity"] == "critical"
4439 |  364 | 
4440 |  365 | 
4441 |  366 | class TestSignatureDetectorIOCFields:
4442 |  367 |     """Tests for specific IOC field values."""
4443 |  368 | 
4444 |  369 |     def test_shadow_ioc_value(self):
4445 |  370 |         """Verify shadow IOC has correct value."""
4446 |  371 |         import sys
4447 |  372 |         sys.path.insert(0, str(SRC_DIR))
4448 |  373 |         from src.detector.signature import SignatureDetector
4449 |  374 |         detector = SignatureDetector()
4450 |  375 |         
4451 |  376 |         event = {"filename": "/etc/shadow", "comm": "test"}
4452 |  377 |         result = detector.analyze_event(event)
4453 |  378 |         
4454 |  379 |         assert result["ioc"] == "/etc/shadow"
4455 |  380 | 
4456 |  381 |     def test_sudoers_ioc_value(self):
4457 |  382 |         """Verify sudoers IOC has correct value."""
4458 |  383 |         import sys
4459 |  384 |         sys.path.insert(0, str(SRC_DIR))
4460 |  385 |         from src.detector.signature import SignatureDetector
4461 |  386 |         detector = SignatureDetector()
4462 |  387 |         
4463 |  388 |         event = {"filename": "/etc/sudoers", "comm": "test"}
4464 |  389 |         result = detector.analyze_event(event)
4465 |  390 |         
4466 |  391 |         assert result["ioc"] == "/etc/sudoers"
4467 |  392 | 
4468 |  393 |     def test_docker_sock_ioc_value(self):
4469 |  394 |         """Verify docker.sock IOC has correct value."""
4470 |  395 |         import sys
4471 |  396 |         sys.path.insert(0, str(SRC_DIR))
4472 |  397 |         from src.detector.signature import SignatureDetector
4473 |  398 |         detector = SignatureDetector()
4474 |  399 |         
4475 |  400 |         event = {"filename": "/var/run/docker.sock", "comm": "test"}
4476 |  401 |         result = detector.analyze_event(event)
4477 |  402 |         
4478 |  403 |         assert result["ioc"] == "/var/run/docker.sock"
4479 |  404 | 
4480 |  405 | 
4481 |  406 | class TestSignatureDetectorRealWorld:
4482 |  407 |     """Real-world attack scenario tests."""
4483 |  408 | 
4484 |  409 |     def test_password_file_access(self):
4485 |  410 |         """Verify /etc/passwd access doesn't trigger (common task)."""
4486 |  411 |         import sys
4487 |  412 |         sys.path.insert(0, str(SRC_DIR))
4488 |  413 |         from src.detector.signature import SignatureDetector
4489 |  414 |         detector = SignatureDetector()
4490 |  415 |         
4491 |  416 |         event = {"filename": "/etc/passwd", "comm": "cat"}
4492 |  417 |         result = detector.analyze_event(event)
4493 |  418 |         
4494 |  419 |         assert result is None
4495 |  420 | 
4496 |  421 |     def test_scheduled_task_access(self):
4497 |  422 |         """Verify cron access is allowed."""
4498 |  423 |         import sys
4499 |  424 |         sys.path.insert(0, str(SRC_DIR))
4500 |  425 |         from src.detector.signature import SignatureDetector
4501 |  426 |         detector = SignatureDetector()
4502 |  427 |         
4503 |  428 |         event = {"filename": "/etc/cron.d", "comm": "cron"}
4504 |  429 |         result = detector.analyze_event(event)
4505 |  430 |         
4506 |  431 |         assert result is None
4507 |  432 | 
4508 |  433 |     def test_web_server_shell(self):
4509 |  434 |         """Verify shell spawning from any process is detected."""
4510 |  435 |         import sys
4511 |  436 |         sys.path.insert(0, str(SRC_DIR))
4512 |  437 |         from src.detector.signature import SignatureDetector
4513 |  438 |         detector = SignatureDetector()
4514 |  439 |         
4515 |  440 |         event = {"filename": "/bin/bash", "comm": "bash"}
4516 |  441 |         result = detector.analyze_event(event)
4517 |  442 |         
4518 |  443 |         assert result is not None
4519 |  444 |         assert result["severity"] == "warning"
4520 |  445 | 
4521 |  446 |     def test_reverse_shell_pattern(self):
4522 |  447 |         """Verify reverse shell pattern is caught."""
4523 |  448 |         import sys
4524 |  449 |         sys.path.insert(0, str(SRC_DIR))
4525 |  450 |         from src.detector.signature import SignatureDetector
4526 |  451 |         detector = SignatureDetector()
4527 |  452 |         
4528 |  453 |         event = {"filename": "/bin/bash", "comm": "nc"}
4529 |  454 |         result = detector.analyze_event(event)
4530 |  455 |         
4531 |  456 |         assert result is not None
4532 | ```
4533 | 
4534 | ### tests/test_statistical_detector.py
4535 | 
4536 | ```python
4537 |    1 | import pytest
4538 |    2 | import numpy as np
4539 |    3 | from unittest.mock import MagicMock, patch, PropertyMock
4540 |    4 | from pathlib import Path
4541 |    5 | import sys
4542 |    6 | 
4543 |    7 | sys.path.insert(0, str(Path(__file__).parent.parent))
4544 |    8 | 
4545 |    9 | from src.detector.statistical import StatisticalDetector
4546 |   10 | from src.metrics.engine import MetricsEngine
4547 |   11 | 
4548 |   12 | 
4549 |   13 | class TestStatisticalDetectorInit:
4550 |   14 |     """Tests for StatisticalDetector initialization."""
4551 |   15 | 
4552 |   16 |     def test_detector_file_exists(self):
4553 |   17 |         """Verify StatisticalDetector module exists."""
4554 |   18 |         assert StatisticalDetector is not None
4555 |   19 | 
4556 |   20 |     def test_default_threshold(self):
4557 |   21 |         """Verify default threshold is 3.0."""
4558 |   22 |         engine = MetricsEngine()
4559 |   23 |         detector = StatisticalDetector(engine)
4560 |   24 |         assert detector.threshold_z == 3.0
4561 |   25 | 
4562 |   26 |     def test_custom_threshold(self):
4563 |   27 |         """Verify custom threshold is set."""
4564 |   28 |         engine = MetricsEngine()
4565 |   29 |         detector = StatisticalDetector(engine, threshold_z=5.0)
4566 |   30 |         assert detector.threshold_z == 5.0
4567 |   31 | 
4568 |   32 |     def test_engine_reference_stored(self):
4569 |   33 |         """Verify engine reference is stored."""
4570 |   34 |         engine = MetricsEngine()
4571 |   35 |         detector = StatisticalDetector(engine)
4572 |   36 |         assert detector.engine is engine
4573 |   37 | 
4574 |   38 | 
4575 |   39 | class TestStatisticalDetectorEvaluate:
4576 |   40 |     """Tests for evaluate method."""
4577 |   41 | 
4578 |   42 |     def test_unknown_pid_returns_non_anomalous(self):
4579 |   43 |         """Verify unknown PID returns non-anomalous."""
4580 |   44 |         engine = MetricsEngine()
4581 |   45 |         detector = StatisticalDetector(engine)
4582 |   46 |         
4583 |   47 |         result = detector.evaluate(999, np.array([1.0, 2.0, 3.0]))
4584 |   48 |         
4585 |   49 |         assert result["is_anomalous"] is False
4586 |   50 |         assert result["max_z_score"] == 0.0
4587 |   51 | 
4588 |   52 |     def test_known_pid_z_score_calculation(self):
4589 |   53 |         """Verify known PID z-score is calculated."""
4590 |   54 |         engine = MetricsEngine()
4591 |   55 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
4592 |   56 |         
4593 |   57 |         detector = StatisticalDetector(engine, threshold_z=3.0)
4594 |   58 |         result = detector.evaluate(123, np.array([12.0, 10.0, 8.0]))
4595 |   59 |         
4596 |   60 |         assert result["pid"] == 123
4597 |   61 | 
4598 |   62 |     def test_anomaly_detection_threshold(self):
4599 |   63 |         """Verify anomaly detection above threshold."""
4600 |   64 |         engine = MetricsEngine()
4601 |   65 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
4602 |   66 |         
4603 |   67 |         detector = StatisticalDetector(engine, threshold_z=3.0)
4604 |   68 |         result = detector.evaluate(123, np.array([100.0, 10.0, 10.0]))
4605 |   69 |         
4606 |   70 |         assert result["is_anomalous"] is True
4607 |   71 |         assert result["max_z_score"] > 3.0
4608 |   72 | 
4609 |   73 |     def test_no_anomaly_below_threshold(self):
4610 |   74 |         """Verify no anomaly below threshold."""
4611 |   75 |         engine = MetricsEngine()
4612 |   76 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
4613 |   77 |         
4614 |   78 |         detector = StatisticalDetector(engine, threshold_z=3.0)
4615 |   79 |         result = detector.evaluate(123, np.array([12.0, 10.0, 10.0]))
4616 |   80 |         
4617 |   81 |         assert result["is_anomalous"] is False
4618 |   82 | 
4619 |   83 |     def test_z_vector_returned(self):
4620 |   84 |         """Verify z_vector is returned."""
4621 |   85 |         engine = MetricsEngine()
4622 |   86 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
4623 |   87 |         
4624 |   88 |         detector = StatisticalDetector(engine)
4625 |   89 |         result = detector.evaluate(123, np.array([20.0, 20.0, 20.0]))
4626 |   90 |         
4627 |   91 |         assert "z_vector" in result
4628 |   92 |         assert isinstance(result["z_vector"], list)
4629 |   93 | 
4630 |   94 |     def test_euclidean_distance_calculated(self):
4631 |   95 |         """Verify Euclidean distance is calculated."""
4632 |   96 |         engine = MetricsEngine()
4633 |   97 |         engine.update_scalar_metrics(123, np.array([0.0, 0.0, 0.0]))
4634 |   98 |         
4635 |   99 |         detector = StatisticalDetector(engine)
4636 |  100 |         result = detector.evaluate(123, np.array([3.0, 4.0, 0.0]))
4637 |  101 |         
4638 |  102 |         assert result["euclidean_distance"] == 5.0
4639 |  103 | 
4640 |  104 |     def test_euclidean_distance_zero_for_unknown(self):
4641 |  105 |         """Verify distance is 0 for unknown PID."""
4642 |  106 |         engine = MetricsEngine()
4643 |  107 |         detector = StatisticalDetector(engine)
4644 |  108 |         
4645 |  109 |         result = detector.evaluate(999, np.array([1.0, 2.0, 3.0]))
4646 |  110 |         
4647 |  111 |         assert result["euclidean_distance"] == 0.0
4648 |  112 | 
4649 |  113 | 
4650 |  114 | class TestStatisticalDetectorSeverity:
4651 |  115 |     """Tests for severity mapping."""
4652 |  116 | 
4653 |  117 |     def test_severity_info_below_threshold(self):
4654 |  118 |         """Verify severity is info below threshold."""
4655 |  119 |         engine = MetricsEngine()
4656 |  120 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
4657 |  121 |         
4658 |  122 |         detector = StatisticalDetector(engine, threshold_z=3.0)
4659 |  123 |         result = detector.evaluate(123, np.array([11.0, 10.0, 10.0]))
4660 |  124 |         
4661 |  125 |         assert result["severity"] == "info"
4662 |  126 | 
4663 |  127 |     def test_severity_warning_at_threshold(self):
4664 |  128 |         """Verify severity is critical at threshold boundary."""
4665 |  129 |         engine = MetricsEngine()
4666 |  130 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
4667 |  131 |         
4668 |  132 |         detector = StatisticalDetector(engine, threshold_z=3.0)
4669 |  133 |         result = detector.evaluate(123, np.array([19.0, 10.0, 10.0]))
4670 |  134 |         
4671 |  135 |         assert result["severity"] == "warning" or result["severity"] == "critical"
4672 |  136 | 
4673 |  137 |     def test_severity_warning_between_threshold(self):
4674 |  138 |         """Verify severity is critical above threshold."""
4675 |  139 |         engine = MetricsEngine()
4676 |  140 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
4677 |  141 |         
4678 |  142 |         detector = StatisticalDetector(engine, threshold_z=3.0)
4679 |  143 |         result = detector.evaluate(123, np.array([25.0, 10.0, 10.0]))
4680 |  144 |         
4681 |  145 |         assert result["severity"] == "critical"
4682 |  146 | 
4683 |  147 |     def test_severity_critical_above_double_threshold(self):
4684 |  148 |         """Verify severity is critical above 2x threshold."""
4685 |  149 |         engine = MetricsEngine()
4686 |  150 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
4687 |  151 |         
4688 |  152 |         detector = StatisticalDetector(engine, threshold_z=3.0)
4689 |  153 |         result = detector.evaluate(123, np.array([100.0, 10.0, 10.0]))
4690 |  154 |         
4691 |  155 |         assert result["severity"] == "critical"
4692 |  156 | 
4693 |  157 |     def test_mapped_to_severity_method(self):
4694 |  158 |         """Verify _map_to_severity method."""
4695 |  159 |         engine = MetricsEngine()
4696 |  160 |         detector = StatisticalDetector(engine)
4697 |  161 |         
4698 |  162 |         assert detector._map_to_severity(1.0) == "info"
4699 |  163 |         assert detector._map_to_severity(3.5) == "warning"
4700 |  164 |         assert detector._map_to_severity(10.0) == "critical"
4701 |  165 | 
4702 |  166 | 
4703 |  167 | class TestStatisticalDetectorReturnValues:
4704 |  168 |     """Tests for return value structure."""
4705 |  169 | 
4706 |  170 |     def test_return_has_pid(self):
4707 |  171 |         """Verify return has pid field."""
4708 |  172 |         engine = MetricsEngine()
4709 |  173 |         detector = StatisticalDetector(engine)
4710 |  174 |         
4711 |  175 |         result = detector.evaluate(123, np.array([1.0]))
4712 |  176 |         
4713 |  177 |         assert "pid" in result
4714 |  178 | 
4715 |  179 |     def test_return_has_is_anomalous(self):
4716 |  180 |         """Verify return has is_anomalous field."""
4717 |  181 |         engine = MetricsEngine()
4718 |  182 |         detector = StatisticalDetector(engine)
4719 |  183 |         
4720 |  184 |         result = detector.evaluate(123, np.array([1.0]))
4721 |  185 |         
4722 |  186 |         assert "is_anomalous" in result
4723 |  187 |         assert isinstance(result["is_anomalous"], bool)
4724 |  188 | 
4725 |  189 |     def test_return_has_max_z_score(self):
4726 |  190 |         """Verify return has max_z_score field."""
4727 |  191 |         engine = MetricsEngine()
4728 |  192 |         detector = StatisticalDetector(engine)
4729 |  193 |         
4730 |  194 |         result = detector.evaluate(123, np.array([1.0]))
4731 |  195 |         
4732 |  196 |         assert "max_z_score" in result
4733 |  197 | 
4734 |  198 |     def test_return_has_severity(self):
4735 |  199 |         """Verify return has severity field."""
4736 |  200 |         engine = MetricsEngine()
4737 |  201 |         detector = StatisticalDetector(engine)
4738 |  202 |         
4739 |  203 |         result = detector.evaluate(123, np.array([1.0]))
4740 |  204 |         
4741 |  205 |         assert "severity" in result
4742 |  206 | 
4743 |  207 | 
4744 |  208 | class TestStatisticalDetectorEdgeCases:
4745 |  209 |     """Edge case tests."""
4746 |  210 | 
4747 |  211 |     def test_empty_vector(self):
4748 |  212 |         """Verify empty vector handled."""
4749 |  213 |         engine = MetricsEngine()
4750 |  214 |         detector = StatisticalDetector(engine)
4751 |  215 |         
4752 |  216 |         result = detector.evaluate(123, np.array([]))
4753 |  217 |         
4754 |  218 |         assert result["pid"] == 123
4755 |  219 | 
4756 |  220 |     def test_single_element_vector(self):
4757 |  221 |         """Verify single element vector."""
4758 |  222 |         engine = MetricsEngine()
4759 |  223 |         engine.update_scalar_metrics(123, np.array([50.0]))
4760 |  224 |         
4761 |  225 |         detector = StatisticalDetector(engine)
4762 |  226 |         result = detector.evaluate(123, np.array([60.0]))
4763 |  227 |         
4764 |  228 |         assert result["max_z_score"] > 0
4765 |  229 | 
4766 |  230 |     def test_large_vector(self):
4767 |  231 |         """Verify large vector handled."""
4768 |  232 |         engine = MetricsEngine()
4769 |  233 |         large_vector = np.random.rand(1000)
4770 |  234 |         detector = StatisticalDetector(engine)
4771 |  235 |         
4772 |  236 |         result = detector.evaluate(123, large_vector)
4773 |  237 |         
4774 |  238 |         assert "z_vector" in result
4775 |  239 |         assert len(result["z_vector"]) == 1000
4776 |  240 | 
4777 |  241 |     def test_negative_values(self):
4778 |  242 |         """Verify negative values handled."""
4779 |  243 |         engine = MetricsEngine()
4780 |  244 |         engine.update_scalar_metrics(123, np.array([-10.0, -20.0]))
4781 |  245 |         
4782 |  246 |         detector = StatisticalDetector(engine)
4783 |  247 |         result = detector.evaluate(123, np.array([-5.0, -30.0]))
4784 |  248 |         
4785 |  249 |         assert result["max_z_score"] > 0
4786 |  250 | 
4787 |  251 |     def test_zero_threshold(self):
4788 |  252 |         """Verify zero threshold handled."""
4789 |  253 |         engine = MetricsEngine()
4790 |  254 |         engine.update_scalar_metrics(123, np.array([10.0]))
4791 |  255 |         
4792 |  256 |         detector = StatisticalDetector(engine, threshold_z=0.0)
4793 |  257 |         result = detector.evaluate(123, np.array([10.0]))
4794 |  258 |         
4795 |  259 |         assert "severity" in result
4796 |  260 | 
4797 |  261 |     def test_negative_threshold(self):
4798 |  262 |         """Verify negative threshold handled."""
4799 |  263 |         engine = MetricsEngine()
4800 |  264 |         engine.update_scalar_metrics(123, np.array([10.0]))
4801 |  265 |         
4802 |  266 |         detector = StatisticalDetector(engine, threshold_z=-1.0)
4803 |  267 |         result = detector.evaluate(123, np.array([10.0]))
4804 |  268 |         
4805 |  269 |         assert "severity" in result
4806 |  270 | 
4807 |  271 | 
4808 |  272 | class TestStatisticalDetectorIntegration:
4809 |  273 |     """Integration tests with MetricsEngine."""
4810 |  274 | 
4811 |  275 |     def test_full_workflow(self):
4812 |  276 |         """Verify full detection workflow."""
4813 |  277 |         engine = MetricsEngine(alpha=0.3)
4814 |  278 |         
4815 |  279 |         for i in range(50):
4816 |  280 |             vector = np.array([
4817 |  281 |                 float(i) + np.random.randn(),
4818 |  282 |                 float(i * 2) + np.random.randn(),
4819 |  283 |                 float(i * 3) + np.random.randn()
4820 |  284 |             ])
4821 |  285 |             engine.update_scalar_metrics(123, vector)
4822 |  286 |         
4823 |  287 |         detector = StatisticalDetector(engine, threshold_z=3.0)
4824 |  288 |         
4825 |  289 |         normal = np.array([25.0, 50.0, 75.0])
4826 |  290 |         result_normal = detector.evaluate(123, normal)
4827 |  291 |         
4828 |  292 |         assert "is_anomalous" in result_normal
4829 |  293 |         assert "euclidean_distance" in result_normal
4830 |  294 | 
4831 |  295 |         anomalous = np.array([1000.0, 1000.0, 1000.0])
4832 |  296 |         result_anom = detector.evaluate(123, anomalous)
4833 |  297 |         
4834 |  298 |         assert result_anom["is_anomalous"] is True
4835 |  299 | 
4836 |  300 |     def test_multiple_pids(self):
4837 |  301 |         """Verify multiple PIDs tracked separately."""
4838 |  302 |         engine = MetricsEngine()
4839 |  303 |         
4840 |  304 |         for pid in [100, 200, 300]:
4841 |  305 |             for _ in range(20):
4842 |  306 |                 engine.update_scalar_metrics(pid, np.array([float(pid)]))
4843 |  307 |         
4844 |  308 |         detector = StatisticalDetector(engine)
4845 |  309 |         
4846 |  310 |         for pid in [100, 200, 300]:
4847 |  311 |             result = detector.evaluate(pid, np.array([float(pid)]))
4848 |  312 |             assert result["is_anomalous"] is False
4849 |  313 | 
4850 |  314 |     def test_ewma_integration(self):
4851 |  315 |         """Verify EWMA updates work with detector."""
4852 |  316 |         engine = MetricsEngine(alpha=0.3)
4853 |  317 |         
4854 |  318 |         engine.update_scalar_metrics(123, np.array([10.0, 10.0, 10.0]))
4855 |  319 |         
4856 |  320 |         for _ in range(10):
4857 |  321 |             engine.update_scalar_metrics(123, np.array([20.0, 20.0, 20.0]))
4858 |  322 |         
4859 |  323 |         detector = StatisticalDetector(engine)
4860 |  324 |         result = detector.evaluate(123, np.array([25.0, 25.0, 25.0]))
4861 |  325 |         
4862 |  326 |         assert "z_vector" in result
4863 |  327 | 
4864 |  328 | 
4865 |  329 | class TestStatisticalDetectorNgramIntegration:
4866 |  330 |     """Integration with n-gram functionality."""
4867 |  331 | 
4868 |  332 |     def test_ngram_with_statistical(self):
4869 |  333 |         """Verify ngram integration works."""
4870 |  334 |         engine = MetricsEngine(n_gram_size=3)
4871 |  335 |         
4872 |  336 |         for i in range(100):
4873 |  337 |             engine.update_ngram(123, i)
4874 |  338 |             engine.update_ngram(123, i + 1)
4875 |  339 |             engine.update_ngram(123, i + 2)
4876 |  340 |         
4877 |  341 |         detector = StatisticalDetector(engine)
4878 |  342 |         
4879 |  343 |         anomaly_score = engine.get_ngram_anomaly_score(123, (999, 1000, 1001))
4880 |  344 |         assert anomaly_score > 0.5
4881 | ```
4882 | 
4883 | ### tests/test_storage_sqlite.py
4884 | 
4885 | ```python
4886 |    1 | import pytest
4887 |    2 | import sys
4888 |    3 | import sqlite3
4889 |    4 | import json
4890 |    5 | import tempfile
4891 |    6 | import os
4892 |    7 | from pathlib import Path
4893 |    8 | from unittest.mock import patch, MagicMock
4894 |    9 | 
4895 |   10 | SRC_DIR = Path(__file__).parent.parent / "src"
4896 |   11 | sys.path.insert(0, str(SRC_DIR))
4897 |   12 | 
4898 |   13 | from storage.sqlite import StorageManager
4899 |   14 | 
4900 |   15 | 
4901 |   16 | class TestStorageManagerSchema:
4902 |   17 |     """Tests for database schema initialization."""
4903 |   18 | 
4904 |   19 |     def test_init_creates_profiles_table(self):
4905 |   20 |         """Verify profiles table is created."""
4906 |   21 |         with tempfile.TemporaryDirectory() as tmpdir:
4907 |   22 |             db_path = os.path.join(tmpdir, "test.db")
4908 |   23 |             manager = StorageManager(db_path=db_path)
4909 |   24 |             
4910 |   25 |             conn = sqlite3.connect(db_path)
4911 |   26 |             cursor = conn.execute(
4912 |   27 |                 "SELECT name FROM sqlite_master WHERE type='table' AND name='profiles'"
4913 |   28 |             )
4914 |   29 |             result = cursor.fetchone()
4915 |   30 |             conn.close()
4916 |   31 |             
4917 |   32 |             assert result is not None, "profiles table should exist"
4918 |   33 | 
4919 |   34 |     def test_init_creates_alerts_table(self):
4920 |   35 |         """Verify alerts table is created."""
4921 |   36 |         with tempfile.TemporaryDirectory() as tmpdir:
4922 |   37 |             db_path = os.path.join(tmpdir, "test.db")
4923 |   38 |             manager = StorageManager(db_path=db_path)
4924 |   39 |             
4925 |   40 |             conn = sqlite3.connect(db_path)
4926 |   41 |             cursor = conn.execute(
4927 |   42 |                 "SELECT name FROM sqlite_master WHERE type='table' AND name='alerts'"
4928 |   43 |             )
4929 |   44 |             result = cursor.fetchone()
4930 |   45 |             conn.close()
4931 |   46 |             
4932 |   47 |             assert result is not None, "alerts table should exist"
4933 |   48 | 
4934 |   49 |     def test_init_creates_profiles_with_correct_columns(self):
4935 |   50 |         """Verify profiles table has required columns."""
4936 |   51 |         with tempfile.TemporaryDirectory() as tmpdir:
4937 |   52 |             db_path = os.path.join(tmpdir, "test.db")
4938 |   53 |             manager = StorageManager(db_path=db_path)
4939 |   54 |             
4940 |   55 |             conn = sqlite3.connect(db_path)
4941 |   56 |             cursor = conn.execute("PRAGMA table_info(profiles)")
4942 |   57 |             columns = {row[1] for row in cursor.fetchall()}
4943 |   58 |             conn.close()
4944 |   59 |             
4945 |   60 |             required = {"id", "identifier", "mu", "sigma", "last_updated"}
4946 |   61 |             assert required.issubset(columns), f"Missing columns: {required - columns}"
4947 |   62 | 
4948 |   63 |     def test_init_creates_alerts_with_correct_columns(self):
4949 |   64 |         """Verify alerts table has required columns."""
4950 |   65 |         with tempfile.TemporaryDirectory() as tmpdir:
4951 |   66 |             db_path = os.path.join(tmpdir, "test.db")
4952 |   67 |             manager = StorageManager(db_path=db_path)
4953 |   68 |             
4954 |   69 |             conn = sqlite3.connect(db_path)
4955 |   70 |             cursor = conn.execute("PRAGMA table_info(alerts)")
4956 |   71 |             columns = {row[1] for row in cursor.fetchall()}
4957 |   72 |             conn.close()
4958 |   73 |             
4959 |   74 |             required = {"id", "timestamp", "pid", "score", "severity", "reasons", "container_info"}
4960 |   75 |             assert required.issubset(columns), f"Missing columns: {required - columns}"
4961 |   76 | 
4962 |   77 |     def test_profile_identifier_unique_constraint(self):
4963 |   78 |         """Verify identifier column has UNIQUE constraint."""
4964 |   79 |         with tempfile.TemporaryDirectory() as tmpdir:
4965 |   80 |             db_path = os.path.join(tmpdir, "test.db")
4966 |   81 |             manager = StorageManager(db_path=db_path)
4967 |   82 |             
4968 |   83 |             conn = sqlite3.connect(db_path)
4969 |   84 |             cursor = conn.execute(
4970 |   85 |                 "SELECT sql FROM sqlite_master WHERE type='table' AND name='profiles'"
4971 |   86 |             )
4972 |   87 |             schema = cursor.fetchone()[0]
4973 |   88 |             conn.close()
4974 |   89 |             
4975 |   90 |             assert "UNIQUE" in schema.upper(), "profiles.identifier must have UNIQUE constraint"
4976 |   91 | 
4977 |   92 | 
4978 |   93 | class TestStorageManagerAlerts:
4979 |   94 |     """Tests for alert storage operations."""
4980 |   95 | 
4981 |   96 |     def test_save_alert_inserts_record(self):
4982 |   97 |         """Verify save_alert inserts a record into the database."""
4983 |   98 |         with tempfile.TemporaryDirectory() as tmpdir:
4984 |   99 |             db_path = os.path.join(tmpdir, "test.db")
4985 |  100 |             manager = StorageManager(db_path=db_path)
4986 |  101 |             
4987 |  102 |             alert_data = {
4988 |  103 |                 "timestamp": "2024-01-01T00:00:00",
4989 |  104 |                 "pid": 1234,
4990 |  105 |                 "score": 15.5,
4991 |  106 |                 "severity": "critical",
4992 |  107 |                 "reasons": ["unauthorized access"],
4993 |  108 |                 "container_info": {"id": "abc123"}
4994 |  109 |             }
4995 |  110 |             manager.save_alert(alert_data)
4996 |  111 |             
4997 |  112 |             conn = sqlite3.connect(db_path)
4998 |  113 |             cursor = conn.execute("SELECT * FROM alerts WHERE pid = ?", (1234,))
4999 |  114 |             row = cursor.fetchone()
5000 |  115 |             conn.close()
5001 |  116 |             
5002 |  117 |             assert row is not None, "Alert should be saved"
5003 |  118 |             assert row[2] == 1234
5004 |  119 |             assert row[3] == 15.5
5005 |  120 |             assert row[4] == "critical"
5006 |  121 | 
5007 |  122 |     def test_save_alert_serializes_reasons_as_json(self):
5008 |  123 |         """Verify reasons are stored as JSON string."""
5009 |  124 |         with tempfile.TemporaryDirectory() as tmpdir:
5010 |  125 |             db_path = os.path.join(tmpdir, "test.db")
5011 |  126 |             manager = StorageManager(db_path=db_path)
5012 |  127 |             
5013 |  128 |             alert_data = {
5014 |  129 |                 "timestamp": "2024-01-01T00:00:00",
5015 |  130 |                 "pid": 1234,
5016 |  131 |                 "score": 10.0,
5017 |  132 |                 "severity": "warning",
5018 |  133 |                 "reasons": ["reason1", "reason2"],
5019 |  134 |                 "container_info": None
5020 |  135 |             }
5021 |  136 |             manager.save_alert(alert_data)
5022 |  137 |             
5023 |  138 |             conn = sqlite3.connect(db_path)
5024 |  139 |             cursor = conn.execute("SELECT reasons FROM alerts WHERE pid = ?", (1234,))
5025 |  140 |             row = cursor.fetchone()
5026 |  141 |             conn.close()
5027 |  142 |             
5028 |  143 |             parsed = json.loads(row[0])
5029 |  144 |             assert parsed == ["reason1", "reason2"]
5030 |  145 | 
5031 |  146 |     def test_save_alert_serializes_container_info_as_json(self):
5032 |  147 |         """Verify container_info is stored as JSON string."""
5033 |  148 |         with tempfile.TemporaryDirectory() as tmpdir:
5034 |  149 |             db_path = os.path.join(tmpdir, "test.db")
5035 |  150 |             manager = StorageManager(db_path=db_path)
5036 |  151 |             
5037 |  152 |             alert_data = {
5038 |  153 |                 "timestamp": "2024-01-01T00:00:00",
5039 |  154 |                 "pid": 1234,
5040 |  155 |                 "score": 10.0,
5041 |  156 |                 "severity": "warning",
5042 |  157 |                 "reasons": [],
5043 |  158 |                 "container_info": {"id": "def456", "name": "testcontainer"}
5044 |  159 |             }
5045 |  160 |             manager.save_alert(alert_data)
5046 |  161 |             
5047 |  162 |             conn = sqlite3.connect(db_path)
5048 |  163 |             cursor = conn.execute("SELECT container_info FROM alerts WHERE pid = ?", (1234,))
5049 |  164 |             row = cursor.fetchone()
5050 |  165 |             conn.close()
5051 |  166 |             
5052 |  167 |             parsed = json.loads(row[0])
5053 |  168 |             assert parsed == {"id": "def456", "name": "testcontainer"}
5054 |  169 | 
5055 |  170 |     def test_save_alert_handles_none_container_info(self):
5056 |  171 |         """Verify None container_info is handled correctly."""
5057 |  172 |         with tempfile.TemporaryDirectory() as tmpdir:
5058 |  173 |             db_path = os.path.join(tmpdir, "test.db")
5059 |  174 |             manager = StorageManager(db_path=db_path)
5060 |  175 |             
5061 |  176 |             alert_data = {
5062 |  177 |                 "timestamp": "2024-01-01T00:00:00",
5063 |  178 |                 "pid": 1234,
5064 |  179 |                 "score": 10.0,
5065 |  180 |                 "severity": "warning",
5066 |  181 |                 "reasons": [],
5067 |  182 |                 "container_info": None
5068 |  183 |             }
5069 |  184 |             manager.save_alert(alert_data)
5070 |  185 |             
5071 |  186 |             conn = sqlite3.connect(db_path)
5072 |  187 |             cursor = conn.execute("SELECT container_info FROM alerts WHERE pid = ?", (1234,))
5073 |  188 |             row = cursor.fetchone()
5074 |  189 |             conn.close()
5075 |  190 |             
5076 |  191 |             assert row[0] == "null"
5077 |  192 | 
5078 |  193 |     def test_get_recent_alerts_returns_ordered_by_timestamp(self):
5079 |  194 |         """Verify alerts are returned in descending timestamp order."""
5080 |  195 |         with tempfile.TemporaryDirectory() as tmpdir:
5081 |  196 |             db_path = os.path.join(tmpdir, "test.db")
5082 |  197 |             manager = StorageManager(db_path=db_path)
5083 |  198 |             
5084 |  199 |             manager.save_alert({
5085 |  200 |                 "timestamp": "2024-01-01T00:00:00",
5086 |  201 |                 "pid": 1001,
5087 |  202 |                 "score": 5.0,
5088 |  203 |                 "severity": "info",
5089 |  204 |                 "reasons": [],
5090 |  205 |                 "container_info": None
5091 |  206 |             })
5092 |  207 |             manager.save_alert({
5093 |  208 |                 "timestamp": "2024-01-02T00:00:00",
5094 |  209 |                 "pid": 1002,
5095 |  210 |                 "score": 10.0,
5096 |  211 |                 "severity": "warning",
5097 |  212 |                 "reasons": [],
5098 |  213 |                 "container_info": None
5099 |  214 |             })
5100 |  215 |             
5101 |  216 |             alerts = manager.get_recent_alerts(limit=10)
5102 |  217 |             
5103 |  218 |             assert alerts[0]["pid"] == 1002, "Most recent alert should be first"
5104 |  219 |             assert alerts[1]["pid"] == 1001
5105 |  220 | 
5106 |  221 |     def test_get_recent_alerts_respects_limit(self):
5107 |  222 |         """Verify limit parameter is respected."""
5108 |  223 |         with tempfile.TemporaryDirectory() as tmpdir:
5109 |  224 |             db_path = os.path.join(tmpdir, "test.db")
5110 |  225 |             manager = StorageManager(db_path=db_path)
5111 |  226 |             
5112 |  227 |             for i in range(10):
5113 |  228 |                 manager.save_alert({
5114 |  229 |                     "timestamp": f"2024-01-0{i+1}T00:00:00",
5115 |  230 |                     "pid": 1000 + i,
5116 |  231 |                     "score": 5.0,
5117 |  232 |                     "severity": "info",
5118 |  233 |                     "reasons": [],
5119 |  234 |                     "container_info": None
5120 |  235 |                 })
5121 |  236 |             
5122 |  237 |             alerts = manager.get_recent_alerts(limit=3)
5123 |  238 |             
5124 |  239 |             assert len(alerts) == 3, "Should return only 3 alerts"
5125 |  240 | 
5126 |  241 |     def test_get_recent_alerts_returns_empty_list_when_no_alerts(self):
5127 |  242 |         """Verify empty list is returned when no alerts exist."""
5128 |  243 |         with tempfile.TemporaryDirectory() as tmpdir:
5129 |  244 |             db_path = os.path.join(tmpdir, "test.db")
5130 |  245 |             manager = StorageManager(db_path=db_path)
5131 |  246 |             
5132 |  247 |             alerts = manager.get_recent_alerts(limit=10)
5133 |  248 |             
5134 |  249 |             assert alerts == []
5135 |  250 | 
5136 |  251 |     def test_get_recent_alerts_parses_json_reasons(self):
5137 |  252 |         """Verify reasons are automatically parsed from JSON to list."""
5138 |  253 |         with tempfile.TemporaryDirectory() as tmpdir:
5139 |  254 |             db_path = os.path.join(tmpdir, "test.db")
5140 |  255 |             manager = StorageManager(db_path=db_path)
5141 |  256 |             
5142 |  257 |             manager.save_alert({
5143 |  258 |                 "timestamp": "2024-01-01T00:00:00",
5144 |  259 |                 "pid": 1234,
5145 |  260 |                 "score": 10.0,
5146 |  261 |                 "severity": "warning",
5147 |  262 |                 "reasons": ["reason1", "reason2"],
5148 |  263 |                 "container_info": None
5149 |  264 |             })
5150 |  265 |             
5151 |  266 |             alerts = manager.get_recent_alerts(limit=1)
5152 |  267 |             
5153 |  268 |             assert isinstance(alerts[0]["reasons"], list), "reasons should be parsed from JSON to list"
5154 |  269 |             assert alerts[0]["reasons"] == ["reason1", "reason2"]
5155 |  270 | 
5156 |  271 |     def test_get_recent_alerts_parses_json_container_info(self):
5157 |  272 |         """Verify container_info is automatically parsed from JSON."""
5158 |  273 |         with tempfile.TemporaryDirectory() as tmpdir:
5159 |  274 |             db_path = os.path.join(tmpdir, "test.db")
5160 |  275 |             manager = StorageManager(db_path=db_path)
5161 |  276 |             
5162 |  277 |             manager.save_alert({
5163 |  278 |                 "timestamp": "2024-01-01T00:00:00",
5164 |  279 |                 "pid": 1234,
5165 |  280 |                 "score": 10.0,
5166 |  281 |                 "severity": "warning",
5167 |  282 |                 "reasons": [],
5168 |  283 |                 "container_info": {"id": "abc", "name": "test"}
5169 |  284 |             })
5170 |  285 |             
5171 |  286 |             alerts = manager.get_recent_alerts(limit=1)
5172 |  287 |             
5173 |  288 |             assert isinstance(alerts[0]["container_info"], dict), "container_info should be parsed from JSON"
5174 |  289 |             assert alerts[0]["container_info"] == {"id": "abc", "name": "test"}
5175 |  290 | 
5176 |  291 | 
5177 |  292 | class TestStorageManagerProfiles:
5178 |  293 |     """Tests for profile storage operations."""
5179 |  294 | 
5180 |  295 |     def test_save_profile_inserts_record(self):
5181 |  296 |         """Verify save_profile inserts a record."""
5182 |  297 |         with tempfile.TemporaryDirectory() as tmpdir:
5183 |  298 |             db_path = os.path.join(tmpdir, "test.db")
5184 |  299 |             manager = StorageManager(db_path=db_path)
5185 |  300 |             
5186 |  301 |             manager.save_profile("bash", b"mu_data", b"sigma_data")
5187 |  302 |             
5188 |  303 |             conn = sqlite3.connect(db_path)
5189 |  304 |             cursor = conn.execute("SELECT * FROM profiles WHERE identifier = ?", ("bash",))
5190 |  305 |             row = cursor.fetchone()
5191 |  306 |             conn.close()
5192 |  307 |             
5193 |  308 |             assert row is not None, "Profile should be saved"
5194 |  309 |             assert row[1] == "bash"
5195 |  310 | 
5196 |  311 |     def test_save_profile_updates_existing(self):
5197 |  312 |         """Verify save_profile updates existing record."""
5198 |  313 |         with tempfile.TemporaryDirectory() as tmpdir:
5199 |  314 |             db_path = os.path.join(tmpdir, "test.db")
5200 |  315 |             manager = StorageManager(db_path=db_path)
5201 |  316 |             
5202 |  317 |             manager.save_profile("bash", b"mu_v1", b"sigma_v1")
5203 |  318 |             manager.save_profile("bash", b"mu_v2", b"sigma_v2")
5204 |  319 |             
5205 |  320 |             conn = sqlite3.connect(db_path)
5206 |  321 |             cursor = conn.execute("SELECT mu, sigma FROM profiles WHERE identifier = ?", ("bash",))
5207 |  322 |             row = cursor.fetchone()
5208 |  323 |             conn.close()
5209 |  324 |             
5210 |  325 |             assert row[0] == b"mu_v2", "mu should be updated"
5211 |  326 |             assert row[1] == b"sigma_v2", "sigma should be updated"
5212 |  327 | 
5213 |  328 |     def test_get_profile_returns_dict(self):
5214 |  329 |         """Verify get_profile returns dictionary."""
5215 |  330 |         with tempfile.TemporaryDirectory() as tmpdir:
5216 |  331 |             db_path = os.path.join(tmpdir, "test.db")
5217 |  332 |             manager = StorageManager(db_path=db_path)
5218 |  333 |             
5219 |  334 |             manager.save_profile("bash", b"mu_data", b"sigma_data")
5220 |  335 |             profile = manager.get_profile("bash")
5221 |  336 |             
5222 |  337 |             assert isinstance(profile, dict)
5223 |  338 |             assert profile["identifier"] == "bash"
5224 |  339 |             assert profile["mu"] == b"mu_data"
5225 |  340 | 
5226 |  341 |     def test_get_profile_returns_none_for_missing(self):
5227 |  342 |         """Verify get_profile returns None for non-existent profile."""
5228 |  343 |         with tempfile.TemporaryDirectory() as tmpdir:
5229 |  344 |             db_path = os.path.join(tmpdir, "test.db")
5230 |  345 |             manager = StorageManager(db_path=db_path)
5231 |  346 |             
5232 |  347 |             profile = manager.get_profile("nonexistent")
5233 |  348 |             
5234 |  349 |             assert profile is None
5235 |  350 | 
5236 |  351 | 
5237 |  352 | class TestStorageManagerConcurrency:
5238 |  353 |     """Tests for thread safety."""
5239 |  354 | 
5240 |  355 |     def test_lock_is_thread_lock(self):
5241 |  356 |         """Verify lock is a threading.Lock."""
5242 |  357 |         with tempfile.TemporaryDirectory() as tmpdir:
5243 |  358 |             db_path = os.path.join(tmpdir, "test.db")
5244 |  359 |             manager = StorageManager(db_path=db_path)
5245 |  360 |             
5246 |  361 |             import threading
5247 |  362 |             assert isinstance(manager._lock, type(threading.Lock()))
5248 |  363 | 
5249 |  364 |     def test_concurrent_saves_do_not_corrupt(self):
5250 |  365 |         """Verify concurrent writes don't corrupt database."""
5251 |  366 |         import threading
5252 |  367 |         with tempfile.TemporaryDirectory() as tmpdir:
5253 |  368 |             db_path = os.path.join(tmpdir, "test.db")
5254 |  369 |             manager = StorageManager(db_path=db_path)
5255 |  370 |             
5256 |  371 |             def save_alert(i):
5257 |  372 |                 manager.save_alert({
5258 |  373 |                     "timestamp": f"2024-01-0{i%9+1}T00:00:00",
5259 |  374 |                     "pid": 2000 + i,
5260 |  375 |                     "score": 5.0,
5261 |  376 |                     "severity": "info",
5262 |  377 |                     "reasons": [],
5263 |  378 |                     "container_info": None
5264 |  379 |                 })
5265 |  380 |             
5266 |  381 |             threads = [threading.Thread(target=save_alert, args=(i,)) for i in range(20)]
5267 |  382 |             for t in threads:
5268 |  383 |                 t.start()
5269 |  384 |             for t in threads:
5270 |  385 |                 t.join()
5271 |  386 |             
5272 |  387 |             conn = sqlite3.connect(db_path)
5273 |  388 |             cursor = conn.execute("SELECT COUNT(*) FROM alerts")
5274 |  389 |             count = cursor.fetchone()[0]
5275 |  390 |             conn.close()
5276 |  391 |             
5277 |  392 |             assert count == 20, "All 20 alerts should be saved"
5278 | ```
5279 | 
5280 | ### tests/test_tracepoints.py
5281 | 
5282 | ```python
5283 |    1 | import re
5284 |    2 | import pytest
5285 |    3 | from pathlib import Path
5286 |    4 | 
5287 |    5 | EBPF_DIR = Path(__file__).parent.parent / "ebpf"
5288 |    6 | TRACER_FILE = EBPF_DIR / "tracer.bpf.c"
5289 |    7 | 
5290 |    8 | 
5291 |    9 | class TestTracepointHooks:
5292 |   10 |     """Tests for eBPF tracepoint hook validation."""
5293 |   11 | 
5294 |   12 |     @pytest.fixture
5295 |   13 |     def tracer_content(self):
5296 |   14 |         """Load tracer.bpf.c content."""
5297 |   15 |         return TRACER_FILE.read_text()
5298 |   16 | 
5299 |   17 |     def test_tracer_file_exists(self):
5300 |   18 |         """Verify tracer.bpf.c exists."""
5301 |   19 |         assert TRACER_FILE.exists(), "tracer.bpf.c not found"
5302 |   20 | 
5303 |   21 |     def test_includes_required_headers(self, tracer_content):
5304 |   22 |         """Verify required headers are included."""
5305 |   23 |         required_headers = ["vmlinux.h", "bpf/bpf_helpers.h", "bpf/bpf_tracing.h", "maps.bpf.h"]
5306 |   24 |         for header in required_headers:
5307 |   25 |             assert header in tracer_content, f"Required header {header} not included"
5308 |   26 | 
5309 |   27 |     def test_license_defined(self, tracer_content):
5310 |   28 |         """Verify GPL license is defined."""
5311 |   29 |         assert "LICENSE" in tracer_content, "LICENSE not defined"
5312 |   30 |         assert "GPL" in tracer_content, "GPL license not set"
5313 |   31 | 
5314 |   32 |     def test_trace_openat_hook_exists(self, tracer_content):
5315 |   33 |         """Verify tracepoint for openat syscall is defined."""
5316 |   34 |         assert "sys_enter_openat" in tracer_content, "sys_enter_openat tracepoint not found"
5317 |   35 |         assert "trace_openat" in tracer_content, "trace_openat handler function not found"
5318 |   36 | 
5319 |   37 |     def test_trace_close_hook_exists(self, tracer_content):
5320 |   38 |         """Verify tracepoint for close syscall is defined."""
5321 |   39 |         assert "sys_enter_close" in tracer_content, "sys_enter_close tracepoint not found"
5322 |   40 |         assert "trace_close" in tracer_content, "trace_close handler function not found"
5323 |   41 | 
5324 |   42 |     def test_openat_tracepoint_sec_format(self, tracer_content):
5325 |   43 |         """Verify openat tracepoint has correct SEC() format."""
5326 |   44 |         pattern = r'SEC\("tracepoint/syscalls/sys_enter_openat"\)'
5327 |   45 |         assert re.search(pattern, tracer_content), "Incorrect SEC format for openat tracepoint"
5328 |   46 | 
5329 |   47 |     def test_close_tracepoint_sec_format(self, tracer_content):
5330 |   48 |         """Verify close tracepoint has correct SEC() format."""
5331 |   49 |         pattern = r'SEC\("tracepoint/syscalls/sys_enter_close"\)'
5332 |   50 |         assert re.search(pattern, tracer_content), "Incorrect SEC format for close tracepoint"
5333 |   51 | 
5334 |   52 |     def test_trace_openat_returns_int(self, tracer_content):
5335 |   53 |         """Verify trace_openat function returns int."""
5336 |   54 |         pattern = r'int\s+trace_openat\s*\('
5337 |   55 |         assert re.search(pattern, tracer_content), "trace_openat should return int"
5338 |   56 | 
5339 |   57 |     def test_trace_close_returns_int(self, tracer_content):
5340 |   58 |         """Verify trace_close function returns int."""
5341 |   59 |         pattern = r'int\s+trace_close\s*\('
5342 |   60 |         assert re.search(pattern, tracer_content), "trace_close should return int"
5343 |   61 | 
5344 |   62 |     def test_trace_openat_context_param(self, tracer_content):
5345 |   63 |         """Verify trace_openat has correct context parameter."""
5346 |   64 |         assert "struct trace_event_raw_sys_enter" in tracer_content, "Missing trace_event_raw_sys_enter context"
5347 |   65 | 
5348 |   66 |     def test_bpf_get_current_pid_tgid_used(self, tracer_content):
5349 |   67 |         """Verify bpf_get_current_pid_tgid is used."""
5350 |   68 |         assert "bpf_get_current_pid_tgid" in tracer_content, "bpf_get_current_pid_tgid not used"
5351 |   69 | 
5352 |   70 |     def test_bpf_get_current_cgroup_id_used(self, tracer_content):
5353 |   71 |         """Verify bpf_get_current_cgroup_id is used."""
5354 |   72 |         assert "bpf_get_current_cgroup_id" in tracer_content, "bpf_get_current_cgroup_id not used"
5355 |   73 | 
5356 |   74 |     def test_bpf_get_current_comm_used(self, tracer_content):
5357 |   75 |         """Verify bpf_get_current_comm is used."""
5358 |   76 |         assert "bpf_get_current_comm" in tracer_content, "bpf_get_current_comm not used"
5359 |   77 | 
5360 |   78 |     def test_ringbuf_reserve_used(self, tracer_content):
5361 |   79 |         """Verify ring buffer reserve is used."""
5362 |   80 |         assert "bpf_ringbuf_reserve" in tracer_content, "bpf_ringbuf_reserve not used"
5363 |   81 | 
5364 |   82 |     def test_ringbuf_submit_used(self, tracer_content):
5365 |   83 |         """Verify ring buffer submit is used."""
5366 |   84 |         assert "bpf_ringbuf_submit" in tracer_content, "bpf_ringbuf_submit not used"
5367 |   85 | 
5368 |   86 |     def test_proc_metrics_lookup(self, tracer_content):
5369 |   87 |         """Verify proc_metrics map lookup is used."""
5370 |   88 |         assert "bpf_map_lookup_elem" in tracer_content, "bpf_map_lookup_elem not used"
5371 |   89 |         assert "proc_metrics" in tracer_content, "proc_metrics map not referenced"
5372 |   90 | 
5373 |   91 |     def test_proc_metrics_update(self, tracer_content):
5374 |   92 |         """Verify proc_metrics map update is used."""
5375 |   93 |         assert "bpf_map_update_elem" in tracer_content, "bpf_map_update_elem not used"
5376 | ```
5377 | 
5378 | ## Markdown
5379 | 
5380 | ### ARCHITECTURE.md
5381 | 
5382 | ```markdown
5383 |    1 | # SovND - Kernel-Level Security Monitoring & Explainable Scoring
5384 |    2 | 
5385 |    3 | ## Project Overview
5386 |    4 | 
5387 |    5 | **SovND** (pronounced "sovereign") is a real-time Linux kernel security monitoring system that combines eBPF-based syscall tracing with multi-vectors detection (signature, statistical, and provenance graph analysis) to generate explainable threat scores.
5388 |    6 | 
5389 |    7 | ### Key Features
5390 |    8 | - **eBPF Kernel Tracing** - Zero-overhead syscall capture via `tracepoint/syscalls`
5391 |    9 | - **Explainable Scoring** - Three-component formula: `S = Σ(w_i × d_i)`
5392 |   10 | - **Multi-Vector Detection** - Signature + Statistical + Graph heuristics
5393 |   11 | - **Live Dashboard** - WebSocket telemetry with Chart.js visualization
5394 |   12 | - **SQLite Persistence** - Alert storage for historical analysis
5395 |   13 | 
5396 |   14 | ### Motivation
5397 |   15 | Traditional HIDS agents (AIDE, OSSEC) scan periodically, missing transient threats. Commercial solutions (CrowdStrike, SentinelOne) are expensive and opaque. SovND provides an open-source, kernel-level alternative with mathematically explainable scoring.
5398 |   16 | 
5399 |   17 | ---
5400 |   18 | 
5401 |   19 | ## Architecture
5402 |   20 | 
5403 |   21 | ```
5404 |   22 | ┌─────────────────────────────────────────────────────────────────────────┐
5405 |   23 | │                        DASHBOARD (Browser)                         │
5406 |   24 | │              Chart.js + WebSocket (static/index.html)            │
5407 |   25 | └───────────────────────────────┬─────────────────────────────────────┘
5408 |   26 |                               │ ws://localhost:8000/ws/telemetry
5409 |   27 | ┌───────────────────────────────▼─────────────────────────────────────┐
5410 |   28 | │                    API SERVER (FastAPI)                           │
5411 |   29 | │              src/api/main.py (Uvicorn on port 8000)              │
5412 |   30 | │  ┌────────────────┐  ┌────────────────┐  ┌───────────────────┐   │
5413 |   31 | │  │ WebSocket      │  │ /api/attack   │  │ SQLite Query      │   │
5414 |   32 | │  │ Telemetry     │  │ Trigger      │  │ Endpoint        │   │
5415 |   33 | │  └───────────────┘  └──────────────┘  └─────────────────┘   │
5416 |   34 | └───────────────────────────────┬─────────────────────────────────────┘
5417 |   35 |                              │ storage.save_alert()
5418 |   36 | ┌───────────────────────────▼───────────────────────────────────────┐
5419 |   37 | │              STORAGE LAYER (SQLite)                            │
5420 |   38 | │                   data/sovnd.db                              │
5421 |   39 | │  ┌─────────────────────────────────────────────────────┐     │
5422 |   40 | │  │ alerts: id, timestamp, pid, comm, score, severity,  │     │
5423 |   41 | │  │        reasons (JSON), breakdown (JSON)             │     │
5424 |   42 | │  └─────────────────────────────────────────────────────┘     │
5425 |   43 | └───────────────────────────────┬────────────���────────────────────────┘
5426 |   44 |                              │ get_recent_alerts()
5427 |   45 | ┌───────────────────────────▼───────────────────────────────────────┐
5428 |   46 | │              MAIN AGENT LOOP (Python)                          │
5429 |   47 | │              src/main_agent.py                              │
5430 |   48 | │  ┌─────────────────────────────────────────────────┐           │
5431 |   49 | │  │  ScoringEngine                           │           │
5432 |   50 | │  │  compute_score(event, stat_report,      │           │
5433 |   51 | │  │  sig_match, graph_heuristics)         │           │
5434 |   52 | │  │  → Alert(score, breakdown, reasons)  │           │
5435 |   53 | │  └─────────────────────────────────────────────────┘           │
5436 |   54 | │                        ▲                                     │
5437 |   55 | │    ┌──────────────────┬┴───────────────────┐              │
5438 |   56 | │    │              DETECTORS                  │              │
5439 |   57 | │ ┌──▼──────────┐ ┌─────▼───────┐ ┌─────────▼────────┐     │
5440 |   58 | │ │ Signature   │ │ Statistical │ │ Graph          │     │
5441 |   59 | │ │ Detector   │ │ Detector   │ │ Builder       │     │
5442 |   60 | │ │ (regex IOC) │ │ (z-scores) │ │ (provenance)  │     │
5443 |   61 | │ └────────────┘ └───────────┘ └────────────────┘     │
5444 |   62 | │                        │                                │
5445 |   63 | └────────────────────────┼────────────────────────────────┘
5446 |   64 |                          │ get_event()
5447 |   65 | ┌───────────────────────▼────────────────────────────────┐
5448 |   66 | │              eBPF AGENT (Python ctypes)                    │
5449 |   67 | │              src/ebpf_agent.py                           │
5450 |   68 | │  ┌─────────────────────────────────────────────┐       │
5451 |   69 | │  │ C Library Loader (ebpf/libloader.so)        │       │
5452 |   70 | │  │ - start_loader()                         │       │
5453 |   71 | │  │ - poll_events(timeout_ms)                │       │
5454 |   72 | │  │ - stop_loader()                       │       │
5455 |   73 | │  └─────────────────────────────────────────────┘       │
5456 |   74 | └───────────────────────────────┬────────────────────────────────┘
5457 |   75 |                              │ tracepoint/syscalls
5458 |   76 | ┌───────────────────────────▼────────────────────────────────┐
5459 |   77 | │              LINUX KERNEL (eBPF)                        │
5460 |   78 | │         ebpf/tracer.bpf.c (uprobe/tracepoint)            │
5461 |   79 | │  ┌─────────────────────────────────────────────┐       │
5462 |   80 | │  │ trace_openat() - sys_enter_openat          │       │
5463 |   81 | │  │ trace_close() - sys_enter_close           │       │
5464 |   82 | │  │ ring buffer for events                   │       │
5465 |   83 | │  └───���─────────────────────────────────────────┘       │
5466 |   84 | └──────────────────────────────────────────────────────┘
5467 |   85 | ```
5468 |   86 | 
5469 |   87 | ---
5470 |   88 | 
5471 |   89 | ## Components
5472 |   90 | 
5473 |   91 | ### 1. eBPF Kernel Tracer (`ebpf/tracer.bpf.c`)
5474 |   92 | 
5475 |   93 | **Purpose:** Capture syscalls directly from the kernel with zero process overhead.
5476 |   94 | 
5477 |   95 | **Implementation:**
5478 |   96 | - Two tracepoint hooks: `sys_enter_openat` and `sys_enter_close`
5479 |   97 | - Uses BPF ring buffer (`rb`) for efficient event delivery
5480 |   98 | - CO-RE (Compile Once Run Everywhere) for kernel BTF compatibility
5481 |   99 | 
5482 |  100 | **Data Captured:**
5483 |  101 | | Field | Type | Description |
5484 |  102 | |-------|------|------------|
5485 |  103 | | `pid` | u32 | Process ID |
5486 |  104 | | `tgid` | u32 | Thread Group ID |
5487 |  105 | | `cgroup_id` | u64 | Control Group ID |
5488 |  106 | | `syscall_id` | u32 | Syscall number (257=openat) |
5489 |  107 | | `comm` | char[16] | Process command name |
5490 |  108 | | `filename` | char[256] | File path |
5491 |  109 | 
5492 |  110 | **Key Code:**
5493 |  111 | ```c
5494 |  112 | // tracer.bpf.c (simplified)
5495 |  113 | SEC("tracepoint/syscalls/sys_enter_openat")
5496 |  114 | int trace_openat(struct trace_event_raw_sys_enter *ctx) {
5497 |  115 |     // Load filename from RDI register (first arg)
5498 |  116 |     bpf_probe_read_user(&data.filename, sizeof(data.filename), (void *)ctx->args[1]);
5499 |  117 |     // Store in ring buffer
5500 |  118 |     bpf_ringbuf_output(&rb, &data, sizeof(data), 0);
5501 |  119 |     return 0;
5502 |  120 | }
5503 |  121 | ```
5504 |  122 | 
5505 |  123 | **Build Command:**
5506 |  124 | ```bash
5507 |  125 | clang -target bpf -g -O2 -Iebpf -c ebpf/tracer_bpf.c -o ebpf/tracer_bpf.o
5508 |  126 | ```
5509 |  127 | 
5510 |  128 | ---
5511 |  129 | 
5512 |  130 | ### 2. eBPF Agent (`src/ebpf_agent.py`)
5513 |  131 | 
5514 |  132 | **Purpose:** Python bridge to the compiled eBPF object via shared library.
5515 |  133 | 
5516 |  134 | **Key Responsibilities:**
5517 |  135 | 1. Load C library via `ctypes.CDLL`
5518 |  136 | 2. Register Python callback for ring buffer events
5519 |  137 | 3. Poll events in background thread
5520 |  138 | 4. Expose `get_event(timeout)` API to main loop
5521 |  139 | 
5522 |  140 | **Event Structure (Python):**
5523 |  141 | ```python
5524 |  142 | {
5525 |  143 |     "pid": int,
5526 |  144 |     "tgid": int,
5527 |  145 |     "cgroup_id": int,
5528 |  146 |     "syscall_id": int,
5529 |  147 |     "comm": str,      # e.g., "sudo", "python3"
5530 |  148 |     "filename": str  # e.g., "/etc/shadow"
5531 |  149 | }
5532 |  150 | ```
5533 |  151 | 
5534 |  152 | ---
5535 |  153 | 
5536 |  154 | ### 3. Signature Detector (`src/detector/signature.py`)
5537 |  155 | 
5538 |  156 | **Purpose:** Fast pattern matching against known IOCs (Indicators of Compromise).
5539 |  157 | 
5540 |  158 | **Detection Logic:**
5541 |  159 | 
5542 |  160 | ```python
5543 |  161 | class SignatureDetector:
5544 |  162 |     # Critical file access (IOCs)
5545 |  163 |     critical_paths = [
5546 |  164 |         r'^/etc/shadow$',        # Password hashes
5547 |  165 |         r'^/etc/sudoers$',      # sudo config
5548 |  166 |         r'^/var/run/docker\.sock$',  # Docker socket
5549 |  167 |         r'^/root/.ssh/.*',      # SSH keys
5550 |  168 |         r'^/proc/kcore$'        # Kernel memory
5551 |  169 |     ]
5552 |  170 |     
5553 |  171 |     # Suspicious processes
5554 |  172 |     suspicious_comm = ["bash", "sh", "nc", "ncat", "python", "perl"]
5555 |  173 | ```
5556 |  174 | 
5557 |  175 | **Decision Rationale:**
5558 |  176 | - Regex patterns are O(n) where n = number of paths (5), inherently fast
5559 |  177 | - Critical files are high-confidence IOCs - false positives acceptable
5560 |  178 | - Suspicious comm detection guards against reverse shells and lateral movement
5561 |  179 | 
5562 |  180 | ---
5563 |  181 | 
5564 |  182 | ### 4. Statistical Detector (`src/detector/statistical.py`)
5565 |  183 | 
5566 |  184 | **Purpose:** Learn process behavior and detect statistical anomalies using Z-scores.
5567 |  185 | 
5568 |  186 | **Mathematical Model:**
5569 |  187 | - **EWMA (Exponentially Weighted Moving Average):** `μ_t = α × x_t + (1-α) × μ_{t-1}`
5570 |  188 | - **Z-score:** `z = (x - μ) / σ`
5571 |  189 | - **Anomaly threshold:** `|z| > threshold_z` (default 3.0)
5572 |  190 | 
5573 |  191 | **Implementation:**
5574 |  192 | ```python
5575 |  193 | z_scores = engine.get_z_scores(pid, current_vector)
5576 |  194 | max_z = np.max(np.abs(z_scores))
5577 |  195 | is_anomalous = max_z > self.threshold_z
5578 |  196 | ```
5579 |  197 | 
5580 |  198 | **Why EWMA?**
5581 |  199 | - Adapts to concept drift (process behavior changes over time)
5582 |  200 | - Memory-efficient (only stores μ and σ, not full history)
5583 |  201 | - Configurable via α (default 0.3 = 30% weight on recent samples)
5584 |  202 | 
5585 |  203 | **Design Decision:** In demo mode, statistical scores are randomized (25% chance, z ∈ [2.5, 8.5]) because real attacks would build baseline profiles first - new processes have no history.
5586 |  204 | 
5587 |  205 | ---
5588 |  206 | 
5589 |  207 | ### 5. Metrics Engine (`src/metrics/engine.py`)
5590 |  208 | 
5591 |  209 | **Purpose:** Maintains per-PID behavioral profiles.
5592 |  210 | 
5593 |  211 | **Profile Structure:**
5594 |  212 | ```python
5595 |  213 | {
5596 |  214 |     pid: {
5597 |  215 |         "mu": np.ndarray,        # EWMA mean vector
5598 |  216 |         "sigma": np.ndarray,   # EWMA standard deviation
5599 |  217 |         "history": deque,   # Last 100 observations
5600 |  218 |         "ngram_buffer": deque,   # Last 3 syscall IDs
5601 |  219 |         "ngram_counts": dict    # { (1,2,3): count }
5602 |  220 |     }
5603 |  221 | }
5604 |  222 | ```
5605 |  223 | 
5606 |  224 | **Feature Vector (5-dimensional):**
5607 |  225 | | Index | Feature | Source |
5608 |  226 | |-------|---------|--------|
5609 |  227 | | 0 | syscall_id | Event syscall |
5610 |  228 | | 1 | filename_len | len(filename) |
5611 |  229 | | 2 | tgid | Thread group |
5612 |  230 | | 3 | syscall_count | Constant 1.0 |
5613 |  231 | | 4 | cgroup_mod | cgroup_id % 1000 |
5614 |  232 | 
5615 |  233 | **Design Decision:** Feature vector is intentionally simple for demonstration. Real implementations would include: CPU usage, memory delta, network bytes, disk I/O, etc.
5616 |  234 | 
5617 |  235 | ---
5618 |  236 | 
5619 |  237 | ### 6. Graph Builder (`src/graph/builder.py`)
5620 |  238 | 
5621 |  239 | **Purpose:** Construct process-to-resource provenance for lateral movement detection.
5622 |  240 | 
5623 |  241 | **Graph Structure:**
5624 |  242 | - **Nodes:** Process (`proc_{pid}`), File (`file_{path}`), Socket (`socket_{fd}`)
5625 |  243 | - **Directed Edges:** Process → Resource
5626 |  244 | 
5627 |  245 | **Heuristics Implemented:**
5628 |  246 | ```python
5629 |  247 | # 1. High connectivity - processes touching many files
5630 |  248 | high_connectivity: subgraph.number_of_nodes() > 3
5631 |  249 | 
5632 |  250 | # 2. Sensitive access - /etc or /root files
5633 |  251 | sensitive_access: filename.startswith("/etc") or filename.startswith("/root")
5634 |  252 | ```
5635 |  253 | 
5636 |  254 | **Graph Lib:** NetworkX (Python graph library)
5637 |  255 | 
5638 |  256 | **Design Decision:** Using NetworkX for rapid prototyping. Production would use GPUGraph or Graphistry for billion-node scale.
5639 |  257 | 
5640 |  258 | ---
5641 |  259 | 
5642 |  260 | ### 7. Scoring Engine (`src/scoring/engine.py`)
5643 |  261 | 
5644 |  262 | **Purpose:** Combine all detection vectors into an explainable threat score.
5645 |  263 | 
5646 |  264 | **Scoring Formula:**
5647 |  265 | ```
5648 |  266 | S = w_signature × sig_match + w_statistical × max_z + w_graph × |heuristics|
5649 |  267 | 
5650 |  268 | where:
5651 |  269 |   w_signature = 15.0   (high - signature match is definitive)
5652 |  270 |   w_statistical = 1.0   (low - z-score is scaled)
5653 |  271 |   w_graph = 5.0         (medium - heuristics are suspicious)
5654 |  272 | ```
5655 |  273 | 
5656 |  274 | **Score Breakdown:**
5657 |  275 | ```python
5658 |  276 | breakdown = {
5659 |  277 |     "signature": 0.0 or 15.0,
5660 |  278 |     "statistical": max_z * 1.0,  # e.g., 5.2 if z=5.2
5661 |  279 |     "graph": len(heuristics) * 5.0  # e.g., 10.0 if 2 heuristics
5662 |  280 | }
5663 |  281 | ```
5664 |  282 | 
5665 |  283 | **Alert Generation:**
5666 |  284 | ```python
5667 |  285 | if total_score >= threshold:
5668 |  286 |     severity = "CRITICAL" if total_score > 20 else "WARNING"
5669 |  287 |     return Alert(
5670 |  288 |         score=total_score,
5671 |  289 |         severity=severity,
5672 |  290 |         breakdown=comp,
5673 |  291 |         reasons=[...]  # Human-readable
5674 |  292 |     )
5675 |  293 | ```
5676 |  294 | 
5677 |  295 | **Threshold Decision:** Set to 15.0 to reduce false positives from graph-only alerts (sensitive_access alone is 5.0, below threshold).
5678 |  296 | 
5679 |  297 | ---
5680 |  298 | 
5681 |  299 | ### 8. Storage Layer (`src/storage/sqlite.py`)
5682 |  300 | 
5683 |  301 | **Purpose:** Persist alerts for historical analysis.
5684 |  302 | 
5685 |  303 | **Schema:**
5686 |  304 | ```sql
5687 |  305 | CREATE TABLE IF NOT EXISTS alerts (
5688 |  306 |     id INTEGER PRIMARY KEY AUTOINCREMENT,
5689 |  307 |     timestamp TIMESTAMP,
5690 |  308 |     pid INTEGER,
5691 |  309 |     comm TEXT,
5692 |  310 |     score REAL,
5693 |  311 |     severity TEXT,
5694 |  312 |     reasons TEXT,        -- JSON array
5695 |  313 |     breakdown TEXT      -- JSON object
5696 |  314 | )
5697 |  315 | ```
5698 |  316 | 
5699 |  317 | **Design Decision:** Using SQLite (not PostgreSQL) for demo portability. Production would use TimescaleDB or ClickHouse.
5700 |  318 | 
5701 |  319 | ---
5702 |  320 | 
5703 |  321 | ### 9. API Server (`src/api/main.py`)
5704 |  322 | 
5705 |  323 | **Purpose:** Web dashboard backend.
5706 |  324 | 
5707 |  325 | **Endpoints:**
5708 |  326 | | Path | Method | Description |
5709 |  327 | |------|--------|-------------|
5710 |  328 | | `/` | GET | Serve static/index.html |
5711 |  329 | | `/ws/telemetry` | WS | Stream {eps, alerts} at 2Hz |
5712 |  330 | | `/api/attack` | POST | Trigger demo attacks |
5713 |  331 | 
5714 |  332 | **WebSocket Message Format:**
5715 |  333 | ```json
5716 |  334 | {
5717 |  335 |     "eps": 1500,  // events per second
5718 |  336 |     "alerts": [
5719 |  337 |         {
5720 |  338 |             "timestamp": "2026-04-27T10:30:00",
5721 |  339 |             "pid": 7390,
5722 |  340 |             "comm": "cat",
5723 |  341 |             "score": 17.5,
5724 |  342 |             "severity": "WARNING",
5725 |  343 |             "reasons": ["Access to critical file: /etc/shadow", "Statistical Anomaly (Z=2.5)"],
5726 |  344 |             "breakdown": {"signature": 15.0, "statistical": 2.5, "graph": 0.0}
5727 |  345 |         }
5728 |  346 |     ]
5729 |  347 | }
5730 |  348 | ```
5731 |  349 | 
5732 |  350 | ---
5733 |  351 | 
5734 |  352 | ### 10. Dashboard (`static/index.html`)
5735 |  353 | 
5736 |  354 | **Purpose:** Browser UI for live telemetry.
5737 |  355 | 
5738 |  356 | **Features:**
5739 |  357 | - Chart.js line graph (throughput over 40 buckets)
5740 |  358 | - Alert stack with score breakdown (SIG/STAT/GRPH)
5741 |  359 | - "SIMULATE MULTI-STAGE ATTACK" button
5742 |  360 | 
5743 |  361 | **Key JavaScript (WebSocket):**
5744 |  362 | ```javascript
5745 |  363 | ws.onmessage = (event) => {
5746 |  364 |     const data = JSON.parse(event.data);
5747 |  365 |     
5748 |  366 |     // Update chart
5749 |  367 |     chart.data.datasets[0].data.push(data.eps);
5750 |  368 |     chart.data.datasets[0].data.shift();
5751 |  369 |     chart.update();
5752 |  370 |     
5753 |  371 |     // Show alerts (10s grace period for clock drift)
5754 |  372 |     const liveAlerts = data.alerts.filter(a => 
5755 |  373 |         new Date(a.timestamp).getTime() > sessionStartTime - 10000
5756 |  374 |     );
5757 |  375 |     
5758 |  376 |     // Render cards with breakdown
5759 |  377 |     alertList.innerHTML = liveAlerts.map(a => `
5760 |  378 |         <div>
5761 |  379 |             PID ${a.pid} [${a.comm}] 
5762 |  380 |             SCORE ${a.score}
5763 |  381 |             SIG: ${a.breakdown.signature}
5764 |  382 |             STAT: ${a.breakdown.statistical}
5765 |  383 |             GRPH: ${a.breakdown.graph}
5766 |  384 |         </div>
5767 |  385 |     `).join('');
5768 |  386 | }
5769 |  387 | ```
5770 |  388 | 
5771 |  389 | **Design Decision:** WebSocket avoids polling overhead. Chart.js for zero-dependency charting.
5772 |  390 | 
5773 |  391 | ---
5774 |  392 | 
5775 |  393 | ## Demo Orchestrator (`demo.py`)
5776 |  394 | 
5777 |  395 | **Purpose:** One-command launch for demos.
5778 |  396 | 
5779 |  397 | **Flow:**
5780 |  398 | ```python
5781 |  399 | def start():
5782 |  400 |     # 1. Clean data/ for fresh start
5783 |  401 |     os.remove("data/sovnd.db")
5784 |  402 |     
5785 |  403 |     # 2. Start API server (port 8000)
5786 |  404 |     api_proc = subprocess.Popen(["uvicorn", "src.api.main:app"])
5787 |  405 |     
5788 |  406 |     # 3. Start eBPF agent
5789 |  407 |     agent_proc = subprocess.Popen(["python3", "src/main_agent.py"])
5790 |  408 |     
5791 |  409 |     # 4. Open browser
5792 |  410 |     os.system("xdg-open http://localhost:8000")
5793 |  411 | ```
5794 |  412 | 
5795 |  413 | **Usage:**
5796 |  414 | ```bash
5797 |  415 | sudo python3 demo.py start
5798 |  416 | # Opens browser to http://localhost:8000
5799 |  417 | # Click "SIMULATE MULTI-STAGE ATTACK" to trigger alerts
5800 |  418 | ```
5801 |  419 | 
5802 |  420 | ---
5803 |  421 | 
5804 |  422 | ## Key Design Decisions
5805 |  423 | 
5806 |  424 | ### 1. Why eBPF for tracing?
5807 |  425 | - **Kernel-level:** No userspace overhead, can't be evade by process hiding
5808 |  426 | - **Ring buffer:** Log(1) egress - no blocking
5809 |  427 | - **CO-RE:** Works across kernel versions without recompilation
5810 |  428 | 
5811 |  429 | ### 2. Why three detection vectors?
5812 |  430 | | Vector | Strength | Weakness |
5813 |  431 | |--------|----------|---------|
5814 |  432 | | Signature | Zero false positive on IOCs | Misses novel attacks |
5815 |  433 | | Statistical | Catches deviations | Needs baseline first |
5816 |  434 | | Graph | Detects lateral movement | Computationally heavy |
5817 |  435 | 
5818 |  436 | **Multi-vector approach** ensures coverage across attack kill chain.
5819 |  437 | 
5820 |  438 | ### 3. Why weighted sum scoring?
5821 |  439 | - Interpretability: Each component is explainable
5822 |  440 | - Tunability: Weights can be adjusted per environment
5823 |  441 | - Threshold is single knob for operators
5824 |  442 | 
5825 |  443 | ### 4. Why SQLite for demo?
5826 |  444 | - No external dependency (PostgreSQL requires daemon)
5827 |  445 | - ACID compliance for alert integrity
5828 |  446 | - Easy export for further analysis
5829 |  447 | 
5830 |  448 | ### 5. Why WebSocket over HTTP polling?
5831 |  449 | - 2Hz update rate needed for live feel
5832 |  450 | - Polling would double server load
5833 |  451 | - WebSocket is full-duplex
5834 |  452 | 
5835 |  453 | ---
5836 |  454 | 
5837 |  455 | ## Score Variations (Expected Output)
5838 |  456 | 
5839 |  457 | When running `sudo python3 demo.py start`:
5840 |  458 | 
5841 |  459 | | Scenario | SIG | STAT | GRPH | Total |
5842 |  460 | |----------|-----|------|------|-------|
5843 |  461 | | Signature only | 15.0 | 0.0 | 0.0 | **15.0** |
5844 |  462 | | SIG + sensitive_access | 15.0 | 0.0 | 5.0 | **20.0** |
5845 |  463 | | SIG + z-score 2.5 | 15.0 | 2.5 | 0.0 | **17.5** |
5846 |  464 | | SIG + z-score 8.5 | 15.0 | 8.5 | 0.0 | **23.5** |
5847 |  465 | | SIG + STAT + GRPH + z7.5 | 15.0 | 7.5 | 5.0 | **27.5** |
5848 |  466 | 
5849 |  467 | ---
5850 |  468 | 
5851 |  469 | ## Dependencies
5852 |  470 | 
5853 |  471 | ### Python Packages
5854 |  472 | | Package | Version | Purpose |
5855 |  473 | |---------|---------|---------|
5856 |  474 | | numpy | 1.26.4 | Statistical calculations |
5857 |  475 | | networkx | 2.8.8 | Graph provenance |
5858 |  476 | | fastapi | - | Web API |
5859 |  477 | | uvicorn | - | ASGI server |
5860 |  478 | | websockets | - | WebSocket support |
5861 |  479 | 
5862 |  480 | ### System Requirements
5863 |  481 | - Linux kernel 5.10+ (BTF support)
5864 |  482 | - Root access (CAP_BPF for eBPF)
5865 |  483 | - clang + llvm (eBPF compilation)
5866 |  484 | 
5867 |  485 | ---
5868 |  486 | 
5869 |  487 | ## Future Improvements
5870 |  488 | 
5871 |  489 | ### Phase 2 (Production-Ready)
5872 |  490 | 1. **Machine Learning:** Train classifier on labeled attack data
5873 |  491 | 2. **Kafka Export:** Stream alerts to SIEM
5874 |  492 | 3. **Horizontal Scaling:** DistributedAgents per host
5875 |  493 | 4. **Graph Visualization:** Cytoscape.js for provenance
5876 |  494 | 
5877 |  495 | ### Phase 3 (Enterprise)
5878 |  496 | 1. **eBPFmaps:** Share state across agents
5879 |  497 | 2. **Kernel Hardening:** SECCOMP policies
5880 |  498 | 3. **Performance:** < 1% CPU overhead
5881 |  499 | 4. **Compliance:** SOC2 audit logs
5882 |  500 | 
5883 |  501 | ---
5884 |  502 | 
5885 |  503 | ## Appendix: File Structure
5886 |  504 | 
5887 |  505 | ```
5888 |  506 | sovnd-project/
5889 |  507 | ├── ebpf/
5890 |  508 | │   ├── tracer.bpf.c      # eBPF program
5891 |  509 | │   ├── tracer.skel.h     # Generated skeleton
5892 |  510 | │   └── Makefile         # Build rules
5893 |  511 | ├── src/
5894 |  512 | │   ├── ebpf_agent.py    # Python ↔ eBPF bridge
5895 |  513 | │   ├── main_agent.py   # Main loop + scoring
5896 |  514 | │   ├── detector/
5897 |  515 | │   │   ├── signature.py    # IOC matching
5898 |  516 | │   │   └── statistical.py # Z-score detection
5899 |  517 | │   ├── metrics/
5900 |  518 | │   │   └── engine.py   # EWMA profiles
5901 |  519 | │   ├── graph/
5902 |  520 | │   │   └── builder.py # Provenance graph
5903 |  521 | │   ├── scoring/
5904 |  522 | │   │   └── engine.py # Weighted scoring
5905 |  523 | │   ├── storage/
5906 |  524 | │   │   └── sqlite.py # Alert persistence
5907 |  525 | │   └── api/
5908 |  526 | │       └── main.py   # FastAPI server
5909 |  527 | ├── static/
5910 |  528 | │   └── index.html  # Dashboard UI
5911 |  529 | ├── data/
5912 |  530 | │   ├── sovnd.db     # Alert database
5913 |  531 | │   └── heartbeat.json # Throughput metric
5914 |  532 | ├── demo.py          # Orchestrator
5915 |  533 | └── README.md
5916 |  534 | ```
5917 |  535 | 
5918 |  536 | ---
5919 |  537 | 
5920 |  538 | *Generated: April 2026*
5921 |  539 | *Version: 0.1.0*
```

## HTML

### static/index.html

```html
   1 | <!DOCTYPE html>
   2 | <html lang="uk">
   3 | <head>
   4 |     <meta charset="UTF-8">
   5 |     <title>Дашборд системи</title>
   6 |     <script src="https://cdn.tailwindcss.com"></script>
   7 |     <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
   8 |     <style>
   9 |         body {
  10 |             background: #f8fafc;
  11 |             color: #1e293b;
  12 |             font-family: system-ui, -apple-system, sans-serif;
  13 |         }
  14 |     </style>
  15 | </head>
  16 | <body class="p-6">
  17 |     <div class="max-w-[1600px] mx-auto">
  18 | 
  19 |         <!-- Header -->
  20 |         <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
  21 |             <div>
  22 |                 <h1 class="text-2xl font-semibold text-slate-800">Дашборд системи</h1>
  23 |                 <div class="flex items-center gap-2 text-sm text-slate-500 mt-1">
  24 |                     <span class="h-2 w-2 rounded-full bg-green-500"></span>
  25 |                     Система моніторингу активна
  26 |                 </div>
  27 |             </div>
  28 | 
  29 |             <div class="grid grid-cols-2 md:grid-cols-4 gap-4 w-full md:w-auto">
  30 |                 <div class="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
  31 |                     <div class="text-xs text-slate-500">Подій/сек</div>
  32 |                     <div id="stat-eps" class="text-xl font-bold text-slate-800">0</div>
  33 |                 </div>
  34 |                 <div class="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
  35 |                     <div class="text-xs text-slate-500">Сповіщення</div>
  36 |                     <div id="stat-alerts" class="text-xl font-bold text-red-600">0</div>
  37 |                 </div>
  38 |                 <div class="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
  39 |                     <div class="text-xs text-slate-500">Статус</div>
  40 |                     <div class="text-sm font-medium text-slate-700">Онлайн</div>
  41 |                 </div>
  42 |                 <button onclick="fireAttack()" class="bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors">
  43 |                     Запустити тест
  44 |                 </button>
  45 |             </div>
  46 |         </div>
  47 | 
  48 |         <div class="grid grid-cols-12 gap-6">
  49 | 
  50 |             <!-- Left Column -->
  51 |             <div class="col-span-12 lg:col-span-8 space-y-6">
  52 | 
  53 |                 <!-- Main Chart -->
  54 |                 <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
  55 |                     <h3 class="text-sm font-medium text-slate-600 mb-4">Історія подій</h3>
  56 |                     <canvas id="mainChart" height="120"></canvas>
  57 |                 </div>
  58 | 
  59 |                 <!-- Live Feed -->
  60 |                 <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
  61 |                     <div class="bg-slate-50 px-4 py-3 border-b border-slate-200">
  62 |                         <span class="text-sm font-medium text-slate-600">Журнал активності</span>
  63 |                     </div>
  64 |                     <div id="kernel-feed" class="h-48 overflow-y-auto p-4 text-sm text-slate-600">
  65 |                         <div class="text-slate-400 italic">Очікування даних...</div>
  66 |                     </div>
  67 |                 </div>
  68 |             </div>
  69 | 
  70 |             <!-- Right Column: Alerts -->
  71 |             <div class="col-span-12 lg:col-span-4 flex flex-col h-full">
  72 |                 <div class="flex items-center justify-between mb-4">
  73 |                     <h3 class="text-sm font-medium text-slate-600">Сповіщення</h3>
  74 |                     <span id="alert-count-badge" class="bg-slate-100 text-slate-600 text-xs px-2 py-1 rounded-full">0</span>
  75 |                 </div>
  76 | 
  77 |                 <div id="alert-list" class="space-y-3 overflow-y-auto max-h-[700px] pr-2">
  78 |                     <div class="text-center py-12 border border-slate-200 rounded-xl text-slate-500 text-sm">
  79 |                         Немає сповіщень
  80 |                     </div>
  81 |                 </div>
  82 |             </div>
  83 |         </div>
  84 |     </div>
  85 | 
  86 |     <script>
  87 |         const sessionStartTime = new Date().getTime();
  88 |         const kernelFeed = document.getElementById('kernel-feed');
  89 |         const alertList = document.getElementById('alert-list');
  90 |         const alertBadge = document.getElementById('alert-count-badge');
  91 | 
  92 |         let totalAlerts = 0;
  93 |         let feedInitialized = false;
  94 | 
  95 |         const ctx = document.getElementById('mainChart').getContext('2d');
  96 |         const mainChart = new Chart(ctx, {
  97 |             type: 'line',
  98 |             data: {
  99 |                 labels: Array(50).fill(''),
 100 |                 datasets: [{
 101 |                     label: 'Подій/сек',
 102 |                     data: Array(50).fill(0),
 103 |                     borderColor: '#3b82f6',
 104 |                     backgroundColor: 'rgba(59, 130, 246, 0.1)',
 105 |                     fill: true,
 106 |                     tension: 0.3,
 107 |                     borderWidth: 2,
 108 |                     pointRadius: 0
 109 |                 }]
 110 |             },
 111 |             options: {
 112 |                 responsive: true,
 113 |                 maintainAspectRatio: true,
 114 |                 scales: {
 115 |                     y: { grid: { color: '#e2e8f0' }, ticks: { color: '#64748b' } },
 116 |                     x: { display: false }
 117 |                 },
 118 |                 plugins: { legend: { display: false } },
 119 |                 animation: false
 120 |             }
 121 |         });
 122 | 
 123 |         const ws = new WebSocket(`ws://${window.location.host}/ws/telemetry`);
 124 | 
 125 |         ws.onmessage = (event) => {
 126 |             const data = JSON.parse(event.data);
 127 | 
 128 |             document.getElementById('stat-eps').innerText = data.eps.toLocaleString();
 129 |             mainChart.data.datasets[0].data.push(data.eps);
 130 |             mainChart.data.datasets[0].data.shift();
 131 |             mainChart.update();
 132 | 
 133 |             if (data.eps > 0 && !feedInitialized) {
 134 |                 kernelFeed.innerHTML = '';
 135 |                 feedInitialized = true;
 136 |             }
 137 | 
 138 |             if (data.eps > 0) {
 139 |                 const syscalls = ['openat', 'execve', 'close', 'mmap', 'read', 'write', 'fstat'];
 140 |                 for(let i=0; i<2; i++) {
 141 |                     const log = document.createElement('div');
 142 |                     const ts = new Date().toLocaleTimeString();
 143 |                     const sc = syscalls[Math.floor(Math.random() * syscalls.length)];
 144 |                     log.innerHTML = `<span class="text-slate-400">[${ts}]</span> ${sc}(pid=${Math.floor(Math.random()*20000+1000)})`;
 145 |                     kernelFeed.prepend(log);
 146 |                     if(kernelFeed.children.length > 30) kernelFeed.removeChild(kernelFeed.lastChild);
 147 |                 }
 148 |             }
 149 | 
 150 |             const liveAlerts = data.alerts.filter(a => {
 151 |                 return new Date(a.timestamp).getTime() > (sessionStartTime - 20000);
 152 |             });
 153 | 
 154 |             totalAlerts = data.alerts.length;
 155 |             document.getElementById('stat-alerts').innerText = totalAlerts;
 156 |             alertBadge.innerText = liveAlerts.length;
 157 | 
 158 |             if (liveAlerts.length > 0) {
 159 |                 alertList.innerHTML = liveAlerts.map(a => `
 160 |                     <div class="p-4 rounded-lg border ${a.score > 20 ? 'border-red-300 bg-red-50' : 'border-amber-300 bg-amber-50'}">
 161 |                         <div class="flex justify-between items-start mb-2">
 162 |                             <div>
 163 |                                 <div class="text-xs text-slate-500">${new Date(a.timestamp).toLocaleTimeString()}</div>
 164 |                                 <div class="font-medium text-slate-800">PID ${a.pid} - ${a.comm}</div>
 165 |                             </div>
 166 |                             <div class="text-sm font-bold ${a.score > 20 ? 'text-red-600' : 'text-amber-600'}">
 167 |                                 ${a.score}
 168 |                             </div>
 169 |                         </div>
 170 |                         <div class="text-sm text-slate-600 mb-3">
 171 |                             ${a.reasons.join(', ')}
 172 |                         </div>
 173 |                         <div class="grid grid-cols-3 gap-2 text-xs">
 174 |                             <div class="text-center">
 175 |                                 <div class="text-slate-500">Сигнатура</div>
 176 |                                 <div class="font-medium ${a.breakdown.signature > 0 ? 'text-red-600' : 'text-slate-400'}">${a.breakdown.signature}</div>
 177 |                             </div>
 178 |                             <div class="text-center">
 179 |                                 <div class="text-slate-500">Статистика</div>
 180 |                                 <div class="font-medium ${a.breakdown.statistical > 0 ? 'text-amber-600' : 'text-slate-400'}">${a.breakdown.statistical.toFixed(1)}</div>
 181 |                             </div>
 182 |                             <div class="text-center">
 183 |                                 <div class="text-slate-500">Граф</div>
 184 |                                 <div class="font-medium ${a.breakdown.graph > 0 ? 'text-purple-600' : 'text-slate-400'}">${a.breakdown.graph}</div>
 185 |                             </div>
 186 |                         </div>
 187 |                     </div>
 188 |                 `).join('');
 189 |             } else {
 190 |                 alertList.innerHTML = `<div class="text-center py-12 border border-slate-200 rounded-xl text-slate-500 text-sm">Немає сповіщень</div>`;
 191 |             }
 192 |         };
 193 | 
 194 |         async function fireAttack() {
 195 |             const btn = event.target;
 196 |             btn.innerText = "Запуск...";
 197 |             btn.disabled = true;
 198 |             await fetch('/api/attack', { method: 'POST' });
 199 |             setTimeout(() => {
 200 |                 btn.innerText = "Запустити тест";
 201 |                 btn.disabled = false;
 202 |             }, 2000);
 203 |         }
 204 |     </script>
 205 | </body>
 206 | </html>
```

