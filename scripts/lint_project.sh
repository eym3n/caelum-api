#!/usr/bin/env bash

PROJECT_NAME="$1"
cd __out__/"$PROJECT_NAME" || { echo "❌ Project '$PROJECT_NAME' not found!"; exit 1; }

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
echo "🧴 Checking Tailwind CSS (globals.css) with Tailwind CLI..."
if ! bash ../../scripts/css_check.sh "$PROJECT_NAME" 2>&1; then
    CSS_EXIT_CODE=$?
    echo ""
    echo "❌ CSS check failed for globals.css"
    exit $CSS_EXIT_CODE
fi

echo ""
echo "✅ All checks passed (ESLint, TypeScript, CSS)."
exit 0
