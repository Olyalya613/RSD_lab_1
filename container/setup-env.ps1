$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& py -3.12 "$PSScriptRoot\create-env.py"
if ($LASTEXITCODE -ne 0) { throw 'Could not create .env. Install Python 3.12.' }
