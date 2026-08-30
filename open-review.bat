@echo off
REM Pure ASCII - safe on Chinese Windows CMD (no UTF-8 garble)
cd /d "%~dp0"

set "REVIEW=%~dp0project\trials\case-01\review.html"

echo.
echo ========================================
echo   Open acceptance page (review.html)
echo ========================================
echo.

if not exist "%REVIEW%" (
    echo [ERROR] File not found:
    echo   %REVIEW%
    echo.
    goto :end
)

echo Opening in your default browser...
start "" "%REVIEW%"

echo.
echo [OK] Browser should open now.
echo.
echo CHECK: LEFT side = journal text in Chinese
echo        RIGHT side = 3 sample user stories
echo.
echo If browser did NOT open, copy this into Chrome/Edge address bar:
echo   %REVIEW%
echo.

:end
echo Close this window anytime - browser tab stays open.
echo.
pause
