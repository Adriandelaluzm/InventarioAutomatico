@echo off
setlocal
cd /d "%~dp0"

if not exist ".env" (
  if exist ".env.example" (
    copy ".env.example" ".env" >nul
    echo Se creo .env a partir de .env.example. Revisa la IP de la ESP32-CAM antes de continuar.
  )
)

where python >nul 2>nul
if errorlevel 1 (
  echo Python no esta instalado o no esta en PATH.
  exit /b 1
)

if not exist ".venv" (
  python -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
  rmdir /s /q ".venv"
  python -m venv .venv
)

".venv\Scripts\python.exe" -c "import sys; print(sys.version)" >nul 2>nul
if errorlevel 1 (
  rmdir /s /q ".venv"
  python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
