#!/usr/bin/env bash
# =============================================================================
# RAINGOD — Start All Services
# Starts ComfyUI and the RAINGOD FastAPI backend with health-check verification
# and graceful shutdown.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Colour codes
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Colour

log()  { echo -e "${GREEN}[RAINGOD]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}   $*"; }
err()  { echo -e "${RED}[ERROR]${NC}  $*" >&2; }

# ---------------------------------------------------------------------------
# Configuration (override via environment)
# ---------------------------------------------------------------------------
COMFYUI_DIR="${COMFYUI_DIR:-./ComfyUI}"
COMFYUI_HOST="${COMFYUI_HOST:-127.0.0.1}"
COMFYUI_PORT="${COMFYUI_PORT:-8188}"
BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
BACKEND_WORKERS="${BACKEND_WORKERS:-1}"
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-60}"  # seconds

PID_DIR=".pids"
LOG_DIR="logs"

mkdir -p "$PID_DIR" "$LOG_DIR"

# ---------------------------------------------------------------------------
# Graceful shutdown on SIGINT / SIGTERM
# ---------------------------------------------------------------------------
cleanup() {
    log "Shutting down services..."

    if [[ -f "$PID_DIR/backend.pid" ]]; then
        backend_pid=$(cat "$PID_DIR/backend.pid")
        if kill -0 "$backend_pid" 2>/dev/null; then
            log "Stopping RAINGOD backend (PID $backend_pid)..."
            kill -TERM "$backend_pid"
        fi
        rm -f "$PID_DIR/backend.pid"
    fi

    if [[ -f "$PID_DIR/comfyui.pid" ]]; then
        comfyui_pid=$(cat "$PID_DIR/comfyui.pid")
        if kill -0 "$comfyui_pid" 2>/dev/null; then
            log "Stopping ComfyUI (PID $comfyui_pid)..."
            kill -TERM "$comfyui_pid"
        fi
        rm -f "$PID_DIR/comfyui.pid"
    fi

    log "All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
wait_for_http() {
    local url="$1"
    local service="$2"
    local timeout="$STARTUP_TIMEOUT"
    local elapsed=0

    log "Waiting for $service at $url ..."
    while ! curl -sf "$url" > /dev/null 2>&1; do
        sleep 2
        elapsed=$((elapsed + 2))
        if (( elapsed >= timeout )); then
            err "$service did not respond within ${timeout}s"
            return 1
        fi
        echo -n "."
    done
    echo
    log "$service is ${GREEN}UP${NC} ✔"
    return 0
}

check_command() {
    if ! command -v "$1" &>/dev/null; then
        err "Required command not found: $1"
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
check_command python3
check_command uvicorn
check_command curl

# Check backend package is importable
if ! python3 -c "import backend.rain_backend" 2>/dev/null; then
    err "Cannot import backend.rain_backend."
    err "Run: pip install -r backend/requirements.txt"
    exit 1
fi

# ---------------------------------------------------------------------------
# Start ComfyUI
# ---------------------------------------------------------------------------
if [[ -d "$COMFYUI_DIR" ]]; then
    log "Starting ComfyUI from $COMFYUI_DIR ..."
    (
        cd "$COMFYUI_DIR"
        python3 main.py \
            --listen "$COMFYUI_HOST" \
            --port "$COMFYUI_PORT" \
            --cpu 2>&1 | tee "$LOG_DIR/comfyui.log"
    ) &
    echo $! > "$PID_DIR/comfyui.pid"
    log "ComfyUI PID: $(cat $PID_DIR/comfyui.pid)"

    wait_for_http "http://${COMFYUI_HOST}:${COMFYUI_PORT}/system_stats" "ComfyUI" \
        || { err "ComfyUI startup failed. Check logs/comfyui.log"; cleanup; }
else
    warn "ComfyUI directory not found at $COMFYUI_DIR — skipping ComfyUI startup."
    warn "Set COMFYUI_DIR env var or install with: scripts/rain_quickstart.sh"
fi

# ---------------------------------------------------------------------------
# Start RAINGOD Backend
# ---------------------------------------------------------------------------
log "Starting RAINGOD backend on ${BACKEND_HOST}:${BACKEND_PORT} ..."

uvicorn backend.rain_backend:app \
    --host "$BACKEND_HOST" \
    --port "$BACKEND_PORT" \
    --workers "$BACKEND_WORKERS" \
    --log-level info \
    2>&1 | tee "$LOG_DIR/backend.log" &

echo $! > "$PID_DIR/backend.pid"
log "Backend PID: $(cat $PID_DIR/backend.pid)"

wait_for_http "http://127.0.0.1:${BACKEND_PORT}/health" "RAINGOD backend" \
    || { err "Backend startup failed. Check logs/backend.log"; cleanup; }

# ---------------------------------------------------------------------------
# All services up
# ---------------------------------------------------------------------------
echo
log "====================================================="
log "  RAINGOD services are running"
log "  Backend:  http://127.0.0.1:${BACKEND_PORT}"
log "  API Docs: http://127.0.0.1:${BACKEND_PORT}/docs"
log "  ComfyUI:  http://${COMFYUI_HOST}:${COMFYUI_PORT}"
log "====================================================="
log "Press Ctrl+C to stop all services."

# Wait indefinitely — cleanup() handles SIGINT/SIGTERM
wait
