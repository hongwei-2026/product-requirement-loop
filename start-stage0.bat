@echo off
REM Pure ASCII - full stage 0 launcher
cd /d "%~dp0"

echo.
echo ========================================
echo   Stage 0 launcher
echo ========================================
echo.

where powershell >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PowerShell not found.
    echo Run open-review.bat instead.
    goto :end
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_stage0.ps1"
set ERR=%ERRORLEVEL%

echo.
if %ERR% equ 0 (
    echo [OK] Launcher finished. Check browser tabs.
) else (
    echo [FAIL] exit code %ERR%
    echo Run open-review.bat to open acceptance page only.
)

:end
echo.
echo This window is only a helper. Closing it does NOT close the browser.
echo.
pause
