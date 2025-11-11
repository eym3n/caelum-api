#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="${1:-}"
if [ -z "$PROJECT_NAME" ]; then echo "Usage: $0 <project-name>"; exit 1; fi
ENV="${ENV:-local}"
STORAGE_ROOT="${OUTPUT_PATH:-}"
if [ -z "$STORAGE_ROOT" ]; then
	if [[ "$ENV" == "local"  ]]; then STORAGE_ROOT="./storage"; else STORAGE_ROOT="/mnt/storage"; fi
fi
if [ ! -d "$STORAGE_ROOT" ] && [ -d "__out__" ]; then STORAGE_ROOT="__out__"; fi
cd "$STORAGE_ROOT/$PROJECT_NAME" || { echo "❌ Project '$PROJECT_NAME' not found in $STORAGE_ROOT"; exit 1; }
echo "🚀 Installing dependencies for '$PROJECT_NAME' (ENV=$ENV, STORAGE_ROOT=$STORAGE_ROOT)..."
npm install