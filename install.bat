@echo off
REM ============================================================
REM  Hark History Studio - Local Backend Edition - Installer
REM  Tested with Python 3.12.3 (any real Python 3.11+ works).
REM ============================================================
setlocal
cd /d "%~dp0"
echo.
echo === Hark History Studio - checking your Python ===
echo.

REM --- Probe for a REAL Python (the Microsoft Store stub does not count) ---
set "PYEXE="
where py >nul 2>nul && set "PYEXE=py"
if not defined PYEXE where python >nul 2>nul && set "PYEXE=python"
if not defined PYEXE goto :nopython

for /f "delims=" %%V in ('%PYEXE% --version 2^>^&1') do set "PYVER=%%V"
echo Found: %PYVER%
%PYEXE% -c "import sys; print('Python path:', sys.executable)"
%PYEXE% -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" || goto :oldpython
echo %PYEXE% | findstr /I "WindowsApps" >nul && goto :storepython
%PYEXE% -c "import sys; p = sys.executable.lower(); sys.exit(1 if 'windowsapps' in p else 0)" || goto :storepython

echo.
echo === Creating the virtual environment (.venv) ===
if not exist ".venv\Scripts\python.exe" (
  %PYEXE% -m venv .venv
  if errorlevel 1 goto :venvfail
) else (
  echo .venv already exists - reusing it.
)

echo.
echo === Installing core dependencies ===
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :pipfail

echo.
echo === Installing the optional voiceover engine (Piper TTS) ===
".venv\Scripts\python.exe" -m pip install -r requirements-tts.txt
if errorlevel 1 (
  echo.
  echo NOTE: Piper TTS could not be installed. The studio still works -
  echo only the voiceover feature stays off until Piper is installed.
)

echo.
echo === Checking FFmpeg ===
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo.
  echo WARNING: FFmpeg was NOT found on your PATH.
  echo The studio needs FFmpeg to render MP4 videos. Install it with:
  echo     winget install Gyan.FFmpeg
  echo or download it from https://www.gyan.dev/ffmpeg/builds/ and add
  echo its "bin" folder to your PATH. Then run start.bat again.
) else (
  ffmpeg -version | findstr /C:"ffmpeg version"
  echo FFmpeg found - rendering is available.
)

echo.
echo ============================================================
echo  Installation finished.
echo  Now double-click start.bat to launch the studio.
echo ============================================================
pause
exit /b 0

:nopython
echo No Python was found on this PC.
echo Install REAL Python 3.11 or newer from https://www.python.org/downloads/
echo IMPORTANT: tick "Add python.exe to PATH" during setup, and do NOT use
echo the Microsoft Store version - it does not work with this studio.
pause
exit /b 1

:storepython
echo The Python on this PC is the Microsoft Store stub, which cannot run
echo this studio. Install REAL Python from https://www.python.org/downloads/
echo (tick "Add python.exe to PATH"), then run install.bat again.
pause
exit /b 1

:oldpython
echo %PYVER% is too old. This studio needs Python 3.11 or newer.
echo Install it from https://www.python.org/downloads/ and run install.bat again.
pause
exit /b 1

:venvfail
echo Could not create the virtual environment. Make sure Python is a real
echo python.org install, then run install.bat again.
pause
exit /b 1

:pipfail
echo Installing dependencies failed. Check your internet connection -
echo pip needs to download the packages once. Then run install.bat again.
pause
exit /b 1
