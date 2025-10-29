#!/usr/bin/env bash
# Exit if any command fails
set -e

PROJECT_NAME="$1"
cd __out__/"$PROJECT_NAME" || { echo "❌ Project '$PROJECT_NAME' not found!"; exit 1; }

echo "🚀 Installing dependencies for '$PROJECT_NAME'..."
npm install