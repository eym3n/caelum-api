#!/usr/bin/env bash

PROJECT_NAME="$1"
cd __out__/"$PROJECT_NAME" || { echo "❌ Project '$PROJECT_NAME' not found!"; exit 1; }

echo "🔍 Running linter and syntax checks for '$PROJECT_NAME'..."

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "⚠️  node_modules not found. Run install_dependencies first."
    exit 1
fi

# Run ESLint (capture output and exit code)
echo "📋 Running ESLint..."
if npm run lint 2>&1; then
    echo ""
    echo "✅ Linting completed successfully! No issues found."
    exit 0
else
    LINT_EXIT_CODE=$?
    echo ""
    echo "❌ ESLint found errors! You must fix these issues before proceeding."
    echo "Exit code: $LINT_EXIT_CODE"
    exit 1
fi

