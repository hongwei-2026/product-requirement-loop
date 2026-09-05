@echo off
cd /d "%~dp0"

echo.
echo ========================================
echo   Product Requirement Loop - START
echo ========================================
echo.
echo   CWD: %CD%
echo.

if not exist "project\.venv\Scripts\python.exe" (
  echo [ERROR] Missing project\.venv
  echo         Double-click setup bat first (filename starts with setup).
  echo.
  pause
  exit /b 1
)

if not exist "project\.env" (
  echo [ERROR] Missing project\.env
  echo         Copy project\.env.example to project\.env
  echo         and set AGNES_API_KEY.
  echo.
  pause
  exit /b 1
)

echo [OK] Env check passed.
echo      Opening Product-Server window. Keep that window open.
echo.

start "Product-Server" /D "%~dp0" cmd /k "scripts\run_ai_server.bat"

echo Waiting about 5 seconds...
timeout /t 5 /nobreak >nul

echo.
echo Probing http://127.0.0.1:8765/ ...
project\.venv\Scripts\python.exe -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/login.html', timeout=3); print('[OK] Server is up')" 2>nul
if errorlevel 1 (
  echo [WARN] Cannot reach the page yet.
  echo        Check the Product-Server window for errors.
  echo.
) else (
  start "" "http://127.0.0.1:8765/"
  echo [OK] Browser opened.
  echo.
)

echo ----------------------------------------
echo  You may close THIS window.
echo  Keep Product-Server window open.
echo  Demo login: demo / demo1234
echo ----------------------------------------
echo.
pause
