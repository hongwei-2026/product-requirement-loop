@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo.
echo ========================================
echo   产品需求梳理智能体 · 启动
echo ========================================
echo.

if not exist "project\.venv\Scripts\python.exe" (
  echo [WARN] 未检测到 project\.venv ，建议先运行 setup阶段1环境.bat
  echo.
)

if not exist "project\.env" (
  echo [ERROR] 缺少 project\.env
  echo         请复制 project\.env.example 为 project\.env 并填写 AGNES_API_KEY
  echo.
  pause
  exit /b 1
)

start "Product-Server-DO-NOT-CLOSE" "%~dp0scripts\run_ai_server.bat"

echo Waiting for server...
timeout /t 4 /nobreak >nul

start "" "http://127.0.0.1:8765/"

echo.
echo [OK] 已打开产品页。请勿关闭黑色服务窗口。
echo      产品首页: http://127.0.0.1:8765/
echo      使用指南: docs\交付\产品操作手册.md
echo.

echo Press any key to close this helper window (server stays open)...
pause
