#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-${REPO_ROOT}/.venv}"

if [ ! -d "${VENV_DIR}" ]; then
  echo "[test_backend] Missing venv. Run scripts/setup_sd_env.sh first." >&2
  exit 1
fi

source "${VENV_DIR}/bin/activate"
cd "${REPO_ROOT}"
export PYTHONPATH="${PYTHONPATH:-}:${REPO_ROOT}/yokai-gen"

pytest yokai-gen/apps/backend/tests

