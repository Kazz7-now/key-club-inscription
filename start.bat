@echo off
cd /d "%~dp0"
echo === Key Club - demarrage local (Windows) ===

where python >nul 2>nul
if errorlevel 1 (
  echo Python 3 n'est pas installe.
  pause
  exit /b 1
)

if not exist ".venv" python -m venv .venv
call .venv\Scripts\activate
python -m pip install -q -r requirements.txt
start "" http://127.0.0.1:5000
python app.py
pause
