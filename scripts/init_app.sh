#!/usr/bin/env bash

set -euo pipefail

SESSION_NAME="$1"
TARGET_DIR="__out__/${SESSION_NAME}"

mkdir -p "__out__"

if [ -d "${TARGET_DIR}" ] && [ -f "${TARGET_DIR}/package.json" ]; then
  echo "✅ Next.js app already exists at ${TARGET_DIR}. Skipping initialization."
  exit 0
fi

if [ -d "${TARGET_DIR}" ] && [ "$(ls -A "${TARGET_DIR}")" ]; then
  echo "⚠️  Target directory ${TARGET_DIR} exists and is not empty. Skipping initialization to avoid overwriting existing files."
  exit 0
fi

yes "" | npx create-next-app@latest "${TARGET_DIR}" \
  --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm
