#!/usr/bin/env bash
# Helper to launch the FastAPI backend with proper environment variables.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-${REPO_ROOT}/.venv}"
APP_MODULE="${APP_MODULE:-apps.backend.app.main:app}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
DEVICE="${YOKAI_DEVICE:-auto}" # auto | cuda | mps | cpu

if [ ! -d "${VENV_DIR}" ]; then
  echo "[run_backend] Missing venv at ${VENV_DIR}. Run scripts/setup_sd_env.sh first." >&2
  exit 1
fi

source "${VENV_DIR}/bin/activate"
cd "${REPO_ROOT}"
export PYTHONPATH="${PYTHONPATH:-}:${REPO_ROOT}/yokai-gen"

export YOKAI_DEVICE="${DEVICE}"
export YOKAI_MODEL_DIR="${YOKAI_MODEL_DIR:-${REPO_ROOT}/yokai-gen/models/base}"
export YOKAI_LORA_DIR="${YOKAI_LORA_DIR:-${REPO_ROOT}/yokai-gen/models/lora}"

echo "[run_backend] Starting FastAPI on ${HOST}:${PORT}"
exec uvicorn "${APP_MODULE}" --host "${HOST}" --port "${PORT}" --reload

