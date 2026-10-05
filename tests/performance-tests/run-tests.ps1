param([ValidateSet('smoke','load','stress','spike','endurance','all')][string]$Test = 'smoke')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command k6 -ErrorAction SilentlyContinue)) { throw 'Install k6 with: winget install k6 --source winget' }
$apiUrl = if ($env:API_URL) { $env:API_URL.TrimEnd('/') } else { 'http://localhost:4567' }
if (([uri]$apiUrl).Host -notin @('localhost','127.0.0.1','[::1]')) { throw 'Lab 2 requires API, PostgreSQL and k6 on the same computer.' }
$apiListeners = Get-NetTCPConnection -LocalPort ([uri]$apiUrl).Port -State Listen -ErrorAction SilentlyContinue
$apiProcesses = $apiListeners | ForEach-Object { Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue }
if (-not ($apiProcesses | Where-Object { $_.ProcessName -match 'python|uvicorn' })) { throw 'Port belongs to another process. Start native Python API, not Docker.' }
$dbListeners = Get-NetTCPConnection -LocalPort 5432 -State Listen -ErrorAction SilentlyContinue
$dbProcesses = $dbListeners | ForEach-Object { Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue }
if (-not ($dbProcesses | Where-Object { $_.ProcessName -match '^postgres' })) { throw 'Start native PostgreSQL on port 5432, not Docker.' }
$health = Invoke-RestMethod "$apiUrl/health"
if ($health.status -ne 'ok') { throw 'API health check failed.' }
New-Item -ItemType Directory -Force results | Out-Null
$gitHead = 'not available'
if (Get-Command git -ErrorAction SilentlyContinue) { $gitHead = (& git rev-parse HEAD) -join '' }
$metadata = [ordered]@{
    started_at=(Get-Date).ToString('o'); api_url=$apiUrl; execution='native Windows processes, confirm PostgreSQL/API are not containers';
    os=(Get-CimInstance Win32_OperatingSystem).Caption;
    cpu=(Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name) -join '; ';
    logical_processors=(Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors;
    ram_gb=[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,2);
    k6_version=(& k6 version) -join ' '; workers=1; db_pool_max=20;
    git_head=$gitHead
}
$metadata | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 results\run-meta.json
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
& "$projectRoot\.venv\Scripts\python.exe" "$projectRoot\native\record-environment.py" --output results\run-meta.json
if ($LASTEXITCODE -ne 0) { throw 'Could not record database version and isolation level.' }
$tests = if ($Test -eq 'all') { @('smoke','load','stress','spike','endurance') } else { @($Test) }
foreach ($name in $tests) {
    $old = Get-ChildItem "results\$name-*" -File -ErrorAction SilentlyContinue
    if ($old) {
        $backup = "results\previous-$name-$(Get-Date -Format yyyyMMdd-HHmmss)"
        New-Item -ItemType Directory $backup | Out-Null
        $old | Move-Item -Destination $backup
    }
    Write-Host "Running $name. Endurance lasts 30 minutes; threshold failures in stress tests are recorded, not hidden."
    $monitor = Start-Job -ArgumentList (Join-Path $PSScriptRoot "results\$name-resources.csv") -ScriptBlock {
        param($file)
        'time,api_ram_mb,postgres_ram_mb,host_cpu_percent' | Set-Content -Encoding UTF8 $file
        while ($true) {
            $python = Get-Process python*,uvicorn* -ErrorAction SilentlyContinue
            $postgres = Get-Process postgres* -ErrorAction SilentlyContinue
            $pm = ($python | Measure-Object WorkingSet64 -Sum).Sum / 1MB
            $dm = ($postgres | Measure-Object WorkingSet64 -Sum).Sum / 1MB
            $cpu = (Get-CimInstance Win32_Processor | Measure-Object LoadPercentage -Average).Average
            '{0},{1},{2},{3}' -f (Get-Date).ToUniversalTime().ToString('o'), $pm.ToString('F2',[cultureinfo]::InvariantCulture),$dm.ToString('F2',[cultureinfo]::InvariantCulture),$cpu | Add-Content -Encoding UTF8 $file
            Start-Sleep -Seconds 5
        }
    }
    $ErrorActionPreference = 'Continue'
    & k6 run --no-usage-report --out "json=results/$name-metrics.json.gz" "$name-test.js" 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath "results\$name-console.txt"
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    Stop-Job $monitor
    Remove-Job $monitor -Force
    $code | Set-Content "results\$name-exit-code.txt"
    if ($name -eq 'smoke' -and $code -ne 0) { throw 'Smoke failed. Fix it before continuing. The console and JSON output are in results.' }
    if ($code -ne 0 -and $code -ne 99) { throw "k6 stopped with exit code $code. Inspect results\$name-console.txt." }
    if ($Test -eq 'all') { Start-Sleep -Seconds 15 }
}
Write-Host 'Finished. Run native/build-report.py from the project root to generate the Word report.'
