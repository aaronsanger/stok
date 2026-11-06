@echo off
cd /d "%~dp0"
if exist "..\.venv\Scripts\python.exe" (
    "..\.venv\Scripts\python.exe" run_local_server.py --host 127.0.0.1 --port 8080
) else (
    python run_local_server.py --host 127.0.0.1 --port 8080
)
pause
