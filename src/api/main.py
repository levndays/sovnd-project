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
        # High signature score (15 pts) - critical files
        ("signature", "cat /etc/shadow"),
        ("signature", "cat /etc/sudoers"),
        ("signature", "cat /var/run/docker.sock"),
        ("signature", "cat /root/.ssh/id_rsa"),
        
        # Graph heuristics - sensitive access
        ("graph", "find /etc -type f -name '*.conf' 2>/dev/null | head -10"),
        ("graph", "ls -la /root"),
        ("graph", "ls -la /etc/passwd /etc/shadow"),
        
        # Statistical anomaly - high frequency
        ("statistical", "bash -c 'for i in $(seq 1 100); do echo $i > /tmp/f$i; done'"),
        ("statistical", "touch /tmp/x{1..50}"),
        
        # Mixed - signature + graph
        ("both", "cat /etc/shadow && find /root -type f 2>/dev/null"),
    ]
    
    # Pick 3 random payloads
    selected = random.sample(payloads, 3)
    
    results = []
    for type_hint, cmd in selected:
        result = os.system(f"{cmd} > /dev/null 2>&1 &")
        results.append({"type": type_hint, "cmd": cmd, "result": result})
    
    return {"status": "attacks_launched", "count": len(selected), "payloads": results}