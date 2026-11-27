$ErrorActionPreference = "Stop"
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Tokoflux.lnk"
$sc = $ws.CreateShortcut($shortcutPath)
$sc.TargetPath = Join-Path $dir "Avvia-Tokoflux.cmd"
$sc.WorkingDirectory = $dir
$ico = Join-Path $dir "tokoflux.ico"
if (Test-Path $ico) { $sc.IconLocation = $ico }
$sc.Description = "Tokoflux - monitor dell'inferenza locale"
$sc.Save()
Write-Host ""
Write-Host "Collegamento creato sul desktop: Tokoflux" -ForegroundColor Green
Write-Host "Fai doppio clic sull'icona per avviare Tokoflux."
