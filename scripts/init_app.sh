#!/usr/bin/env bash

set -euo pipefail

SESSION_NAME="${1:-}"
if [ -z "$SESSION_NAME" ]; then echo "Usage: $0 <session-name>"; exit 1; fi
ENV="${ENV:-local}"
STORAGE_ROOT="${OUTPUT_PATH:-}"
if [ -z "$STORAGE_ROOT" ]; then
  if [[ "$ENV" == "local" || "$ENV" == "development" ]]; then
    STORAGE_ROOT="./storage"
  else
    STORAGE_ROOT="/mnt/storage"
  fi
fi
if [ ! -d "$STORAGE_ROOT" ] && [ -d "__out__" ]; then STORAGE_ROOT="__out__"; fi
mkdir -p "$STORAGE_ROOT"
TARGET_DIR="${STORAGE_ROOT}/${SESSION_NAME}"

if [ -d "${TARGET_DIR}" ] && [ -f "${TARGET_DIR}/package.json" ]; then
  echo "✅ Next.js app already exists at ${TARGET_DIR}. Skipping initialization."
  exit 0
fi

if [ -d "${TARGET_DIR}" ] && [ "$(ls -A "${TARGET_DIR}")" ]; then
  echo "⚠️  Target directory ${TARGET_DIR} exists and is not empty. Skipping initialization to avoid overwriting existing files."
  exit 0
fi

npx create-next-app@latest "${TARGET_DIR}" \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --use-npm \
  --yes \
  --no-turbo \
  --no-compiler

