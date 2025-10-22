Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Ensure UTF-8 everywhere for Streamlit/Python
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

# Switch console code page to UTF-8
try {
    chcp 65001 | Out-Null
} catch {
    Write-Warning "Failed to change code page to UTF-8: $($_.Exception.Message)"
}

# Move to repo root (script resides in .streamlit)
$scriptDir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$repoRoot = Split-Path -Path $scriptDir -Parent
Set-Location -LiteralPath $repoRoot

# Activate virtual environment (PowerShell)
$venvActivate = Join-Path $repoRoot '.venv\Scripts\Activate.ps1'
if (Test-Path -LiteralPath $venvActivate) {
    & $venvActivate
} else {
    Write-Warning "Virtual environment activation script not found: $venvActivate"
}
streamlit run .\ui\app.py @args
