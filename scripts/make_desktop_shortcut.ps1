Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = $shell.CreateShortcut("$desktop\Coloring Explorers.lnk")
$lnk.TargetPath = (Join-Path (Get-Location) "start-ui.bat")
$lnk.WorkingDirectory = (Get-Location).Path
$lnk.WindowStyle = 1
$lnk.Description = "Launch Coloring Explorers UI"
$lnk.Save()

Write-Host "Shortcut created on Desktop: Coloring Explorers.lnk"

