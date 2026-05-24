import asyncio, json, os, time, random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Response
from fastapi.staticfiles import StaticFiles
from internal.storage.sqlite import StorageManager

app = FastAPI(
    title="SovND Security API",
    description="API for accessing eBPF-based security monitoring data",
    version="1.0.0"
)

storage = StorageManager()

def get_storage():
    return storage

# Ensure web directory exists for static files
os.makedirs("web", exist_ok=True)

class NoCacheStaticMount(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

# Mount static files to /static
app.mount("/static", NoCacheStaticMount(directory="web"), name="static")

@app.get("/")
async def get_index():
    """Serves the main security dashboard at root."""
    try:
        content = open("web/index.html", "r").read()
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
        return {"error": "Dashboard HTML not found in web/ index.html"}

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
                with open("data/heartbeat.json", "r") as f:
                    hb = json.load(f)
                    if time.time() - hb.get("timestamp", 0) < 3:
                        eps = hb.get("events_per_sec", 0)
            except: pass
            await websocket.send_json({"eps": eps, "alerts": alerts})
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass

@app.post("/api/attack")
async def trigger_attack():
    payloads = [
        {
            "type": "signature",
            "name": "Shadow File Access",
            "cmd": "cat /etc/shadow",
            "expected_reason": "Access to critical file: /etc/shadow",
            "description": "Attempts to read /etc/shadow for password hashes"
        },
        {
            "type": "signature",
            "name": "Sudoers Access",
            "cmd": "cat /etc/sudoers",
            "expected_reason": "Access to critical file: /etc/sudoers",
            "description": "Attempts to read sudo configuration"
        },
        {
            "type": "signature",
            "name": "Docker Socket Access",
            "cmd": "cat /var/run/docker.sock",
            "expected_reason": "Access to critical file: /var/run/docker.sock",
            "description": "Attempts to access Docker socket"
        },
        {
            "type": "signature",
            "name": "SSH Key Theft",
            "cmd": "cat /root/.ssh/id_rsa 2>/dev/null || echo no-key",
            "expected_reason": "Access to critical file: /root/.ssh",
            "description": "Attempts to steal SSH private keys"
        },
        {
            "type": "statistical",
            "name": "File Creation Storm",
            "cmd": "bash -c 'for i in $(seq 1 500); do echo x > /tmp/f$i; done' && rm -f /tmp/f*",
            "expected_reason": "Statistical Anomaly",
            "description": "Creates burst of file creates to trigger anomaly detection"
        },
        {
            "type": "statistical",
            "name": "Process Spawn Storm",
            "cmd": "bash -c 'for i in $(seq 1 200); do sleep 0.01 & done'",
            "expected_reason": "Statistical Anomaly",
            "description": "Spawns many processes rapidly"
        },
        {
            "type": "graph",
            "name": "Reconnaissance Scan",
            "cmd": "find /etc -type f -name '*.conf' -exec ls -la {} \\; 2>/dev/null | head -30",
            "expected_reason": "Graph Heuristic",
            "description": "Scans many config files triggering graph connections"
        },
        {
            "type": "graph",
            "name": "Recursive Directory Traverse",
            "cmd": "ls -laR /var /opt /home 2>/dev/null | head -100",
            "expected_reason": "Graph Heuristic",
            "description": "Recursively traverses directories creating graph edges"
        },
        {
            "type": "signature+graph",
            "name": "Sensitive Config Exfiltration",
            "cmd": "cat /etc/passwd /etc/shadow && find /etc -name '*.conf' 2>/dev/null | head -5",
            "expected_reason": "multiple",
            "description": "Combines signature file access with graph enumeration"
        },
        {
            "type": "signature+statistical",
            "name": "Credentials Dumping",
            "cmd": "cat /etc/shadow && bash -c 'for i in $(seq 1 300); do echo $i > /tmp/dump$i; done'",
            "expected_reason": "multiple",
            "description": "Reads shadow file plus creates file storm"
        },
        {
            "type": "graph+statistical",
            "name": "Network Recon Storm",
            "cmd": "bash -c 'for h in $(seq 1 50); do ping -c 1 127.0.0.$h 2>/dev/null; done' && ls -la /etc /var",
            "expected_reason": "multiple",
            "description": "Creates network activity + file access patterns"
        },
        {
            "type": "all_three",
            "name": "FullAttack Exfiltration",
            "cmd": "cat /etc/shadow >/dev/null 2>&1; bash -c 'for i in $(seq 1 400); do echo $i > /tmp/a$i; done'; find /root /etc -type f 2>/dev/null | head -10",
            "expected_reason": "multiple",
            "description": "Maximum signature + statistical + graph detection"
        },
    ]
    
    selected = random.choice(payloads)
    cmd = selected["cmd"]
    result = os.system(f"{cmd} > /dev/null 2>&1 &")
    
    return {
        "status": "attack_launched",
        "payload": {
            "name": selected["name"],
            "type": selected["type"],
            "description": selected["description"],
            "expected_reason": selected["expected_reason"]
        },
        "result": result
    }
