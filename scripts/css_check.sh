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

# For Tailwind v4, there's no standalone CLI. We'll use a basic syntax check instead.
# The real validation happens during Next.js build, which uses PostCSS.

# Check for common @apply mistakes by scanning the file
if grep -E '@apply\s+(ring-focus|shadow-soft|btn-base|text-foreground|bg-noise|shadow-elevated|layout-gridlines|container-safe)' "$CSS_INPUT" >/dev/null 2>&1; then
  echo ""
  echo "❌ CSS check failed. Found @apply with custom utility classes that don't exist:"
  echo ""
  grep -n -E '@apply.*(ring-focus|shadow-soft|btn-base|text-foreground|bg-noise|shadow-elevated|layout-gridlines|container-safe)' "$CSS_INPUT"
  echo ""
  echo "⚠️  Cannot use @apply with custom utilities. Only use @apply with native Tailwind classes."
  popd >/dev/null
  exit 1
fi

# Additional check: ensure no undefined CSS custom properties in @apply
if grep -E '@apply\s+[^;]*var\(' "$CSS_INPUT" >/dev/null 2>&1; then
  echo "⚠️  Warning: Found @apply with CSS variables. This may cause issues."
fi

echo "✅ CSS check passed (no obvious @apply errors detected)."
popd >/dev/null
exit 0


