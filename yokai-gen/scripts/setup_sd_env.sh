#!/usr/bin/env bash
# Bootstrap a local Stable Diffusion Diffusers environment for yokai generation.
# - Creates/updates a Python virtual environment
# - Installs backend requirements
# - Optionally downloads a base SD model (requires huggingface-cli + token)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-${REPO_ROOT}/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-${REPO_ROOT}/yokai-gen/apps/backend/requirements.txt}"
MODEL_ID="${MODEL_ID:-stabilityai/stable-diffusion-xl-base-1.0}"
MODEL_DIR="${MODEL_DIR:-${REPO_ROOT}/yokai-gen/models/base}"
HF_CACHE_DIR="${HF_CACHE_DIR:-${REPO_ROOT}/.cache/huggingface}"

echo "[setup] Repo root: ${REPO_ROOT}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "[setup] ${PYTHON_BIN} not found. Please install Python 3.10+ first." >&2
  exit 1
fi

if [ ! -d "${VENV_DIR}" ]; then
  echo "[setup] Creating virtual environment at ${VENV_DIR}"
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
else
  echo "[setup] Reusing existing virtual environment at ${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip wheel setuptools

if [ ! -f "${REQUIREMENTS_FILE}" ]; then
  echo "[setup] Requirements file ${REQUIREMENTS_FILE} is missing. Add backend deps first." >&2
  exit 1
fi

echo "[setup] Installing Python dependencies..."
python -m pip install -r "${REQUIREMENTS_FILE}"

mkdir -p "${MODEL_DIR}"

if command -v huggingface-cli >/dev/null 2>&1; then
  echo "[setup] Downloading base model ${MODEL_ID}"
  HF_HOME="${HF_CACHE_DIR}" huggingface-cli download "${MODEL_ID}" --exclude "*.bin" --local-dir "${MODEL_DIR}" --resume-download
else
  cat <<EOF
[setup] huggingface-cli not found.
Install it via 'pip install huggingface-hub' and ensure HF_TOKEN is set, then rerun:
    HF_TOKEN=xxxxx huggingface-cli login
    ${BASH_SOURCE[0]}
EOF
fi

echo "[setup] Done. Activate the venv with:"
echo "    source ${VENV_DIR}/bin/activate"

