@echo off
cd /d "%~dp0"
echo Running verify_all (stage 0..7)...
echo.
python scripts\verify_all.py --write-reports
echo.
pause
