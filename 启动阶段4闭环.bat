@echo off
cd /d "%~dp0"
echo Stage4 demo loop (reuse artifacts if present)...
cd project
call .venv\Scripts\activate.bat
python implementation.py trials\case-01 --demo --reuse-artifacts
echo.
echo Stage5 check...
python check.py trials\case-01\output\stories.json --source trials\case-01\input\journal-official-full.md --write-uncovered trials\case-01\output\uncovered.md --allow-documented-uncovered
python check.py trials\case-01\output\accepted.json --source trials\case-01\input\journal-official-full.md --strict --allow-documented-uncovered
echo.
pause
