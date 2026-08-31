@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo.
echo ========================================
echo   Stage 1: setup Python environment
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ from python.org
    goto end
)

cd project

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtualenv .venv ...
    python -m venv .venv
)

echo Activating and installing packages ...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Checking imports ...
python -c "import yaml, langgraph; print('[OK] yaml + langgraph')"
if errorlevel 1 goto fail

cd ..
echo.
echo [OK] Stage 1 environment ready.
echo Next: copy implementation.py from your Fork (see docs\阶段1\阶段1实现报告.md)
echo       python scripts\verify_stage1.py
goto end

:fail
echo [FAIL] Import check failed.
cd ..

:end
echo.
pause
