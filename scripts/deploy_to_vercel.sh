#!/usr/bin/env bash

set -euo pipefail

SESSION_NAME="${1:-}"

if [ -z "$SESSION_NAME" ]; then
  echo "❌ Usage: $0 <session_name>"
  exit 1
fi

TARGET_DIR="__out__/${SESSION_NAME}"

if [ ! -d "$TARGET_DIR" ]; then
  echo "❌ Project directory not found: $TARGET_DIR"
  exit 1
fi

if [ ! -f "${TARGET_DIR}/package.json" ]; then
  echo "❌ package.json not found in $TARGET_DIR"
  exit 1
fi

# Check if pnpm is installed, install if not found
if ! command -v pnpm >/dev/null 2>&1; then
  echo "📦 pnpm not found. Installing pnpm globally..."
  npm install -g pnpm
  echo "✅ pnpm installed successfully."
fi

# Check if vercel CLI is installed
if ! command -v vercel >/dev/null 2>&1; then
  echo "❌ Vercel CLI not found. Install it with: npm install -g vercel"
  exit 1
fi

echo "🚀 Deploying '${SESSION_NAME}' to Vercel..."

pushd "$TARGET_DIR" >/dev/null

# Check if already linked to Vercel
if [ -d ".vercel" ]; then
  echo "📦 Project already linked to Vercel. Deploying updates..."
  vercel --prod --yes
else
  echo "🔗 Setting up new Vercel project for '${SESSION_NAME}'..."
  # Deploy with automatic setup
  # - Answers yes to initial setup
  # - Uses session name as project name
  # - Auto-detects Next.js settings
  # - Deploys to production
  vercel --prod --yes --name="${SESSION_NAME}"
fi

popd >/dev/null

echo "✅ Deployment complete for '${SESSION_NAME}'!"
echo "📝 View your deployment at: https://vercel.com"
