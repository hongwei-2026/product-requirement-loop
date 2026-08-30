@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo Opening review.html ...
start "" "%~dp0project\trials\case-01\review.html"
if errorlevel 1 (
    echo Failed to open browser.
    pause
    exit /b 1
)
echo Done. Left side should show journal text.
timeout /t 3 >nul
