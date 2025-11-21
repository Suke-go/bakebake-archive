#!/usr/bin/env bash
# Bootstrap script for RunPod containers to train LoRA models with sd-scripts.
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/workspace}"
SD_SCRIPTS_REPO="${SD_SCRIPTS_REPO:-https://github.com/kohya-ss/sd-scripts.git}"
SD_SCRIPTS_DIR="${SD_SCRIPTS_DIR:-${PROJECT_ROOT}/sd-scripts}"

# Dependency pins tuned for H100 (sm90) and CUDA 12.1 base images.
TORCH_VERSION="${TORCH_VERSION:-2.3.1}"
TORCH_CUDA="${TORCH_CUDA:-cu121}"
# torchvision は torch2.3系に対して 0.18.x が対応表
TORCHVISION_VERSION="${TORCHVISION_VERSION:-0.18.1}"
TORCHAUDIO_VERSION="${TORCHAUDIO_VERSION:-${TORCH_VERSION}}"
XFORMERS_VERSION="${XFORMERS_VERSION:-0.0.27}"
BITSANDBYTES_VERSION="${BITSANDBYTES_VERSION:-0.43.1}"
INSTALL_BITSANDBYTES="${INSTALL_BITSANDBYTES:-1}"

ACCELERATE_CACHE_DIR="${ACCELERATE_CACHE_DIR:-/workspace/.cache/huggingface/accelerate}"
ACCELERATE_CONFIG_FILE="${ACCELERATE_CONFIG_FILE:-${ACCELERATE_CACHE_DIR}/default_config.yaml}"

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

echo "[setup] Installing Python deps (torch ${TORCH_VERSION} ${TORCH_CUDA}, xformers ${XFORMERS_VERSION})..."
python3 -m pip install --upgrade pip wheel setuptools
python3 -m pip install --extra-index-url "https://download.pytorch.org/whl/${TORCH_CUDA}" \
  torch=="${TORCH_VERSION}" torchvision=="${TORCHVISION_VERSION}" torchaudio=="${TORCHAUDIO_VERSION}"
python3 -m pip install -r requirements.txt
python3 -m pip install xformers=="${XFORMERS_VERSION}"

if [ "${INSTALL_BITSANDBYTES}" = "1" ]; then
  echo "[setup] Installing bitsandbytes ${BITSANDBYTES_VERSION} (optional, set INSTALL_BITSANDBYTES=0 to skip)"
  python3 -m pip install bitsandbytes=="${BITSANDBYTES_VERSION}" || echo "[setup] bitsandbytes install failed; continuing without it."
fi

echo "[setup] Writing non-interactive Accelerate config..."
mkdir -p "${ACCELERATE_CACHE_DIR}"
cat > "${ACCELERATE_CONFIG_FILE}" <<'YAML'
compute_environment: LOCAL_MACHINE
distributed_type: NO
num_processes: 1
machine_rank: 0
num_machines: 1
mixed_precision: bf16
use_cpu: false
downcast_bf16: no
YAML

echo "[setup] Done. Ready to run training via train.sh."

