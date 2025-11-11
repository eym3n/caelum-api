#!/usr/bin/env bash

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
if [ ! -d "$STORAGE_ROOT" ] && [ -d "__out__" ]; then STORAGE_ROOT="__out__"; fi
echo "[lint_project] Using STORAGE_ROOT='$STORAGE_ROOT' (ENV=$ENV OUTPUT_PATH='${OUTPUT_PATH:-}')"
TARGET_DIR="$STORAGE_ROOT/$PROJECT_NAME"
if [ ! -d "$TARGET_DIR" ]; then
    echo "❌ Project '$PROJECT_NAME' not found in $STORAGE_ROOT"
    exit 1
fi
cd "$TARGET_DIR"

echo "🔍 Running linter, TypeScript, and CSS checks for '$PROJECT_NAME'..."

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "⚠️  node_modules not found. Run install_dependencies first."
    exit 1
fi

# Run ESLint (capture output and exit code)
echo "📋 Running ESLint..."
if ! npm run lint 2>&1; then
    LINT_EXIT_CODE=$?
    echo ""
    echo "❌ ESLint found errors! You must fix these issues before proceeding."
    echo "Exit code: $LINT_EXIT_CODE"
    exit 1
fi

# Run TypeScript compiler check (tsc)
echo ""
echo "🧑‍💻 Running TypeScript (tsc) check..."
if ! npx tsc --noEmit 2>&1; then
    TSC_EXIT_CODE=$?
    echo ""
    echo "❌ TypeScript errors detected! You must fix these issues before proceeding."
    echo "Exit code: $TSC_EXIT_CODE"
    exit 1
fi

echo ""
echo "🧴 Checking Tailwind CSS (globals.css) syntax..."
if ! bash "$PWD/../../scripts/css_check.sh" "$PROJECT_NAME" 2>&1; then
    CSS_EXIT_CODE=$?
    echo ""
    echo "❌ CSS check failed for globals.css"
    exit $CSS_EXIT_CODE
fi

echo ""
echo "✅ All checks passed (ESLint, TypeScript, CSS)."
exit 0
