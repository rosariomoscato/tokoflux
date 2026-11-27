# Setup-Tokoflux.ps1
# One-shot setup: clone (or update) Tokoflux from GitHub, rebuild the frontend,
# and launch it. Idempotent and non-destructive: it never deletes or overwrites
# existing data.
param(
    [string]$Target = (Join-Path $env:USERPROFILE "Tokoflux")
)

$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/rosariomoscato/tokoflux.git"
$Avvia = "Avvia-Tokoflux.cmd"

function Fail([string]$line) {
    Write-Host ""
    Write-Host $line -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Setup Tokoflux / Tokoflux setup" -ForegroundColor Cyan
Write-Host "Cartella di destinazione / Target folder: $Target"
Write-Host ""

# 1. Prerequisiti / Prerequisites
$missing = @()
foreach ($cmd in @("git", "node", "npm", "uv")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { $missing += $cmd }
}
if ($missing.Count -gt 0) {
    Write-Host "Prerequisiti mancanti / Missing prerequisites: $($missing -join ', ')" -ForegroundColor Red
    Write-Host "Installa Git, Node.js (include npm) e uv, poi riprova."
    Write-Host "Install Git, Node.js (includes npm) and uv, then run again."
    Fail "Setup interrotto / Setup aborted."
}

# 2. Clone o aggiornamento / Clone or update
if (Test-Path -LiteralPath $Target) {
    if (Test-Path -LiteralPath (Join-Path $Target ".git")) {
        Write-Host "Repository gia' presente: aggiorno / Repository found: pulling..." -ForegroundColor Green
        git -C $Target pull
        if ($LASTEXITCODE -ne 0) { Fail "git pull non riuscito / git pull failed." }
    } else {
        Write-Host "La cartella esiste ma non e' un repository Tokoflux." -ForegroundColor Yellow
        Write-Host "The folder exists but is not a Tokoflux repository."
        Write-Host "Non elimino e non sovrascrivo nulla / Nothing was deleted or overwritten."
        Fail "Indica una cartella diversa con -Target / Choose a different folder with -Target."
    }
} else {
    Write-Host "Clono il repository / Cloning repository..." -ForegroundColor Green
    git clone $RepoUrl $Target
    if ($LASTEXITCODE -ne 0) { Fail "git clone non riuscito / git clone failed." }
}

# 3. Build del frontend / Frontend build
$Frontend = Join-Path $Target "frontend"
Write-Host ""
Write-Host "Compilo il frontend / Building the frontend (npm ci && npm run build)..." -ForegroundColor Green
Push-Location $Frontend
try {
    npm ci
    if ($LASTEXITCODE -ne 0) { Fail "npm ci non riuscito / npm ci failed." }
    npm run build
    if ($LASTEXITCODE -ne 0) { Fail "npm run build non riuscito / npm run build failed." }
} finally {
    Pop-Location
}

# 4. Avvio / Launch
Write-Host ""
Write-Host "Avvio Tokoflux / Launching Tokoflux..." -ForegroundColor Green
Start-Process -FilePath "cmd.exe" -ArgumentList "/c $Avvia" -WorkingDirectory $Target
Write-Host "Tokoflux apre http://127.0.0.1:8765 / Tokoflux opens http://127.0.0.1:8765"
Write-Host ""
Write-Host "Setup completato / Setup complete." -ForegroundColor Green
