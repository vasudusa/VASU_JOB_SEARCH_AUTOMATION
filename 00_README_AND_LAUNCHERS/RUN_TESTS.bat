@echo off
setlocal
set "PROJECT_ROOT=D:\VASU_JOB_SEARCH_AUTOMATION"
cd /d "%PROJECT_ROOT%"
set "PYTHONPATH=%PROJECT_ROOT%\app"

if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    "%PROJECT_ROOT%\.venv\Scripts\python.exe" -m unittest discover -s 07_tests -p "test_*.py" -v
) else (
    python -m unittest discover -s 07_tests -p "test_*.py" -v
)

pause

