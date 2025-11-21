#!/usr/bin/env bash
# Kick off LoRA training on RunPod using sd-scripts.
set -euo pipefail

SD_SCRIPTS_DIR="${SD_SCRIPTS_DIR:-/workspace/sd-scripts}"
CONFIG_FILE="${CONFIG_FILE:-/workspace/project/runpod/config.toml}"
ACCELERATE_CMD="${ACCELERATE_CMD:-accelerate launch}"

if [ ! -d "${SD_SCRIPTS_DIR}" ]; then
  echo "[train] sd-scripts not found at ${SD_SCRIPTS_DIR}" >&2
  exit 1
fi
if [ ! -f "${CONFIG_FILE}" ]; then
  echo "[train] Config file not found at ${CONFIG_FILE}" >&2
  exit 1
fi

cd "${SD_SCRIPTS_DIR}"

${ACCELERATE_CMD} --num_processes=1 --mixed_precision=bf16 \
  train_network.py --config_file "${CONFIG_FILE}"

