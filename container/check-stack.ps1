param([ValidateSet('benchmark','limited')][string]$Profile='benchmark')
$ErrorActionPreference='Stop'
. "$PSScriptRoot\common.ps1"
Set-Location $ProjectRoot
Assert-Docker
$argsCompose=Get-ComposeArguments $Profile
$health=Invoke-RestMethod 'http://localhost:4567/health'
if ($health.status -ne 'ok') { throw 'API health check failed.' }
& docker @argsCompose exec -T web python -c 'import os; assert os.getuid()==1000; print(os.getuid())'
if ($LASTEXITCODE -ne 0) { throw 'Non-root verification failed.' }
if (-not (Get-Command hurl -ErrorAction SilentlyContinue)) { throw 'Install Hurl; Lab 3 requires its run screenshot.' }
New-Item -ItemType Directory -Force results\monitoring | Out-Null
$ErrorActionPreference='Continue'
& hurl --test .\tests\ --variables-file .\tests\variables.properties --jobs 1 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath results\monitoring\hurl-console.txt
$code=$LASTEXITCODE
$ErrorActionPreference='Stop'
$code | Set-Content results\monitoring\hurl-exit-code.txt
if ($code -ne 0) { throw 'Hurl failed. Do not benchmark until API checks pass.' }
