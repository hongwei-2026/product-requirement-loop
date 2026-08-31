@echo off
REM Free port 8765 if another program (e.g. python -m http.server) is using it.
set PORT=8765
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
  echo [INFO] Stopping process on port %PORT% PID=%%a
  taskkill /PID %%a /F >nul 2>&1
)
ping 127.0.0.1 -n 2 >nul
