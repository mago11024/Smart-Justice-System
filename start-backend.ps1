param([int]$Port = 8000)

$root = Split-Path -Parent $PSCommandPath
Set-Location "$root\backend"

Write-Host "Starting backend on port $Port..." -ForegroundColor Cyan
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port $Port
