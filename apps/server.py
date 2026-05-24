import asyncio
import json
import sys
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Response
from fastapi.staticfiles import StaticFiles

from core.config import get_settings
from internal.storage.sqlite import StorageManager

settings = get_settings()
app = FastAPI(
    title="SovND Security API",
    description="API for accessing eBPF-based security monitoring data",
    version="1.0.0"
)

storage = StorageManager(db_path=settings.db_path)

WEB_DIR = settings.web_dir

def get_storage():
    return storage

Path(WEB_DIR).mkdir(exist_ok=True)

class NoCacheStaticMount(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

app.mount("/static", NoCacheStaticMount(directory=WEB_DIR), name="static")

INDEX_PATH = Path(WEB_DIR) / "index.html"

@app.get("/")
async def get_index():
    """Serves the main security dashboard at root."""
    try:
        content = Path(INDEX_PATH).read_text()
        return Response(
            content,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    except FileNotFoundError:
        return {"error": f"Dashboard HTML not found in {WEB_DIR}/index.html"}

@app.get("/api")
async def get_api_root():
    """API discovery endpoint."""
    return {"message": "Welcome to the SovND API", "status": "operational"}

@app.get("/api/status")
async def get_status():
    """Returns the operational status of the monitoring engine."""
    return {
        "status": "operational",
        "engine": "eBPF-CO-RE",
        "version": "1.0.0"
    }

@app.get("/api/alerts")
async def get_alerts(limit: int = 50, storage: StorageManager = Depends(get_storage)):
    """Retrieves recent security alerts from storage."""
    return storage.get_recent_alerts(limit=limit)

@app.get("/metrics")
async def get_metrics():
    """Prometheus-compatible metrics endpoint."""
    metrics = (
        "# HELP sovnd_syscalls_total Total system calls observed\n"
        "# TYPE sovnd_syscalls_total counter\n"
        "sovnd_syscalls_total 0\n"
        "# HELP sovnd_cpu_usage_percent CPU usage of the agent\n"
        "# TYPE sovnd_cpu_usage_percent gauge\n"
        "sovnd_cpu_usage_percent 0.0\n"
    )
    return Response(content=metrics, media_type="text/plain")

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            alerts = storage.get_recent_alerts(limit=10)
            eps = 0
            try:
                heartbeat_data = Path(settings.heartbeat_path).read_text()
                hb = json.loads(heartbeat_data)
                if time.time() - hb.get("timestamp", 0) < 3:
                    eps = hb.get("events_per_sec", 0)
            except Exception:
                pass
            await websocket.send_json({"eps": eps, "alerts": alerts})
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass

_attack_cycle = -1

@app.post("/api/attack")
async def trigger_attack():
    global _attack_cycle
    _attack_cycle += 1

    payloads = [
        {
            "name": "Shadow File Access",
            "type": "sig only",
            "expected_score": 15,
            "cmd": "cat /etc/shadow >/dev/null",
            "description": "sig=15 — single IOC, baseline alert"
        },
        {
            "name": "Sudoers Tampering",
            "type": "sig only",
            "expected_score": 15,
            "cmd": "cat /etc/sudoers >/dev/null",
            "description": "sig=15 — single IOC, baseline alert"
        },
        {
            "name": "SSH Key Theft",
            "type": "sig+graph",
            "expected_score": 23,
            "cmd": "cat /root/.ssh/id_rsa 2>/dev/null; ls /root/.ssh/ 2>/dev/null; ls /root/ 2>/dev/null",
            "description": "sig=15 + graph=8 — root access scan"
        },
        {
            "name": "Docker Escape",
            "type": "sig+graph",
            "expected_score": 20,
            "cmd": "cat /var/run/docker.sock 2>/dev/null; ls /var/run/ 2>/dev/null",
            "description": "sig=15 + graph=5 — docker socket access"
        },
        {
            "name": "Ransomware Storm",
            "type": "graph only",
            "expected_score": 15,
            "cmd": "bash -c 'for i in $(seq 1 300); do echo x > /tmp/victim_$i; done; rm -f /tmp/victim_*'",
            "description": "graph=15 — 300 files → mass ops + connectivity"
        },
        {
            "name": "Config Reconnaissance",
            "type": "graph only",
            "expected_score": 8,
            "cmd": "find /etc -type f -name '*.conf' -exec ls -la {} \\; 2>/dev/null | head -40",
            "description": "graph=8 — etc enumeration (below threshold)"
        },
        {
            "name": "Shadow + Sudoers Exfil",
            "type": "sig+graph",
            "expected_score": 28,
            "cmd": "cat /etc/shadow >/dev/null; cat /etc/sudoers >/dev/null; ls /etc/ 2>/dev/null | head -10",
            "description": "sig=15 + graph=13 — dual IOC + etc scan → critical"
        },
        {
            "name": "Full Killchain",
            "type": "all three",
            "expected_score": 30,
            "cmd": "cat /etc/shadow >/dev/null; bash -c 'for i in $(seq 1 200); do echo $i > /tmp/kill_$i; done' 2>/dev/null; find /root /etc -type f 2>/dev/null | head -15",
            "description": "sig=15 + graph=15 — shadow + file storm + root scan"
        },
    ]

    selected = payloads[_attack_cycle % len(payloads)]
    cmd = selected["cmd"]
    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return {
        "status": "attack_launched",
        "payload": {
            "name": selected["name"],
            "type": selected["type"],
            "description": selected["description"],
            "expected_score": selected["expected_score"]
        }
    }
