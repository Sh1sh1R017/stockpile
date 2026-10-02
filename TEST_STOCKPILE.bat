@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Stockpile - Self Healing Test Launcher
cd /d "%~dp0"

echo.
echo  ==========================================
echo       STOCKPILE SELF-HEALING LAUNCHER
echo  ==========================================
echo.

REM ---- Python 3.13 -------------------------------------------------------
REM Stockpile is kept on Python 3.13 for a stable FastAPI/Pydantic runtime.
set "PY="
where py >nul 2>&1
if not errorlevel 1 (
  py -3.13 -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PY=py -3.13"
)

if not defined PY (
  echo [FIX] Python 3.13 is missing. Trying Windows Package Manager...
  where winget >nul 2>&1
  if not errorlevel 1 (
    winget install --id Python.Python.3.13 -e --accept-source-agreements --accept-package-agreements
  )
)

if not defined PY (
  where py >nul 2>&1
  if not errorlevel 1 (
    py -3.13 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PY=py -3.13"
  )
)

if not defined PY (
  where python >nul 2>&1
  if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,13) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY=python"
  )
)

if not defined PY (
  echo.
  echo [ERROR] Python 3.13 was not found.
  echo Install Python 3.13 and run this launcher again.
  pause
  exit /b 1
)
echo [OK] Python found: %PY%

REM ---- Virtual environment -----------------------------------------------
REM Recreate an existing venv if it was created with Python 3.14 or another version.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,13) else 1)" >nul 2>&1
  if errorlevel 1 (
    echo [FIX] Existing virtual environment uses the wrong Python version.
    echo [FIX] Recreating it with Python 3.13...
    rmdir /s /q ".venv"
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo [FIX] Creating Python 3.13 virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
)
set "PYTHON=%CD%\.venv\Scripts\python.exe"
echo [OK] Virtual environment ready.

REM ---- Python packages ----------------------------------------------------
echo [FIX] Checking Python dependencies...
"%PYTHON%" -m pip install --disable-pip-version-check --upgrade pip >nul 2>&1
"%PYTHON%" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo.
  echo [ERROR] Python dependencies could not be installed.
  goto :fail
)
"%PYTHON%" -m pip install --disable-pip-version-check pytest >nul 2>&1
echo [OK] Python dependencies ready.

REM ---- FFmpeg -------------------------------------------------------------
where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo [FIX] FFmpeg is missing. Trying Windows Package Manager...
  where winget >nul 2>&1
  if not errorlevel 1 (
    winget install --id Gyan.FFmpeg.Shared -e --accept-source-agreements --accept-package-agreements
  )
)
where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo.
  echo [ERROR] FFmpeg is still unavailable.
  echo Install FFmpeg and run this launcher again.
  goto :fail
)
echo [OK] FFmpeg found.

REM ---- Quick import smoke test -------------------------------------------
echo [TEST] Importing Stockpile...
"%PYTHON%" -c "import ai_broll_autopilot; from ai_broll_autopilot.api.app import app; print('Stockpile import OK')"
if errorlevel 1 (
  echo.
  echo [ERROR] Stockpile failed its import smoke test.
  goto :fail
)
echo [OK] Stockpile imports cleanly.

REM ---- Automated tests ---------------------------------------------------
echo.
echo [TEST] Running automated tests...
"%PYTHON%" -m pytest -q
if errorlevel 1 (
  echo.
  echo [ERROR] Tests failed. Server will NOT be started.
  goto :fail
)
echo [OK] All automated tests passed.

REM ---- Launch -------------------------------------------------------------
echo.
echo  ==========================================
echo       ALL CHECKS PASSED - STARTING
echo  ==========================================
echo.
echo [START] Stockpile API: http://127.0.0.1:8000
echo [INFO] Keep this window open. Press Ctrl+C to stop.
echo.

start "" http://127.0.0.1:8000/docs
"%PYTHON%" -m ai_broll_autopilot.cli serve --host 127.0.0.1 --port 8000
goto :eof

:fail
echo.
echo  ==========================================
echo       STOCKPILE DID NOT PASS CHECKS
echo  ==========================================
echo.
echo The launcher stopped before starting the app.
pause
exit /b 1
