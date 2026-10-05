param([string]$DatabaseUrl = 'postgresql://traveler_lab2:traveler_lab2_dev@127.0.0.1:5432/traveler_lab2')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    & py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 for Windows, then retry.' }
    & .\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Cannot install Python dependencies.' }
}
$env:DATABASE_URL = $DatabaseUrl
& .\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 4567 --workers 1
