#!/usr/bin/env bash
# Launch backend and frontend together with auto-install steps.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cleanup() {
  if [ -n "${BACKEND_PID:-}" ]; then
    kill "${BACKEND_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

${REPO_ROOT}/yokai-gen/scripts/run_backend.sh &
BACKEND_PID=$!

cd "${REPO_ROOT}/yokai-gen/apps/frontend"
if [ ! -d node_modules ]; then
  npm install
fi
npm run dev

