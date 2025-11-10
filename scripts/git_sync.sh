#!/usr/bin/env bash

set -euo pipefail

PROJECT_NAME="${1:-}"
if [ -z "$PROJECT_NAME" ]; then echo "Usage: $0 <project-name>"; exit 1; fi
ENV="${ENV:-local}"
STORAGE_ROOT="${OUTPUT_PATH:-}"
if [ -z "$STORAGE_ROOT" ]; then
  if [[ "$ENV" == "local" || "$ENV" == "development" ]]; then STORAGE_ROOT="./storage"; else STORAGE_ROOT="/mnt/storage"; fi
fi
if [ ! -d "$STORAGE_ROOT" ] && [ -d "__out__" ]; then STORAGE_ROOT="__out__"; fi
APP_DIR="${STORAGE_ROOT}/${PROJECT_NAME}"
if [ ! -d "$APP_DIR" ]; then
  echo "❌ Project '$PROJECT_NAME' not found!"
  exit 1
fi

pushd "$APP_DIR" >/dev/null

# Initialize repo if missing
if [ ! -d ".git" ]; then
  echo "🆕 Initializing git repository"
  git init
fi

# Ensure identity (local-only)
git config user.name >/dev/null 2>&1 || git config user.name "Auto Commit Bot"
git config user.email >/dev/null 2>&1 || git config user.email "bot@example.com"

# Stage all changes
git add -A

# Check if there is anything to commit
if git diff --cached --quiet; then
  echo "ℹ️  No changes to commit."
  popd >/dev/null
  exit 0
fi

COMMIT_MSG="chore(git): sync workspace changes"
git commit -m "$COMMIT_MSG"

echo "✅ Committed changes:"
git log -1 --pretty=format:"%h %ad %an %s" --date=short

popd >/dev/null
exit 0


