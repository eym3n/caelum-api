#!/usr/bin/env bash

set -euo pipefail

SESSION_ID="${1:-}"
if [ -z "$SESSION_ID" ]; then
  echo "Usage: $0 <session-id>" >&2
  exit 1
fi

ENV="${ENV:-local}"
OUTPUT_PATH="${OUTPUT_PATH:-}"
if [ -n "$OUTPUT_PATH" ]; then
  STORAGE_ROOT="$OUTPUT_PATH"
else
  # Cloud (development or production) always uses /mnt/storage; only local uses ./storage
  if [ "$ENV" = "local" ]; then
    STORAGE_ROOT="./storage"
  else
    STORAGE_ROOT="/mnt/storage"
  fi
fi
if [ ! -d "$STORAGE_ROOT" ] && [ -d "__out__" ]; then STORAGE_ROOT="__out__"; fi

TEMPLATE_DIR="template"
TARGET_DIR="${STORAGE_ROOT}/${SESSION_ID}"
STAMP_FILE="${TARGET_DIR}/.static_template_copied"

echo "[copy_template] SESSION_ID='$SESSION_ID' ENV='$ENV' STORAGE_ROOT='$STORAGE_ROOT' TEMPLATE_DIR='$TEMPLATE_DIR'"

if [ ! -d "$TEMPLATE_DIR" ]; then
  echo "[copy_template] ❌ Template directory '$TEMPLATE_DIR' not found" >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"

if [ -f "$STAMP_FILE" ]; then
  echo "[copy_template] ✅ Template already copied for session '$SESSION_ID' (stamp present)."
  exit 0
fi

echo "[copy_template] Copying template → '$TARGET_DIR'"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete "$TEMPLATE_DIR"/ "$TARGET_DIR"/
else
  cp -R "$TEMPLATE_DIR"/. "$TARGET_DIR"/
fi

touch "$STAMP_FILE"
echo "[copy_template] ✅ Copy complete. Marker file created: $STAMP_FILE"