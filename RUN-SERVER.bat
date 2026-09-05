@echo off
cd /d "%~dp0"
title Product-Server
echo CWD=%CD%
echo.

if not exist "project\.venv\Scripts\python.exe" (
  echo [ERROR] Missing project\.venv\Scripts\python.exe
  echo Run setup bat first.
  goto hold
)

if not exist "project\.env" (
  echo [ERROR] Missing project\.env
  echo Copy project\.env.example to project\.env
  goto hold
)

echo Freeing port 8765 if needed...
call "%~dp0scripts\free_port_8765.bat"

echo.
echo Starting http://127.0.0.1:8765/
echo Login: demo / demo1234
echo KEEP THIS WINDOW OPEN.
echo.

start "" "http://127.0.0.1:8765/login.html"

"%~dp0project\.venv\Scripts\python.exe" "%~dp0scripts\stage0_server.py" --no-browser
echo.
echo [STOPPED] exit code=%ERRORLEVEL%

:hold
echo.
echo Window stays open. Read any error above, then press a key.
pause
