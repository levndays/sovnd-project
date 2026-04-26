#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/.logs"
DB_PATH="$SCRIPT_DIR/data/sovnd.db"

mkdir -p "$LOG_DIR" "$SCRIPT_DIR/data"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

check_venv() {
    if [ ! -d "venv" ]; then
        error "venv not found. Run: python3 -m venv venv"
        exit 1
    fi
}

auth_sudo() {
    log "Requesting sudo access..."
    sudo -v
    if [ $? -eq 0 ]; then
        log "Sudo authenticated"
    else
        error "Sudo authentication failed"
        exit 1
    fi
}

kill_all() {
    log "Killing existing processes..."
    sudo pkill -f uvicorn 2>/dev/null || true
    sudo pkill -f streamlit 2>/dev/null || true
    sudo pkill -f "main_agent.py" 2>/dev/null || true
    sleep 1
    log "All processes killed"
}

clean_data() {
    log "Cleaning old data..."
    rm -f "$DB_PATH"
    rm -f "$SCRIPT_DIR/data/heartbeat.json"
    log "Database and telemetry cleared"
}

compile_ebpf() {
    if [ ! -f "$SCRIPT_DIR/ebpf/libloader.so" ]; then
        log "Compiling eBPF library..."
        cd "$SCRIPT_DIR/ebpf" && make
        cd "$SCRIPT_DIR"
        log "eBPF compiled"
    else
        log "eBPF library already exists"
    fi
}

start_api() {
    log "Starting API server..."
    nohup ./venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/api.log" 2>&1 &
    for i in {1..30}; do
        if curl -s http://localhost:8000/api/status > /dev/null 2>&1; then
            log "API running at http://localhost:8000"
            return 0
        fi
        sleep 1
    done
    error "Failed to start API"
    exit 1
}

start_dashboard() {
    log "Starting dashboard..."
    export STREAMLIT_SERVER_HEADLESS=true
    nohup ./venv/bin/streamlit run src/dashboard/app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true > "$LOG_DIR/dashboard.log" 2>&1 &
    log "Dashboard starting at http://localhost:8501"
}

start_agent() {
    if [ ! -f "$SCRIPT_DIR/ebpf/libloader.so" ]; then
        warn "eBPF libloader.so not found. Skipping agent."
        return
    fi

    log "Starting eBPF agent..."
    nohup sudo ./venv/bin/python src/main_agent.py > "$LOG_DIR/agent.log" 2>&1 &
    sleep 2
    log "eBPF agent started"
}

show_status() {
    echo ""
    echo "========================================"
    echo "         SOVND SYSTEM STATUS"
    echo "========================================"
    echo ""

    if curl -s http://localhost:8000/api/status > /dev/null 2>&1; then
        echo -e "${GREEN}API Server:${NC}  Running at http://localhost:8000"
    else
        echo -e "${RED}API Server:${NC}  Not running"
    fi

    echo -e "${GREEN}Dashboard:${NC} Running at http://localhost:8501"

    echo ""
    echo "----------------------------------------"
    echo "         RECENT ALERTS"
    echo "----------------------------------------"
    echo ""

    if [ -f "$DB_PATH" ] && [ -s "$DB_PATH" ]; then
        curl -s http://localhost:8000/api/alerts?limit=5 | ./venv/bin/python -m json.tool 2>/dev/null || echo "No alerts"
    else
        echo "No alerts (clean slate)"
    fi

    echo ""
    echo "========================================"
    echo ""
}

tail_logs() {
    case "${1:-all}" in
        api)
            tail -f "$LOG_DIR/api.log" ;;
        dashboard)
            tail -f "$LOG_DIR/dashboard.log" ;;
        agent)
            tail -f "$LOG_DIR/agent.log" ;;
        all)
            echo "=== API ===" && tail -30 "$LOG_DIR/api.log" 2>/dev/null || true
            echo "" && echo "=== Dashboard ===" && tail -30 "$LOG_DIR/dashboard.log" 2>/dev/null || true
            echo "" && echo "=== Agent ===" && tail -30 "$LOG_DIR/agent.log" 2>/dev/null || true
            ;;
    esac
}

show_help() {
    cat << EOF
SovND Demo Script

Usage: $0 <command>

Commands:
  start       Master reset: kills all, cleans, starts fresh (DEFAULT)
  stop        Stop all services
  status      Show system status
  logs        Show logs (api|dashboard|agent|all)

Examples:
  $0           # Same as start - full reset and start
  $0 start     # Full reset and start
  $0 logs      # View all logs
  $0 logs agent# View agent logs only

EOF
}

case "${1:-start}" in
    start)
        auth_sudo
        kill_all
        clean_data
        compile_ebpf
        start_api
        start_dashboard
        start_agent
        sleep 2
        show_status
        info "Ready! Dashboard: http://localhost:8501"
        ;;
    stop)
        auth_sudo
        kill_all
        log "All services stopped"
        ;;
    status)
        show_status
        ;;
    logs)
        tail_logs "${2:-all}"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac