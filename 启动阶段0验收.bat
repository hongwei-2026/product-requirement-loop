@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo.
echo ========================================
echo   阶段 0 验收启动
echo ========================================
echo.

where powershell >nul 2>&1
if errorlevel 1 (
    echo [错误] 找不到 PowerShell，无法启动。
    goto :fail
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_stage0.ps1"
set ERR=%ERRORLEVEL%

echo.
if %ERR% equ 0 (
    echo [完成] 若浏览器未弹出，请双击：打开验收页.bat
) else (
    echo [失败] 退出码 %ERR% — 请把本窗口文字截图发出来
)
goto :end

:fail
echo.
echo [备选] 双击同目录下的：打开验收页.bat

:end
echo.
pause
