#!/usr/bin/env bash

set -euo pipefail

PROJECT_NAME="$1"
shift

if [ "$#" -eq 0 ]; then
  echo "Usage: run_npx_command.sh <project-name> <npx-command...>"
  exit 1
fi

APP_DIR="__out__/${PROJECT_NAME}"
if [ ! -d "$APP_DIR" ]; then
  echo "❌ Project '$PROJECT_NAME' not found!"
  exit 1
fi

pushd "$APP_DIR" >/dev/null

echo "🚀 Running: npx $*"

# Some interactive shadcn/aceternity commands prompt for confirmation/color.
# Feed default answers automatically so agents aren't blocked.
if [[ "${1:-}" == "shadcn@latest" && "${2:-}" == "add" ]]; then
  # If not initialized, run non-interactive init with defaults first
  if [ ! -f "components.json" ]; then
    echo "ℹ Running 'shadcn init --yes --defaults' (no prompts)"
    npx shadcn@latest init --yes --defaults || true
  fi
  # Then run add non-interactively
  shift 2
  echo "ℹ Adding component(s): $*"
  npx shadcn@latest add "$@" --yes
else
  # shellcheck disable=SC2068
  npx $@
fi
STATUS=$?

popd >/dev/null
exit $STATUS
