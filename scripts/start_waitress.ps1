[CmdletBinding()]
Param(
    [string]$ListenAddress = "0.0.0.0",
    [int]$ListenPort = 8000
)

$ErrorActionPreference = "Stop"
$InformationPreference = "Continue"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvActivate = Join-Path $projectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    & $venvActivate
} else {
    Write-Warning ".venv not found. Run 'python -m venv .venv' first."
}

[Environment]::SetEnvironmentVariable('FLASK_DEBUG', '0', 'Process')
[Environment]::SetEnvironmentVariable('FLASK_APP', 'app.py', 'Process')

if (-not (Get-Command waitress-serve -ErrorAction SilentlyContinue)) {
    Write-Information "Installing waitress into the virtual environment..."
    pip install waitress | Out-Null
}

$originalLocation = Get-Location
Set-Location -LiteralPath $projectRoot
try {
    Write-Information "Upgrading database schema (flask db upgrade)..."
    flask db upgrade
} finally {
    Set-Location $originalLocation
}

$displayTarget = [string]::Format("{0}:{1}", $ListenAddress, $ListenPort)
Write-Information ("Starting Waitress on {0}" -f $displayTarget)
$waitressTarget = 'app' + ':' + 'app'
$waitressArgs = @(
    '--host', $ListenAddress,
    '--port', $ListenPort.ToString(),
    $waitressTarget
)
& waitress-serve @waitressArgs
