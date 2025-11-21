Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$venvDir = if ($env:VENV_DIR) { $env:VENV_DIR } else { Join-Path $repoRoot ".venv" }

if (-not (Test-Path $venvDir)) {
    throw "[test_backend] Missing venv. Run scripts/setup_sd_env.ps1 first."
}

. (Join-Path $venvDir "Scripts\Activate.ps1")
Set-Location $repoRoot
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$env:PYTHONPATH;$repoRoot\yokai-gen" } else { "$repoRoot\yokai-gen" }

pytest yokai-gen/apps/backend/tests

