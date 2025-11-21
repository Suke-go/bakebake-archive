# Bootstraps a local Stable Diffusion Diffusers environment for yokai generation on Windows PowerShell.
# 1. Creates/updates a virtual environment
# 2. Installs backend requirements
# 3. Optionally pulls the base SD model via huggingface-cli

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$venvDir = if ($env:VENV_DIR) { $env:VENV_DIR } else { Join-Path $repoRoot ".venv" }
$pythonExe = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }
$requirements = if ($env:REQUIREMENTS_FILE) { $env:REQUIREMENTS_FILE } else { Join-Path $repoRoot "yokai-gen/apps/backend/requirements.txt" }
$modelId = if ($env:MODEL_ID) { $env:MODEL_ID } else { "stabilityai/stable-diffusion-xl-base-1.0" }
$modelDir = if ($env:MODEL_DIR) { $env:MODEL_DIR } else { Join-Path $repoRoot "yokai-gen/models/base" }
$hfCache = if ($env:HF_CACHE_DIR) { $env:HF_CACHE_DIR } else { Join-Path $repoRoot ".cache/huggingface" }

Write-Host "[setup] Repo root: $repoRoot"
if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    throw "[setup] $pythonExe not found. Install Python 3.10+ first."
}

if (-not (Test-Path $venvDir)) {
    Write-Host "[setup] Creating virtual environment at $venvDir"
    & $pythonExe -m venv $venvDir
} else {
    Write-Host "[setup] Reusing existing virtual environment at $venvDir"
}

$activate = Join-Path $venvDir "Scripts\Activate.ps1"
. $activate

python -m pip install --upgrade pip wheel setuptools

if (-not (Test-Path $requirements)) {
    throw "[setup] Requirements file $requirements is missing. Add backend deps first."
}

Write-Host "[setup] Installing Python dependencies..."
python -m pip install -r $requirements

New-Item -ItemType Directory -Force -Path $modelDir | Out-Null

if (Get-Command huggingface-cli -ErrorAction SilentlyContinue) {
    Write-Host "[setup] Downloading base model $modelId"
    $env:HF_HOME = $hfCache
    huggingface-cli download $modelId --exclude "*.bin" --local-dir $modelDir --resume-download
} else {
    Write-Host "[setup] huggingface-cli not found."
    Write-Host "Install via 'pip install huggingface-hub' then run:"
    Write-Host "    huggingface-cli login"
    Write-Host "and re-run this script."
}

Write-Host "[setup] Done. Activate the venv with:"
Write-Host "    . $activate"

