@echo off
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

echo ================================
echo   Case Dashboard v1.0
echo ================================
echo.
echo [1/3] Starting backend on port 8000...
start "backend" cmd /k "cd /d ""%ROOT%\backend"" && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
timeout /t 3 /nobreak >nul

echo [2/3] Starting frontend on port 5173...
start "frontend" cmd /k "cd /d ""%ROOT%\frontend"" && npm.cmd run dev -- --host 127.0.0.1"
timeout /t 3 /nobreak >nul

echo [3/3] Opening browser...
start "" http://127.0.0.1:5173

echo.
echo Done. Run stop.bat to shut down.
