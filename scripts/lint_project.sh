#!/usr/bin/env bash

PROJECT_NAME="${1:-}"
if [ -z "$PROJECT_NAME" ]; then echo "Usage: $0 <project-name>"; exit 1; fi
ENV="${ENV:-local}"
STORAGE_ROOT="${OUTPUT_PATH:-}"
if [ -z "$STORAGE_ROOT" ]; then
    if [[ "$ENV" == "local" || "$ENV" == "testing" ]]; then
        STORAGE_ROOT="./storage"
    else
        STORAGE_ROOT="/mnt/storage"
    fi
fi
if [ ! -d "$STORAGE_ROOT" ] && [ -d "__out__" ]; then STORAGE_ROOT="__out__"; fi
TARGET_DIR="$STORAGE_ROOT/$PROJECT_NAME"
ALT_DIR="/mnt/storage/$PROJECT_NAME"
if [ ! -d "$TARGET_DIR" ] && [ -d "/mnt/storage" ] && [ -d "$ALT_DIR" ]; then
    echo "[lint_project] Fallback: switching STORAGE_ROOT to /mnt/storage"
    STORAGE_ROOT="/mnt/storage"
    TARGET_DIR="$ALT_DIR"
fi
echo "[lint_project] Using STORAGE_ROOT='$STORAGE_ROOT' (ENV=$ENV OUTPUT_PATH='${OUTPUT_PATH:-}')"
if [ ! -d "$TARGET_DIR" ]; then
    echo "❌ Project '$PROJECT_NAME' not found (checked '$STORAGE_ROOT' ALT='/mnt/storage')"
    exit 1
fi
cd "$TARGET_DIR"

echo "🔍 Running oxlint and CSS checks for '$PROJECT_NAME'..."

if ! command -v npx >/dev/null 2>&1; then
    echo "❌ npx not found (Node toolchain missing)."; exit 1; fi

echo "📋 Running oxlint..."
OX_OUTPUT=$(npx oxlint --type-aware --threads 12 . 2>&1)
    OX_EXIT=$?
echo "$OX_OUTPUT"

# Check for warnings or errors in output
HAS_WARNINGS=false
WARNINGS=0

# Check for summary line like "Found X warnings and Y errors"
if echo "$OX_OUTPUT" | grep -qE "Found [0-9]+ warnings?"; then
    WARNINGS=$(echo "$OX_OUTPUT" | grep -oE "Found [0-9]+ warnings?" | grep -oE "[0-9]+" | head -1)
    if [ -n "$WARNINGS" ] && [ "$WARNINGS" -gt 0 ]; then
        HAS_WARNINGS=true
    fi
fi

# Also check for warning markers (!) in output as fallback
# oxlint outputs warnings with "!" prefix (may be indented or prefixed)
if echo "$OX_OUTPUT" | grep -qE "[[:space:]]*!"; then
    HAS_WARNINGS=true
    if [ "$WARNINGS" -eq 0 ]; then
        WARNINGS=$(echo "$OX_OUTPUT" | grep -cE "[[:space:]]*!" || echo "0")
    fi
fi

if [ "$HAS_WARNINGS" = true ]; then
    echo ""
    echo "❌ oxlint reported $WARNINGS warning(s). Fix them before proceeding."
    exit 1
fi

# Also check exit code
if [ $OX_EXIT -ne 0 ]; then
    echo ""
    echo "❌ oxlint reported issues (exit $OX_EXIT). Fix them before proceeding."
    exit $OX_EXIT
fi


echo ""
echo "✅ All checks passed"
exit 0
