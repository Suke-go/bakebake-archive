Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$venvDir = if ($env:VENV_DIR) { $env:VENV_DIR } else { Join-Path $repoRoot ".venv" }
$appModule = if ($env:APP_MODULE) { $env:APP_MODULE } else { "apps.backend.app.main:app" }
$host = if ($env:HOST) { $env:HOST } else { "0.0.0.0" }
$port = if ($env:PORT) { $env:PORT } else { "8000" }
$device = if ($env:YOKAI_DEVICE) { $env:YOKAI_DEVICE } else { "auto" }

if (-not (Test-Path $venvDir)) {
    throw "[run_backend] Missing venv at $venvDir. Run scripts/setup_sd_env.ps1 first."
}

. (Join-Path $venvDir "Scripts\Activate.ps1")
Set-Location $repoRoot
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$env:PYTHONPATH;$repoRoot\yokai-gen" } else { "$repoRoot\yokai-gen" }

$env:YOKAI_DEVICE = $device
$env:YOKAI_MODEL_DIR = if ($env:YOKAI_MODEL_DIR) { $env:YOKAI_MODEL_DIR } else { Join-Path $repoRoot "yokai-gen/models/base" }
$env:YOKAI_LORA_DIR = if ($env:YOKAI_LORA_DIR) { $env:YOKAI_LORA_DIR } else { Join-Path $repoRoot "yokai-gen/models/lora" }

Write-Host "[run_backend] Starting FastAPI on $host`:$port"
uvicorn $appModule --host $host --port $port --reload

