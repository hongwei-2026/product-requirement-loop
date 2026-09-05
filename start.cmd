@echo off
cd /d "%~dp0"
echo ===== START LOG ===== > "%~dp0start-log.txt"
echo CWD=%CD% >> "%~dp0start-log.txt"
echo. >> "%~dp0start-log.txt"

echo.
echo ========================================
echo   START (same window, will not flash-close)
echo ========================================
echo.
echo CWD: %CD%
echo Log: %~dp0start-log.txt
echo.

if not exist "project\.venv\Scripts\python.exe" (
  echo [ERROR] Missing project\.venv
  echo [ERROR] Missing project\.venv >> "%~dp0start-log.txt"
  pause
  exit /b 1
)

if not exist "project\.env" (
  echo [ERROR] Missing project\.env
  echo [ERROR] Missing project\.env >> "%~dp0start-log.txt"
  pause
  exit /b 1
)

call "%~dp0scripts\free_port_8765.bat"

echo Starting server at http://127.0.0.1:8765/
echo KEEP THIS WINDOW OPEN.
echo Demo login: demo / demo1234
echo.

start "" "http://127.0.0.1:8765/"

project\.venv\Scripts\python.exe scripts\stage0_server.py --no-browser
set ERR=%ERRORLEVEL%

echo.
echo Server exited code=%ERR%
echo Server exited code=%ERR% >> "%~dp0start-log.txt"
echo.
echo Press any key to close...
pause
