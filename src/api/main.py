import logging
import json
from typing import List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from src.storage.sqlite import StorageManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SovND Security API",
    description="API for accessing eBPF-based security monitoring data",
    version="1.0.0"
)

# Prometheus Metrics
SYSCALL_COUNT = Counter("sovnd_syscalls_total", "Total number of intercepted syscalls")
ALERT_COUNT = Counter("sovnd_alerts_total", "Total number of security alerts generated", ["severity"])
CPU_USAGE = Gauge("sovnd_cpu_usage_percent", "System CPU usage reported by monitor")

# Storage dependency
def get_storage():
    return StorageManager()

@app.get("/api/alerts", response_model=List[Dict[str, Any]])
async def get_alerts(limit: int = 50, storage: StorageManager = Depends(get_storage)):
    """Retrieves recent security alerts from persistent storage."""
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
    """Returns the current operational status of the monitoring system."""
    return {
        "status": "operational",
        "engine": "eBPF-CO-RE",
        "version": "1.0.0"
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/")
async def root():
    return {"message": "SovND API is running. Access /docs for API documentation."}
