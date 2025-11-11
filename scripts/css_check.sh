#!/usr/bin/env bash

set -euo pipefail

PROJECT_NAME="${1:-}"
if [ -z "$PROJECT_NAME" ]; then echo "Usage: $0 <project-name>"; exit 1; fi
ENV="${ENV:-local}"
STORAGE_ROOT="${OUTPUT_PATH:-}"
if [ -z "$STORAGE_ROOT" ]; then
  if [[ "$ENV" == "local" || "$ENV" == "development" || "$ENV" == "testing" ]]; then
    STORAGE_ROOT="./storage"
  else
    STORAGE_ROOT="/mnt/storage"
  fi
fi
# If running in container (has /mnt/storage) but chosen root is ./storage and project absent, prefer /mnt/storage
if [ -d "/mnt/storage" ] && [[ "$STORAGE_ROOT" == "./storage" || "$STORAGE_ROOT" == "__out__" ]]; then
  ALT_DIR="/mnt/storage/${PROJECT_NAME}"
fi
if [ ! -d "$STORAGE_ROOT" ] && [ -d "__out__" ]; then STORAGE_ROOT="__out__"; fi
APP_DIR="${STORAGE_ROOT}/${PROJECT_NAME}"
if [ ! -d "$APP_DIR" ] && [ -n "${ALT_DIR:-}" ] && [ -d "$ALT_DIR" ]; then
  echo "[css_check] Fallback: switching STORAGE_ROOT to /mnt/storage"
  STORAGE_ROOT="/mnt/storage"
  APP_DIR="$ALT_DIR"
fi
echo "[css_check] Using STORAGE_ROOT='$STORAGE_ROOT' (ENV=$ENV OUTPUT_PATH='${OUTPUT_PATH:-}')"
if [ ! -d "$APP_DIR" ]; then
  echo "❌ Project '$PROJECT_NAME' not found in '$STORAGE_ROOT' (checked ALT='${ALT_DIR:-none}')"
  exit 1
fi

pushd "$APP_DIR" >/dev/null

if [ ! -d "node_modules" ]; then
  echo "⚠️  node_modules not found. Run install_dependencies first."
  popd >/dev/null
  exit 1
fi

CSS_CANDIDATES=(
  "src/app/globals.css"
  "app/globals.css"
  "src/styles/globals.css"
  "styles/globals.css"
)
CSS_INPUT=""
for f in "${CSS_CANDIDATES[@]}"; do
  if [ -f "$f" ]; then CSS_INPUT="$f"; break; fi
done
if [ -z "$CSS_INPUT" ]; then
  echo "❌ ERROR: globals.css not found in any candidate path (${CSS_CANDIDATES[*]})"
  popd >/dev/null
  exit 1
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


