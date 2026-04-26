import logging
import json
import os
import asyncio
from typing import List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from src.storage.sqlite import StorageManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SovND Security API",
    description="API for accessing eBPF-based security monitoring data",
    version="1.0.0"
)

storage = StorageManager()

SYSCALL_COUNT = Counter("sovnd_syscalls_total", "Total number of intercepted syscalls")
ALERT_COUNT = Counter("sovnd_alerts_total", "Total number of security alerts generated", ["severity"])
CPU_USAGE = Gauge("sovnd_cpu_usage_percent", "System CPU usage reported by monitor")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_dashboard():
    return FileResponse("static/index.html")

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            alerts = storage.get_recent_alerts(limit=5)
            for alert in alerts:
                if isinstance(alert.get("reasons"), str):
                    alert["reasons"] = json.loads(alert["reasons"])
                if isinstance(alert.get("container_info"), str):
                    alert["container_info"] = json.loads(alert["container_info"])
            
            eps = 0
            try:
                with open("data/heartbeat.json", "r") as f:
                    eps = json.load(f).get("events_per_sec", 0)
            except:
                pass
            
            await websocket.send_json({
                "eps": eps,
                "alerts": alerts
            })
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/attack")
async def trigger_attack():
    os.system("cat /etc/shadow > /dev/null 2>&1")
    os.system("cat /var/run/docker.sock > /dev/null 2>&1")
    return {"status": "attack_launched"}

def get_storage():
    return StorageManager()

@app.get("/api/alerts", response_model=List[Dict[str, Any]])
async def get_alerts(limit: int = 50, storage: StorageManager = Depends(get_storage)):
    try:
        alerts = storage.get_recent_alerts(limit=limit)
        for alert in alerts:
            if isinstance(alert.get("reasons"), str):
                alert["reasons"] = json.loads(alert["reasons"])
            if isinstance(alert.get("container_info"), str):
                alert["container_info"] = json.loads(alert["container_info"])
        return alerts
    except Exception as e:
        logger.error("Failed to fetch alerts: %s", e)
        raise HTTPException(status_code=500, detail="Internal database error")

@app.get("/api/status")
async def get_status():
    return {
        "status": "operational",
        "engine": "eBPF-CO-RE",
        "version": "1.0.0"
    }

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)