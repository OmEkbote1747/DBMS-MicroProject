@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
    start "Amazon DBMS demo server" cmd /k py -u app.py
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo Python was not found. Install Python 3.10 or newer, then run this file again.
        pause
        exit /b 1
    )
    start "Amazon DBMS demo server" cmd /k python -u app.py
)

timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8000/"
