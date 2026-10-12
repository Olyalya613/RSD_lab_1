param([ValidateSet('benchmark','limited')][string]$Profile='benchmark')
$ErrorActionPreference='Stop'
. "$PSScriptRoot\common.ps1"
Set-Location $ProjectRoot
Assert-Docker
$argsCompose=Get-ComposeArguments $Profile
& docker @argsCompose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Invalid Compose configuration.' }
& docker @argsCompose up --build --detach --wait --wait-timeout 180
if ($LASTEXITCODE -ne 0) { throw 'Stack did not become healthy. Run docker compose logs web postgres.' }
& docker @argsCompose ps
Write-Host 'Open http://localhost:4567/health. Profile:' $Profile
