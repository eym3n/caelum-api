#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$ROOT_DIR/.devserver"
mkdir -p "$STATE_DIR"

SESSION_ID="${1:-}"
if [ -z "$SESSION_ID" ]; then
  echo "❌ Session id is required" >&2
  exit 1
fi

APP_DIR="$ROOT_DIR/__out__/$SESSION_ID"
if [ ! -d "$APP_DIR" ]; then
  echo "❌ App directory '$APP_DIR' not found. Run init_app.sh first." >&2
  exit 1
fi

PID_FILE="$STATE_DIR/current_pid"
SESSION_FILE="$STATE_DIR/current_session"
LOG_FILE="$STATE_DIR/${SESSION_ID}_dev.log"

clean_stale() {
  if [ -f "$PID_FILE" ]; then
    local existing_pid
    existing_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$existing_pid" ]; then
      if ! ps -p "$existing_pid" >/dev/null 2>&1; then
        rm -f "$PID_FILE" "$SESSION_FILE"
      fi
    fi
  fi
}

stop_existing() {
  if [ -f "$PID_FILE" ]; then
    local existing_pid
    existing_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    local existing_session="$(cat "$SESSION_FILE" 2>/dev/null || true)"

    if [ -n "$existing_pid" ] && ps -p "$existing_pid" >/dev/null 2>&1; then
      if [ "$existing_session" != "$SESSION_ID" ]; then
        echo "🛑 Stopping dev server for session '$existing_session' (pid $existing_pid)"
        kill "$existing_pid" >/dev/null 2>&1 || true
        # Wait up to 5 seconds
        for _ in 1 2 3 4 5; do
          if ! ps -p "$existing_pid" >/dev/null 2>&1; then
            break
          fi
          sleep 1
        done
        if ps -p "$existing_pid" >/dev/null 2>&1; then
          echo "⚠️  Force killing lingering dev server (pid $existing_pid)"
          kill -9 "$existing_pid" >/dev/null 2>&1 || true
        fi
        rm -f "$PID_FILE" "$SESSION_FILE"
      fi
    else
      rm -f "$PID_FILE" "$SESSION_FILE"
    fi
  fi
}

clean_stale
stop_existing

if [ -f "$PID_FILE" ]; then
  current_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  current_session="$(cat "$SESSION_FILE" 2>/dev/null || true)"
  if [ -n "$current_pid" ] && [ "$current_session" = "$SESSION_ID" ] && ps -p "$current_pid" >/dev/null 2>&1; then
    echo "✅ npm run dev already running for session '$SESSION_ID' (pid $current_pid)"
    exit 0
  else
    rm -f "$PID_FILE" "$SESSION_FILE"
  fi
fi

pushd "$APP_DIR" >/dev/null

echo "🚀 Starting npm run dev for session '$SESSION_ID'..."
# Run in background and redirect output
nohup npm run dev -- --hostname 0.0.0.0 --port 3000 >"$LOG_FILE" 2>&1 &
DEV_PID=$!

popd >/dev/null

# Give the process a moment to initialize
sleep 1

if ! ps -p "$DEV_PID" >/dev/null 2>&1; then
  echo "❌ Failed to start npm run dev for session '$SESSION_ID'. See $LOG_FILE" >&2
  exit 1
fi

echo "$DEV_PID" >"$PID_FILE"
echo "$SESSION_ID" >"$SESSION_FILE"

echo "✅ npm run dev started for session '$SESSION_ID' (pid $DEV_PID). Logs: $LOG_FILE"
