param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Model,
    [ValidateRange(1024, 65535)]
    [int]$Port = 5000,
    [string]$DatabaseUrl = '',
    [switch]$Reload
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw 'Create the project virtualenv and install requirements.txt first.'
}

$previousKey = [Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'Process')
$previousModel = [Environment]::GetEnvironmentVariable('AI_MODEL', 'Process')
$previousPort = [Environment]::GetEnvironmentVariable('PORT', 'Process')
$previousDatabase = [Environment]::GetEnvironmentVariable('DATABASE_URL', 'Process')
$secureKey = $null
$keyPointer = [IntPtr]::Zero
try {
    if ([string]::IsNullOrWhiteSpace($previousKey)) {
        $secureKey = Read-Host 'Gemini API key (hidden; kept only for this server process)' -AsSecureString
        if ($secureKey.Length -eq 0) { throw 'An API key is required.' }
        $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
        $env:GEMINI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
    }
    $env:AI_MODEL = $Model
    $env:PORT = [string]$Port
    if ($DatabaseUrl) { $env:DATABASE_URL = $DatabaseUrl }
    Push-Location -LiteralPath $projectRoot
    try {
        & $pythonPath tools/gemini_preflight.py
        if ($LASTEXITCODE -ne 0) { throw 'Gemini model access check failed. No document was sent.' }
        $modelReport = Get-Content -LiteralPath (Join-Path $projectRoot 'instance/gemini-preflight.json') -Raw | ConvertFrom-Json
        $env:AI_MODEL = $modelReport.selected_model
        Write-Host "Starting Procure at http://127.0.0.1:$Port. Press Ctrl+C to stop."
        if ($Reload) {
            & $pythonPath -m flask --app run:app run --host 127.0.0.1 --port $Port --reload --no-debugger
        }
        else { & $pythonPath run.py serve }
        if ($LASTEXITCODE -ne 0) { throw "Server exited with code $LASTEXITCODE." }
    }
    finally { Pop-Location }
}
finally {
    [Environment]::SetEnvironmentVariable('GEMINI_API_KEY', $previousKey, 'Process')
    [Environment]::SetEnvironmentVariable('AI_MODEL', $previousModel, 'Process')
    [Environment]::SetEnvironmentVariable('PORT', $previousPort, 'Process')
    [Environment]::SetEnvironmentVariable('DATABASE_URL', $previousDatabase, 'Process')
    if ($keyPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    }
    if ($null -ne $secureKey) { $secureKey.Dispose() }
}
