@echo off
setlocal
set "PROJECT_ROOT=D:\VASU_JOB_SEARCH_AUTOMATION"
cd /d "%PROJECT_ROOT%"
set "PYTHONPATH=%PROJECT_ROOT%\app"

if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    "%PROJECT_ROOT%\.venv\Scripts\python.exe" run_phase1.py
) else (
    python run_phase1.py
)

echo.
echo Phase 1 dry-run complete. Review 06_reports, 08_logs, 09_exports, and 05_database.
pause

