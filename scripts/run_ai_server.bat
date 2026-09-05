@echo off
cd /d "%~dp0\.."

echo.
echo ========================================
echo   Product Server (KEEP THIS WINDOW OPEN)
echo ========================================
echo.
echo   CWD: %CD%
echo.

set "PY=python"
if exist "project\.venv\Scripts\python.exe" (
  set "PY=project\.venv\Scripts\python.exe"
  echo [OK] Using project\.venv
) else (
  echo [WARN] project\.venv not found, trying system python
  where python >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] Python not found. Run setup bat first.
    goto end
  )
)

if not exist "project\.env" (
  echo [ERROR] Missing project\.env
  echo         Copy project\.env.example to project\.env and set AGNES_API_KEY.
  goto end
)

call "%~dp0free_port_8765.bat"

echo.
echo Starting http://127.0.0.1:8765/ ...
echo If it crashes, screenshot this window.
echo.

"%PY%" scripts\stage0_server.py --no-browser
set ERR=%ERRORLEVEL%

echo.
if %ERR% neq 0 (
  echo [ERROR] Server exited with code %ERR%
) else (
  echo Server stopped normally.
)

:end
echo.
echo Press any key to close...
pause >nul
