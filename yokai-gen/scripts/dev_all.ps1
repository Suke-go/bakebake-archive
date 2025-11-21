Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$frontendDir = Join-Path $repoRoot "yokai-gen/apps/frontend"

$backendJob = Start-Job -ScriptBlock {
    & "$using:repoRoot\yokai-gen\scripts\run_backend.ps1"
}

Set-Location $frontendDir
if (-not (Test-Path "node_modules")) {
    npm install
}

try {
    npm run dev
} finally {
    Stop-Job $backendJob | Out-Null
    Remove-Job $backendJob | Out-Null
}

