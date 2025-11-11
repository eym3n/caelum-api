#!/usr/bin/env bash

set -euo pipefail

SESSION_NAME="${1:-}"

if [ -z "$SESSION_NAME" ]; then
  echo "❌ Session name is required"
  exit 1
fi

ENV="${ENV:-local}"
STORAGE_ROOT="${OUTPUT_PATH:-}"
if [ -z "$STORAGE_ROOT" ]; then
  if [[ "$ENV" == "local" || "$ENV" == "development" ]]; then STORAGE_ROOT="./storage"; else STORAGE_ROOT="/mnt/storage"; fi
fi
if [ ! -d "$STORAGE_ROOT" ] && [ -d "__out__" ]; then STORAGE_ROOT="__out__"; fi
mkdir -p "$STORAGE_ROOT"
TARGET_DIR="${STORAGE_ROOT}/${SESSION_NAME}"
TEMPLATE_DIR="template"
STAMP_FILE="${TARGET_DIR}/.template_applied"

if [ ! -d "$TARGET_DIR" ]; then
  echo "❌ Project '$SESSION_NAME' not initialized. Run init_app.sh first."
  exit 1
fi

if [ ! -d "$TEMPLATE_DIR" ]; then
  echo "❌ Template directory not found at '$TEMPLATE_DIR'"
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "⚠️  rsync not found; falling back to 'cp -R' (less efficient, no delete sync)."
  USE_RSYNC=0
else
  USE_RSYNC=1
fi

if [ ! -f "$STAMP_FILE" ]; then
  echo "🧱 Applying base template to '${SESSION_NAME}'..."
  if [ "$USE_RSYNC" -eq 1 ]; then
    rsync -a --delete "$TEMPLATE_DIR"/ "$TARGET_DIR"/
  else
    cp -R "$TEMPLATE_DIR"/. "$TARGET_DIR"/
    # Emulate delete semantics minimally: remove package-lock if present
  fi
  rm -f "${TARGET_DIR}/package-lock.json"
  touch "$STAMP_FILE"
else
  echo "ℹ️  Template already applied to '${SESSION_NAME}'."
fi

if [ -d "${TARGET_DIR}/node_modules" ]; then
  echo "✅ Dependencies already installed for '${SESSION_NAME}'."
  exit 0
fi

pushd "$TARGET_DIR" >/dev/null

echo "📦 Installing dependencies for '${SESSION_NAME}' (from package.json)..."
npm install --no-audit --no-fund

echo "🔁 Ensuring baseline utilities are available..."
npm install \
  @radix-ui/react-slot \
  clsx \
  react-hook-form \
  zod \
  tailwindcss-animate \
  tw-animate-css \
  @tailwindcss/typography \
  @tailwindcss/forms \
  class-variance-authority \
  framer-motion \
  lucide-react \
  pnpm \
  --no-audit --no-fund

popd >/dev/null

echo "✅ Base packages installed for '${SESSION_NAME}'."

