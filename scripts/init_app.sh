#!/usr/bin/env bash

set -euo pipefail

SESSION_NAME="${1:-}"
if [ -z "$SESSION_NAME" ]; then echo "Usage: $0 <session-name>"; exit 1; fi
ENV="${ENV:-local}"
STORAGE_ROOT="${OUTPUT_PATH:-}"

echo "[init_app] === Starting init_app.sh at $(date -u '+%Y-%m-%dT%H:%M:%SZ') ==="
echo "[init_app] Incoming SESSION_NAME='$SESSION_NAME' ENV='$ENV' OUTPUT_PATH='${OUTPUT_PATH:-}'"

if [ -z "$STORAGE_ROOT" ]; then
  if [[ "$ENV" == "local" || "$ENV" == "testing" ]]; then
    STORAGE_ROOT="./storage"
  else
    STORAGE_ROOT="/mnt/storage"
  fi
fi
if [ ! -d "$STORAGE_ROOT" ] && [ -d "__out__" ]; then
  echo "[init_app] STORAGE_ROOT '$STORAGE_ROOT' does not exist, falling back to '__out__'"
  STORAGE_ROOT="__out__"
fi
echo "[init_app] Using STORAGE_ROOT='$STORAGE_ROOT'"

mkdir -p "$STORAGE_ROOT" || { echo "[init_app] ERROR: Cannot create STORAGE_ROOT '$STORAGE_ROOT'"; exit 1; }

TARGET_DIR="${STORAGE_ROOT}/${SESSION_NAME}"
echo "[init_app] TARGET_DIR='$TARGET_DIR'"

# Diagnostics: Node & npm versions, free space, permissions
if command -v node >/dev/null 2>&1; then echo "[init_app] node version: $(node -v)"; else echo "[init_app] WARNING: node not found in PATH"; fi
if command -v npm >/dev/null 2>&1; then echo "[init_app] npm version: $(npm -v)"; else echo "[init_app] WARNING: npm not found in PATH"; fi
if command -v npx >/dev/null 2>&1; then echo "[init_app] npx version: $(npx --version 2>/dev/null || echo 'unknown')"; fi
echo "[init_app] PATH=$PATH"
df -h "$STORAGE_ROOT" 2>/dev/null | sed 's/^/[init_app] df: /' || echo "[init_app] WARNING: df check failed"
echo "[init_app] Directory permissions: $(stat -f '%Sp %Su:%Sg' "$STORAGE_ROOT" 2>/dev/null || echo 'unavailable')"

if [ -d "${TARGET_DIR}" ] && [ -f "${TARGET_DIR}/package.json" ]; then
  echo "[init_app] ✅ Next.js app already exists at ${TARGET_DIR}. Skipping initialization."
  exit 0
fi

if [ -d "${TARGET_DIR}" ] && [ "$(ls -A "${TARGET_DIR}" 2>/dev/null)" ]; then
  echo "[init_app] ⚠️  Target directory ${TARGET_DIR} exists and is not empty. Skipping initialization to avoid overwriting existing files."
  exit 0
fi

echo "[init_app] Running create-next-app..."
START_TS=$(date +%s)
if ! command -v npx >/dev/null 2>&1; then
  echo "[init_app] WARNING: npx missing. Falling back to template copy." 
  if [ -d "template" ]; then
    echo "[init_app] Copying base template to ${TARGET_DIR}" 
    mkdir -p "${TARGET_DIR}" 
    rsync -a --delete template/ "${TARGET_DIR}/" || { echo "[init_app] ERROR: rsync template copy failed"; exit 1; }
    if [ -f "${TARGET_DIR}/package.json" ]; then
      echo "[init_app] ✅ Template fallback succeeded." 
    else
      echo "[init_app] ❌ Template fallback incomplete (package.json missing)."; exit 1
    fi
  else
    echo "[init_app] ❌ Neither npx nor template directory available. Cannot initialize app."; exit 1
  fi
else
  npx create-next-app@latest "${TARGET_DIR}" \
    --typescript \
    --tailwind \
    --eslint \
    --app \
    --src-dir \
    --import-alias "@/*" \
    --use-npm \
    --yes \
    --no-turbo \
    --no-compiler || { echo "[init_app] ERROR: create-next-app failed"; exit 1; }
fi
END_TS=$(date +%s)
echo "[init_app] create-next-app completed in $((END_TS-START_TS))s"

if [ -f "${TARGET_DIR}/package.json" ]; then
  echo "[init_app] ✅ Initialization succeeded (package.json present)."
else
  echo "[init_app] ❌ Initialization incomplete: package.json missing in ${TARGET_DIR}"; exit 1
fi

echo "[init_app] === Finished at $(date -u '+%Y-%m-%dT%H:%M:%SZ') ==="

