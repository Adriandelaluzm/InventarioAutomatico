$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Se creo .env a partir de .env.example. Revisa la IP de la ESP32-CAM antes de continuar."
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python no esta instalado o no esta en PATH."
}

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Remove-Item ".venv" -Recurse -Force
    python -m venv .venv
} else {
    & $venvPython -c "import sys; print(sys.version)" *> $null
    if ($LASTEXITCODE -ne 0) {
        Remove-Item ".venv" -Recurse -Force
        python -m venv .venv
    }
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
