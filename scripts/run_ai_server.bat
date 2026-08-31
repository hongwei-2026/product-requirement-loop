@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0\.."

echo.
echo ========================================
echo   Product Server (keep this window OPEN)
echo ========================================
echo.

set "PY=python"
if exist "project\.venv\Scripts\python.exe" (
  set "PY=project\.venv\Scripts\python.exe"
  echo [OK] Using project\.venv
) else (
  echo [WARN] project\.venv not found. Run setup阶段1环境.bat first.
  where python >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] Python not found.
    goto end
  )
)

if not exist "project\.env" (
    echo [ERROR] project\.env missing.
    echo         Copy project\.env.example to project\.env and set AGNES_API_KEY.
    goto end
)

call "%~dp0free_port_8765.bat"

echo Starting http://127.0.0.1:8765/ ...
echo.
"%PY%" scripts\stage0_server.py --no-browser
set ERR=%ERRORLEVEL%

echo.
if %ERR% neq 0 (
    echo [ERROR] Server exited with code %ERR%
) else (
    echo Server stopped.
)

:end
echo.
echo Press any key to close this window...
pause
