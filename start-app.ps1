param(
    [int]$Port = 1995,
    [string]$PythonPath = ".venv\Scripts\python.exe",
    [string]$EntryScript = "src/run.py"
)

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path $PSScriptRoot
$workspaceRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$logsDir = Join-Path $workspaceRoot "logs"
$issuesDir = Join-Path $logsDir "issues"
New-Item -ItemType Directory -Force -Path $issuesDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$tempLog = Join-Path $env:TEMP "start-app-$timestamp.log"
$issueLog = Join-Path $issuesDir "issues-$timestamp.log"
$commandText = "$PythonPath $EntryScript --port $Port"

@(
    "timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')",
    "command: $commandText",
    "workdir: $projectRoot",
    "python: $($PSVersionTable.PSEdition) $($PSVersionTable.PSVersion)",
    "---- output ----"
) | Set-Content -Path $tempLog -Encoding UTF8

$exitCode = 0

Push-Location $projectRoot
try {
    try {
        # Run via cmd so stderr warnings are treated as output text, not PowerShell errors.
        $cmdLine = "`"$PythonPath`" `"$EntryScript`" --port $Port 2>&1"
        cmd /d /c $cmdLine | ForEach-Object {
            $_
            Add-Content -Path $tempLog -Value $_ -Encoding UTF8
        }
        if ($LASTEXITCODE -ne $null) {
            $exitCode = $LASTEXITCODE
        }
    } catch {
        $errorText = $_ | Out-String
        Write-Host $errorText
        Add-Content -Path $tempLog -Value $errorText -Encoding UTF8
        $exitCode = 1
    }
} finally {
    Pop-Location
}

if ($exitCode -ne 0 -and $exitCode -ne -1073741510) {
    Get-ChildItem -Path $issuesDir -File -Filter "*.log" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
    Move-Item -Path $tempLog -Destination $issueLog -Force
    Write-Host ""
    Write-Host "Startup failed. Issue log saved to:"
    Write-Host $issueLog
    exit $exitCode
}

if (Test-Path $tempLog) {
    Remove-Item -Path $tempLog -Force
}

if ($exitCode -eq -1073741510) {
    Write-Host ""
    Write-Host "Stopped by Ctrl+C. No issue log generated."
    exit 130
}

Write-Host ""
Write-Host "Process exited without startup error. No issue log generated."
exit 0
