#!/usr/bin/env bash
# Exit if any command fails
set -euo pipefail

PROJECT_NAME="${1:-}"
if [ -z "$PROJECT_NAME" ]; then
	echo "Usage: $0 <project-name>" >&2; exit 1; fi

# Determine storage root (ENV & OUTPUT_PATH aware)
ENV="${ENV:-local}"
STORAGE_ROOT="${OUTPUT_PATH:-}"
if [ -z "$STORAGE_ROOT" ]; then
	if [[ "$ENV" == "local"  ]]; then
		STORAGE_ROOT="./storage"
	else
		STORAGE_ROOT="/mnt/storage"
	fi
fi
# Backward compatibility fallback
if [ ! -d "$STORAGE_ROOT" ] && [ -d "__out__" ]; then
	STORAGE_ROOT="__out__"
fi
mkdir -p "$STORAGE_ROOT"

cd "$STORAGE_ROOT/$PROJECT_NAME" || { echo "❌ Project '$PROJECT_NAME' not found in $STORAGE_ROOT"; exit 1; }

echo "🚀 Starting Next.js dev server for '$PROJECT_NAME' (ENV=$ENV, STORAGE_ROOT=$STORAGE_ROOT)..."
npm run dev