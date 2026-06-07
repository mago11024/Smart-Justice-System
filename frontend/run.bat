@echo off
cd /d "%~dp0"
echo Starting frontend on port 5173...
npm.cmd run dev -- --host 127.0.0.1
pause
