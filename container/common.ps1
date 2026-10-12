$ProjectRoot = Split-Path $PSScriptRoot -Parent
function Get-ComposeArguments([string]$Profile) {
    $arguments = @('compose', '-f', (Join-Path $ProjectRoot 'docker-compose.yml'))
    if ($Profile -eq 'benchmark') {
        $arguments += @('-f', (Join-Path $ProjectRoot 'docker-compose.benchmark.yml'))
    }
    return $arguments
}
function Assert-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Install and start Docker Desktop.' }
    & docker info --format '{{.OSType}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop Engine is not ready.' }
    if (-not (Test-Path (Join-Path $ProjectRoot '.env'))) { throw 'Run container/setup-env.ps1 first.' }
}
