#!/usr/bin/env bash
# Portable foreground launcher. Never starts Ollama or downloads models.
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${PRAG_PYTHON:-$PROJECT_DIR/venv/bin/python}"
PORT="${PRAG_PORT:-8000}"
OPEN_BROWSER=1
CHECK_ONLY=0
UI_ONLY=0

while (($#)); do
    case "$1" in
        --check) CHECK_ONLY=1; shift ;;
        --no-browser) OPEN_BROWSER=0; shift ;;
        --ui-only) UI_ONLY=1; shift ;;
        --model)
            if (($# < 2)) || [[ -z "$2" || "$2" == --* ]]; then echo 'Missing value for --model' >&2; exit 2; fi
            export RAG_MODEL="$2"; shift 2 ;;
        --port)
            if (($# < 2)); then echo 'Missing value for --port' >&2; exit 2; fi
            PORT="$2"; shift 2 ;;
        --help|-h)
            echo 'Usage: ./launch.sh [--check] [--ui-only] [--no-browser] [--port PORT] [--model MODEL]'
            echo 'Ctrl+C stops the server. Ollama must be started separately for model answers.'
            exit 0 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done
if [[ ! "$PORT" =~ ^[0-9]{1,5}$ ]] || ((10#$PORT < 1 || 10#$PORT > 65535)); then
    echo 'Port must be between 1 and 65535.' >&2; exit 2
fi
PORT="$((10#$PORT))"
if [[ ! -x "$VENV_PYTHON" ]]; then
    echo 'Project virtual environment is missing. Follow DEPLOYMENT.md.' >&2; exit 1
fi
cd "$PROJECT_DIR"
CHECK_ARGS=()
if ((UI_ONLY)); then CHECK_ARGS+=(--ui-only); fi
"$VENV_PYTHON" scripts/check_ready.py "${CHECK_ARGS[@]}"
if ((CHECK_ONLY)); then exit 0; fi

# Fail on occupied ports rather than opening an unrelated application.
"$VENV_PYTHON" - "$PORT" <<'PY'
import socket
import sys
try:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", int(sys.argv[1])))
except OSError:
    sys.exit("Port is occupied. Choose another --port; no existing process was stopped.")
PY
URL="http://127.0.0.1:$PORT"
SERVER_PID=''
cleanup() {
    if [[ -n "$SERVER_PID" ]]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
"$VENV_PYTHON" -u main.py serve --port "$PORT" &
SERVER_PID=$!
"$VENV_PYTHON" - "$URL" "$SERVER_PID" <<'PY'
import os
import sys
import time
import urllib.request
for _ in range(60):
    try:
        os.kill(int(sys.argv[2]), 0)
        with urllib.request.urlopen(sys.argv[1] + "/", timeout=1) as response:
            if response.status == 200:
                break
    except OSError:
        time.sleep(0.5)
else:
    sys.exit("PRAG did not start. Check the server error above.")
PY
echo "PRAG web interface: $URL — Ctrl+C stops this server."
if ((UI_ONLY)); then echo 'UI-only mode: Ollama/model readiness has not been verified.'; fi
if ((OPEN_BROWSER)) && command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
fi
wait "$SERVER_PID"
