<#
  dev-backend.ps1
  Unified dev startup — checks Docker, stops stale processes, migrates,
  and starts Uvicorn with --reload.

  Usage: .\scripts\dev-backend.ps1
#>
$ErrorActionPreference = 'Stop'
$repo = 'E:\Code_development\Coffee_bake_system'
$backend = Join-Path $repo 'backend'
$uv = 'C:\Users\Kaiser\AppData\Local\Programs\Python\Python312\Scripts\uv.exe'

Write-Host "=== Coffee Roast Dev Backend ===" -ForegroundColor Cyan

# 1. Check Docker PostgreSQL
Write-Host "[1/5] PostgreSQL container …" -ForegroundColor Yellow
$dbStatus = docker compose -f (Join-Path $backend 'docker-compose.yml') ps db --format json 2>$null | ConvertFrom-Json
if (-not $dbStatus -or $dbStatus.Health -ne 'healthy') {
    Write-Host "  Starting db …"
    docker compose -f (Join-Path $backend 'docker-compose.yml') up -d db
    Start-Sleep 3
}
Write-Host "  DB ready" -ForegroundColor Green

# 2. Stop any stale backend process on port 8000
Write-Host "[2/5] Checking port 8000 …" -ForegroundColor Yellow
$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)"
    $cmdLine = $proc.CommandLine
    if ($cmdLine -match 'uvicorn.*app\.main') {
        Write-Host "  Stopping stale uvicorn (PID $($proc.ProcessId)) …"
        Stop-Process -Id $proc.ProcessId -Force
        Start-Sleep 1
    } else {
        Write-Host "  WARNING: port 8000 occupied by non-uvicorn process:" -ForegroundColor Red
        Write-Host "    $cmdLine"
        exit 1
    }
}
Write-Host "  Port 8000 free" -ForegroundColor Green

# 3. Migrations
Write-Host "[3/5] Alembic upgrade …" -ForegroundColor Yellow
Set-Location $backend
& $uv run alembic upgrade head
& $uv run alembic current
Write-Host "  Migrations up to date" -ForegroundColor Green

# 4. Show version info
Write-Host "[4/5] Version info …" -ForegroundColor Yellow
$sha = git -C $repo rev-parse --short HEAD
$env:APP_GIT_SHA = $sha
Write-Host "  Git SHA: $sha" -ForegroundColor Green

# 5. Start with --reload
Write-Host "[5/5] Starting Uvicorn …" -ForegroundColor Yellow
Write-Host "  API:   http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "  Docs:  http://127.0.0.1:8000/api/v1/docs" -ForegroundColor Cyan
Write-Host "  Meta:  http://127.0.0.1:8000/api/v1/meta" -ForegroundColor Cyan
Write-Host ""

& $uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
