@echo off
cd /d "%~dp0"
echo Starting backend on port 8000...
python -m uvicorn app.main:app --reload --port 8000
pause
