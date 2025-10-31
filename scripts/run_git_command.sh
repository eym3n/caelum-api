#!/usr/bin/env bash

set -euo pipefail

PROJECT_NAME="$1"
shift

if [ "$#" -eq 0 ]; then
  echo "Usage: run_git_command.sh <project-name> <git-args...>"
  exit 1
fi

APP_DIR="__out__/${PROJECT_NAME}"
if [ ! -d "$APP_DIR" ]; then
  echo "❌ Project '$PROJECT_NAME' not found!"
  exit 1
fi

pushd "$APP_DIR" >/dev/null

echo "🧩 Running: git $*"

# shellcheck disable=SC2068
git $@
STATUS=$?

popd >/dev/null
exit $STATUS


