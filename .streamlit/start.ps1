$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
chcp 65001 | Out-Null
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path) | Out-Null
Set-Location ..
& .\.venv\Scripts\Activate.ps1
& .\.venv\Scripts\python.exe -m streamlit run .\ui\app.py
