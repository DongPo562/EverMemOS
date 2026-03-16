param(
    [int]$Port = 1995,
    [string]$PythonPath = ".venv\Scripts\python.exe",
    [string]$HelperScript = "..\scripts\stop_evermemos.py",
    [string]$ComposeFile = "docker-compose.yaml"
)

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path $PSScriptRoot
Push-Location $projectRoot
try {
    if (-not (Test-Path $PythonPath)) {
        Write-Host "[ERROR] Cannot find '$PythonPath'"
        exit 1
    }

    if (-not (Test-Path $HelperScript)) {
        Write-Host "[ERROR] Cannot find '$HelperScript'"
        exit 1
    }

    if (-not (Test-Path $ComposeFile)) {
        Write-Host "[ERROR] Cannot find '$ComposeFile'"
        exit 1
    }

    & $PythonPath $HelperScript --port $Port --compose-file $ComposeFile
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
