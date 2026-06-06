@echo off
echo Stopping Case Dashboard...

echo Killing backend (port 8000)...
powershell -NoProfile -Command "$p = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess; if ($p) { Stop-Process -Id $p -Force; Write-Host '  backend stopped (PID:' $p ')' } else { Write-Host '  no backend running' }"

echo Killing frontend (port 5173)...
powershell -NoProfile -Command "$p = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess; if ($p) { Stop-Process -Id $p -Force; Write-Host '  frontend stopped (PID:' $p ')' } else { Write-Host '  no frontend running' }"

echo.
echo Done.
pause
