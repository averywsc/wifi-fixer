@echo off
setlocal
title WiFi Fixer - building the app
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python is not installed. Installing it now, this takes a minute...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  echo.
  echo If you saw an error above, install Python from https://www.python.org/downloads
  echo and tick "Add Python to PATH". Otherwise it is installed now.
  echo Close this window and double-click build_exe.bat again.
  pause
  exit /b
)
echo Installing build tools...
py -m pip install --upgrade pyinstaller psutil
if errorlevel 1 goto fail
echo Building WiFiFixer.exe ...
py -m PyInstaller --onefile --noconsole --uac-admin --name WiFiFixer wifi_fixer.py
if errorlevel 1 goto fail
copy /y dist\WiFiFixer.exe WiFiFixer.exe >nul
echo.
echo DONE. WiFiFixer.exe is now in this folder. Double-click it.
explorer .
pause
exit /b
:fail
echo.
echo Something went wrong. Take a screenshot of this window so you can get help.
pause
