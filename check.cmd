@echo off
cd /d "%~dp0"
echo.
echo CWD: %CD%
echo.
if not exist "project\.venv\Scripts\python.exe" (
  echo [ERROR] Missing venv
  pause
  exit /b 1
)
project\.venv\Scripts\python.exe scripts\verify_acceptance.py
echo.
echo ExitCode=%ERRORLEVEL%
pause
