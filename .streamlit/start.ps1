Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# 1) Set UTF-8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
chcp 65001 | Out-Null

# 2) Change to project root (the folder containing this script)
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path) | Out-Null
Set-Location ..

# 3) Activate the venv
& .\.venv\Scripts\Activate.ps1

# 4) Start the app using the venv's Python
& .\.venv\Scripts\python.exe -m streamlit run .\ui\app.py @args
