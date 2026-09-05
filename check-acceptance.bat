@echo off
cd /d "%~dp0"

echo.
echo ========================================
echo   Acceptance check (6 gates)
echo ========================================
echo.
echo   CWD: %CD%
echo.

if not exist "project\.venv\Scripts\python.exe" (
  echo [ERROR] Missing venv. Run setup bat first.
  echo.
  pause
  exit /b 1
)

project\.venv\Scripts\python.exe scripts\verify_acceptance.py
set ERR=%ERRORLEVEL%

echo.
if %ERR% equ 0 (
  echo [OK] Acceptance PASSED
) else (
  echo [FAIL] Acceptance FAILED, code %ERR%
)
echo.
pause
exit /b %ERR%
