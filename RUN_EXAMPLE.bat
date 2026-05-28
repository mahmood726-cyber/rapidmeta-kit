@echo off
REM Double-click this (Windows) to build the example RapidMeta dashboard
REM and open it in your browser. Needs Python installed (python.org).
cd /d "%~dp0"
echo Building the example RapidMeta dashboard...
python clone.py configs/example_finerenone_ckd.json
if errorlevel 1 (
  echo.
  echo Could not run. Is Python installed? Get it at https://www.python.org/downloads/
  echo During install on Windows, tick "Add Python to PATH".
  pause
  exit /b 1
)
echo.
echo Opening the dashboard in your browser...
start "" "output\finerenone_ckd.html"
echo.
echo To make your own: copy a file in the configs\ folder, edit the drug,
echo condition, and trials, then run:  python clone.py configs\your_file.json
pause
