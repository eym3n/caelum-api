#!/usr/bin/env bash

set -euo pipefail

PROJECT_NAME="$1"

APP_DIR="__out__/${PROJECT_NAME}"
if [ ! -d "$APP_DIR" ]; then
  echo "❌ Project '$PROJECT_NAME' not found!"
  exit 1
fi

pushd "$APP_DIR" >/dev/null

if [ ! -d "node_modules" ]; then
  echo "⚠️  node_modules not found. Run install_dependencies first."
  popd >/dev/null
  exit 1
fi

CSS_INPUT="src/app/globals.css"
if [ ! -f "$CSS_INPUT" ]; then
  echo "ℹ️  globals.css not found at $CSS_INPUT — skipping CSS check."
  popd >/dev/null
  exit 0
fi

echo "🧪 Checking Tailwind CSS in $CSS_INPUT for @apply errors and invalid utilities..."

# Use tailwindcss CLI to process globals.css only; write to a temp file and discard
TMP_OUT=".tw-check.css"
if npx tailwindcss -i "$CSS_INPUT" -o "$TMP_OUT" --minify >/dev/null 2>&1; then
  rm -f "$TMP_OUT"
  echo "✅ CSS check passed (no Tailwind @apply errors detected)."
  popd >/dev/null
  exit 0
else
  STATUS=$?
  echo ""
  echo "❌ CSS check failed. Tailwind reported errors while processing globals.css."
  echo "(If you see 'Cannot apply unknown utility class', replace custom tokens with native utilities or direct CSS properties.)"
  # Re-run to print the actual error output
  npx tailwindcss -i "$CSS_INPUT" -o "$TMP_OUT" --minify
  rm -f "$TMP_OUT" || true
  popd >/dev/null
  exit $STATUS
fi


