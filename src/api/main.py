import asyncio, json, os, time, random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from src.storage.sqlite import StorageManager

app = FastAPI()
storage = StorageManager()

os.makedirs("static", exist_ok=True)
static_mount = StaticFiles(directory="static")

class NoCacheStaticMount(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

app.mount("/static", NoCacheStaticMount(directory="static"), name="static")

@app.get("/")
async def get_index():
    content = open("static/index.html", "r").read()
    return Response(
        content,
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

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
        # Signature detection (critical files)
        "cat /etc/shadow",
        "cat /etc/sudoers",
        "cat /var/run/docker.sock",
        "cat /root/.ssh/id_rsa",
        "cat /root/.ssh/known_hosts",
        "python3 -c 'open(\"/proc/kcore\").read()'",
        
        # Graph detection (sensitive directories)
        "find /etc -type f 2>/dev/null | head -20",
        "ls -la /root",
        "ls -la /etc/passwd",
        
        # Statistical anomaly (high frequency)
        "python3 -c 'import os; [os.system(f\"echo {i} > /tmp/x{i}\") for i in range(100)]'",
        "bash -c 'for i in {1..50}; do touch /tmp/test$i; done'",
        
        # Process anomalies
        "python3 -c 'import subprocess; [subprocess.Popen([\"sleep\", \"1\"]) for _ in range(20)]'",
        "bash -c 'fork() { fork | fork & }; fork'",
        
        # Network-like behavior
        "python3 -c 'import socket; s=socket.socket(); s.connect((\"8.8.8.8\",53))'",
        
        # File modification patterns
        "bash -c 'echo \"malware\" > /tmp/payload.sh && chmod +x /tmp/payload.sh'",
        "python3 -c 'open(\"/tmp/trace\",\"w\").write(\"x\"*10000)'",
        
        # Privilege escalation attempts
        "python3 -c 'import os; os.setuid(0)'",
        "sudo -n true",
    ]
    selected = random.sample(payloads, 4)
    for cmd in selected:
        os.system(f"{cmd} > /dev/null 2>&1 &")
    return {"status": f"{len(selected)}_attacks_launched", "payloads": selected}