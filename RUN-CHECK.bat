@echo off
cd /d "%~dp0"
title Acceptance-Check
echo CWD=%CD%
echo.

if not exist "project\.venv\Scripts\python.exe" (
  echo [ERROR] Missing venv
  pause
  exit /b 1
)

"%~dp0project\.venv\Scripts\python.exe" "%~dp0scripts\verify_acceptance.py"
echo.
echo ExitCode=%ERRORLEVEL%
pause
