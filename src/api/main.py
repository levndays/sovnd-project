import asyncio, json, os, time, random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.storage.sqlite import StorageManager

app = FastAPI()
storage = StorageManager()

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_index():
    return FileResponse("static/index.html")

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
        "cat /etc/shadow",
        "cat /var/run/docker.sock",
        "cat /etc/sudoers",
        "python3 -c 'import os; os.open(\"/proc/kcore\", 0)'",
        "python3 -c 'import os; os.open(\"/root/.ssh/id_rsa\", 0)'",
        "bash -c 'echo \"backdoor\" > /tmp/check'"
    ]
    selected = random.sample(payloads, 3)
    for cmd in selected:
        os.system(f"{cmd} > /dev/null 2>&1 &")
    return {"status": "3_attacks_launched"}