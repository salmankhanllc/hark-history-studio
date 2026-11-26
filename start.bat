@echo off
REM ============================================================
REM  History Studio - Local Backend Edition - Launcher
REM  Starts the local backend on http://127.0.0.1:8765 and
REM  opens the studio in your browser. Keep this window open
REM  while you work; close it to stop the studio.
REM ============================================================
setlocal
cd /d "%~dp0"
title History Studio - Local Backend

if not exist ".venv\Scripts\python.exe" (
  echo The studio is not installed yet.
  echo Run install.bat first - double-click it in this folder.
  pause
  exit /b 1
)

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo NOTE: FFmpeg was not found - the studio will open, but MP4
  echo rendering stays off until FFmpeg is installed (see README).
  echo.
)

echo Starting History Studio at http://127.0.0.1:8765 ...
start "" /min cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8765/"
".venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8765

echo.
echo The studio server has stopped.
pause
