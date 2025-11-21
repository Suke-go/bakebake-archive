#!/usr/bin/env bash
# Bootstrap script for RunPod containers to train LoRA models with sd-scripts.
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/workspace}"
SD_SCRIPTS_REPO="${SD_SCRIPTS_REPO:-https://github.com/kohya-ss/sd-scripts.git}"
SD_SCRIPTS_DIR="${SD_SCRIPTS_DIR:-${PROJECT_ROOT}/sd-scripts}"

echo "[setup] Installing system dependencies..."
if command -v apt-get >/dev/null 2>&1; then
  DEBIAN_FRONTEND=noninteractive sudo apt-get update -y
  DEBIAN_FRONTEND=noninteractive sudo apt-get install -y git git-lfs aria2 libgl1 libglib2.0-0
else
  echo "[setup] Skipping apt install (not available). Ensure git and libgl are present."
fi

git lfs install || true

if [ ! -d "${SD_SCRIPTS_DIR}" ]; then
  echo "[setup] Cloning sd-scripts into ${SD_SCRIPTS_DIR}"
  git clone "${SD_SCRIPTS_REPO}" "${SD_SCRIPTS_DIR}"
else
  echo "[setup] sd-scripts already present, pulling latest changes."
  (cd "${SD_SCRIPTS_DIR}" && git pull)
fi

cd "${SD_SCRIPTS_DIR}"

python3 -m pip install --upgrade pip wheel setuptools
python3 -m pip install -r requirements.txt
python3 -m pip install --upgrade xformers==0.0.25 bitsandbytes==0.43.1

echo "[setup] Done. Ready to run training via train.sh."

