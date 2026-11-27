# test_setup.ps1
# Exercises Setup-Tokoflux.ps1 / Setup-Tokoflux.cmd. Network-free and
# non-destructive: it only uses temporary folders and a child PowerShell.
# Run with:  powershell -NoProfile -ExecutionPolicy Bypass -File test_setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$setup = Join-Path $root "Setup-Tokoflux.ps1"
$cmd = Join-Path $root "Setup-Tokoflux.cmd"
$pwsh = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$script:fail = 0

function Check([bool]$cond, [string]$name) {
    if ($cond) { Write-Host ("PASS  " + $name) -ForegroundColor Green }
    else { Write-Host ("FAIL  " + $name) -ForegroundColor Red; $script:fail++ }
}

Write-Host ""
Write-Host "test_setup.ps1 / Setup-Tokoflux tests" -ForegroundColor Cyan
Write-Host ""

# 1. The .cmd wrapper delegates to the .ps1 (same pattern as Installa-Tokoflux.cmd)
$cmdText = Get-Content -Raw $cmd
Check ($cmdText -match 'powershell\s+-NoProfile\s+-ExecutionPolicy\s+Bypass\s+-File\s+"%~dp0Setup-Tokoflux\.ps1"') `
    "Setup-Tokoflux.cmd delegates to Setup-Tokoflux.ps1"

# 2. The .ps1 parses without syntax errors
$tokens = $null; $errors = $null
[System.Management.Automation.Language.Parser]::ParseFile($setup, [ref]$tokens, [ref]$errors) | Out-Null
Check ($errors.Count -eq 0) "Setup-Tokoflux.ps1 parses without syntax errors"

# 3. Required behaviour is present; nothing destructive is present
$ps = Get-Content -Raw $setup
Check ($ps -match 'https://github\.com/rosariomoscato/tokoflux\.git') "clones the Tokoflux repo URL"
Check ($ps -match 'git\s+clone') "runs git clone"
Check ($ps -match 'git\s+-C\s+\$Target\s+pull') "runs git pull (existing repo)"
Check ($ps -match 'npm ci') "runs npm ci"
Check ($ps -match 'npm run build') "runs npm run build"
Check ($ps -match 'Avvia-Tokoflux\.cmd') "launches via Avvia-Tokoflux.cmd"
Check ($ps -match '\$env:USERPROFILE') "default target uses USERPROFILE"
Check ($ps -match '\[string\]\$Target') "target folder is a parameter"
foreach ($verb in @('Remove-Item', 'rmdir', '-Recurse', 'git reset', 'git clean')) {
    Check (-not ($ps -match [regex]::Escape($verb))) ("no destructive '" + $verb + "'")
}

# 4. Missing prerequisites -> graceful stop
$prereqDir = Join-Path ([System.IO.Path]::GetTempPath()) ("tf-setup-prereq-" + [guid]::NewGuid().ToString("N"))
$out = & $pwsh -NoProfile -Command "`$env:PATH='C:\Windows\System32'; & '$setup' -Target '$prereqDir'" 2>&1 | Out-String
$code = $LASTEXITCODE
Check ($code -ne 0) "missing prerequisites -> non-zero exit"
Check ($out -match 'Prerequisiti mancanti|Missing prerequisites') "missing prerequisites -> clear message"

# 5. Existing non-git folder -> warn and stop, nothing deleted
$nonGitDir = Join-Path ([System.IO.Path]::GetTempPath()) ("tf-setup-nongit-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $nonGitDir | Out-Null
$marker = Join-Path $nonGitDir "marker.txt"
Set-Content -Path $marker -Value "keep" -Encoding ASCII
$out2 = & $pwsh -NoProfile -ExecutionPolicy Bypass -File $setup -Target $nonGitDir 2>&1 | Out-String
$code2 = $LASTEXITCODE
Check ($code2 -ne 0) "non-git folder -> non-zero exit"
Check ($out2 -match 'not a Tokoflux repository') "non-git folder -> warning message"
Check (Test-Path $marker) "non-git folder -> contents preserved"
Check (-not (Test-Path (Join-Path $nonGitDir ".git"))) "non-git folder -> no .git created"

# Cleanup temp folders
Remove-Item -LiteralPath $nonGitDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $prereqDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
if ($script:fail -eq 0) {
    Write-Host ("All tests passed.") -ForegroundColor Green
} else {
    Write-Host ("$script:fail test(s) failed.") -ForegroundColor Red
}
exit $script:fail
