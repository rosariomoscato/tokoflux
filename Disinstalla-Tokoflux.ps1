$ErrorActionPreference = "Stop"
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "Disinstallazione Tokoflux" -ForegroundColor Cyan
Write-Host ""

# 1. Desktop shortcut
$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = Join-Path $desktop "Tokoflux.lnk"
if (Test-Path $lnk) {
    Remove-Item $lnk -Force
    Write-Host "- Rimosso il collegamento dal desktop." -ForegroundColor Green
} else {
    Write-Host "- Nessun collegamento sul desktop." 
}

# 2. App data (history + prefs DB)
$data = Join-Path $env:LOCALAPPDATA "Tokoflux"
if (Test-Path $data) {
    $r = Read-Host "Eliminare anche lo storico e i dati (LOCALAPPDATA\Tokoflux)? [s/N]"
    if ($r -match '^[sSyY]') {
        Remove-Item $data -Recurse -Force
        Write-Host "- Dati rimossi." -ForegroundColor Green
    } else {
        Write-Host "- Dati conservati."
    }
} else {
    Write-Host "- Nessun dato in LOCALAPPDATA."
}

# 3. App folder
$r2 = Read-Host "Eliminare anche la cartella dell'app (tutti i file di Tokoflux)? [s/N]"
if ($r2 -match '^[sSyY]') {
    $tmp = Join-Path $env:TEMP ("tokoflux-del-" + [guid]::NewGuid().ToString("N") + ".cmd")
    "@echo off`r`ntimeout /t 2 /nobreak >nul`r`nrmdir /s /q `"$dir`" 2>nul`r`nif exist `"$dir`" ( timeout /t 2 /nobreak >nul & rmdir /s /q `"$dir`" 2>nul )`r`ndel `"%~f0`" 2>nul" | Set-Content -Path $tmp -Encoding ASCII
    Start-Process -FilePath "cmd.exe" -ArgumentList @('/c', $tmp) -WindowStyle Hidden
    Write-Host "- La cartella dell'app verra' rimossa tra un attimo." -ForegroundColor Green
    Write-Host "  Se resta qualche file (finestra aperta), elimina la cartella a mano." 
} else {
    Write-Host "- Cartella dell'app conservata."
}

Write-Host ""
Write-Host "Disinstallazione completata." -ForegroundColor Green
Read-Host "Premi Invio per chiudere"
