param([ValidateSet('benchmark','limited')][string]$Profile='benchmark')
$ErrorActionPreference='Stop'
. "$PSScriptRoot\common.ps1"
Set-Location $ProjectRoot
Assert-Docker
$argsCompose=Get-ComposeArguments $Profile
New-Item -ItemType Directory -Force results\monitoring | Out-Null
& docker @argsCompose ps | Tee-Object results\monitoring\compose-ps.txt
& docker @argsCompose logs --no-color --tail 100 web | Tee-Object results\monitoring\web-logs.txt
$ids=@(& docker @argsCompose ps -q)
if (-not $ids) { throw 'Stack is not running.' }
& docker stats --no-stream @ids | Tee-Object results\monitoring\docker-stats.txt
Write-Host 'Save screenshots: compose-ps.png, web-logs.png, docker-stats.png, hurl.png in results/monitoring.'
