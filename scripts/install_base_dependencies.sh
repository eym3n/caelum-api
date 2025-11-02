#!/usr/bin/env bash

set -euo pipefail

SESSION_NAME="${1:-}"

if [ -z "$SESSION_NAME" ]; then
  echo "❌ Session name is required"
  exit 1
fi

TARGET_DIR="__out__/${SESSION_NAME}"
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
  echo "❌ rsync command not found. Please install rsync."
  exit 1
fi

if [ ! -f "$STAMP_FILE" ]; then
  echo "🧱 Applying base template to '${SESSION_NAME}'..."
  rsync -a --delete "$TEMPLATE_DIR"/ "$TARGET_DIR"/
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
  --no-audit --no-fund

popd >/dev/null

echo "✅ Base packages installed for '${SESSION_NAME}'."

