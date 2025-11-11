#!/usr/bin/env bash
set -euo pipefail

# Environment variables (with defaults)
: "${HOST:=0.0.0.0}"
: "${PORT:=8080}"
: "${APP_MODULE:=app.main:app}"
: "${WORKERS:=4}"
: "${APP_ENV:=production}"
# Uvicorn expects lowercase log levels among: critical,error,warning,info,debug,trace
: "${LOG_LEVEL:=info}"

LOWER_LOG_LEVEL=$(echo "${LOG_LEVEL}" | tr '[:upper:]' '[:lower:]')
case "${LOWER_LOG_LEVEL}" in
  critical|error|warning|info|debug|trace) ;;
  *) echo "[entrypoint] Invalid LOG_LEVEL='${LOG_LEVEL}', falling back to 'info'"; LOWER_LOG_LEVEL=info ;;
esac

if [ "${APP_ENV}" = "local" ] ]; then
  echo "[entrypoint] Starting development server (reload) for ${APP_MODULE} on ${HOST}:${PORT}"
  exec python -m uvicorn "${APP_MODULE}" --host "${HOST}" --port "${PORT}" --reload --reload-dir app --log-level "${LOWER_LOG_LEVEL}"  
else
  echo "[entrypoint] Starting production server with ${WORKERS} workers for ${APP_MODULE} on ${HOST}:${PORT} (log-level=${LOG_LEVEL})"
  exec python -m uvicorn "${APP_MODULE}" --host "${HOST}" --port "${PORT}" --workers "${WORKERS}" --log-level "${LOWER_LOG_LEVEL}"  
fi
