param([ValidateSet('smoke','load','stress','spike','endurance','all')][string]$Test='smoke',
      [ValidateSet('benchmark','limited')][string]$Profile='benchmark')
$ErrorActionPreference='Stop'
. "$PSScriptRoot\common.ps1"
Set-Location $ProjectRoot
Assert-Docker
if (-not (Get-Command k6 -ErrorAction SilentlyContinue)) { throw 'Install k6 and reopen PowerShell.' }
if ($env:VERIFY -and $env:VERIFY -ne '0') { throw 'Remove VERIFY; shortened runs cannot be Lab 3 measurements.' }
if ($env:LOAD_VUS -or $env:SPIKE_VUS -or $env:THINK_SECONDS) { throw 'Remove LOAD_VUS, SPIKE_VUS and THINK_SECONDS to use the same defaults as Lab 2.' }
$argsCompose=Get-ComposeArguments $Profile
$apiId=(& docker @argsCompose ps -q web) -join ''
if (-not $apiId) { throw 'Start the Compose stack first.' }
# Check effective resource settings match the declared comparison profile.
foreach ($service in @('web','postgres')) {
    $cid=(& docker @argsCompose ps -q $service) -join ''
    if (-not $cid) { throw "Missing container: $service" }
    $inspect=(& docker inspect $cid | ConvertFrom-Json)[0]
    if ($Profile -eq 'benchmark' -and ($inspect.HostConfig.NanoCpus -ne 0 -or $inspect.HostConfig.Memory -ne 0)) { throw "Restart benchmark profile; $service still has CPU/RAM caps." }
    if ($service -eq 'web' -and ($inspect.Config.Cmd -contains '--reload')) { throw 'Development reload must not be used for benchmarks.' }
}
if ((Invoke-RestMethod 'http://localhost:4567/health').status -ne 'ok') { throw 'API is not healthy.' }
$healthStatus=(& docker inspect --format '{{.State.Health.Status}}' $apiId) -join ''
if ($healthStatus -ne 'healthy') { throw 'Compose web is not healthy; a different API might own port 4567.' }
$outDir=Join-Path $ProjectRoot 'results\docker'
New-Item -ItemType Directory -Force $outDir | Out-Null
$meta=[ordered]@{
    started_at=(Get-Date).ToString('o'); api_url='http://localhost:4567';
    os=(Get-CimInstance Win32_OperatingSystem).Caption;
    cpu=(Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name) -join '; ';
    logical_processors=(Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors;
    ram_gb=[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,2);
    k6_version=(& k6 version) -join ' '
}
$meta | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $outDir 'run-meta.json')
& py -3.12 "$PSScriptRoot\record-environment.py" --output "$outDir\run-meta.json" --profile $Profile
if ($LASTEXITCODE -ne 0) { throw 'Cannot record container environment.' }
# k6 remains on Windows, just as in Lab 2; scripts are not changed.
$oldUrl=$env:API_URL; $oldResults=$env:RESULTS_DIR
$env:API_URL='http://localhost:4567'; $env:RESULTS_DIR=$outDir.Replace('\','/')
$names=if ($Test -eq 'all') { @('smoke','load','stress','spike','endurance') } else { @($Test) }
try {
    foreach ($name in $names) {
        $old=Get-ChildItem "$outDir\$name-*" -File -ErrorAction SilentlyContinue
        if ($old) {
            $backup=Join-Path $outDir "previous-$name-$(Get-Date -Format yyyyMMdd-HHmmss)"
            New-Item -ItemType Directory $backup | Out-Null
            $old | Move-Item -Destination $backup
        }
        Copy-Item "$outDir\run-meta.json" "$outDir\$name-environment.json"
        $ids=@(& docker @argsCompose ps -q)
        $monitor=Start-Job -ArgumentList (Join-Path $outDir "$name-docker-stats.jsonl"),($ids -join ',') -ScriptBlock {
            param($file,$idsText)
            $containerIds=$idsText.Split(',')
            while ($true) {
                $stamp=(Get-Date).ToUniversalTime().ToString('o')
                $lines=& docker stats --no-stream --format '{{json .}}' @containerIds
                foreach ($line in $lines) {
                    try { @{time=$stamp;stats=($line | ConvertFrom-Json)} | ConvertTo-Json -Compress -Depth 8 | Add-Content -Encoding UTF8 $file } catch { }
                }
                Start-Sleep -Seconds 5
            }
        }
        try {
            Set-Location (Join-Path $ProjectRoot 'tests\performance-tests')
            $ErrorActionPreference='Continue'
            & k6 run --no-usage-report --out "json=$($env:RESULTS_DIR)/$name-metrics.json.gz" "$name-test.js" 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath "$outDir\$name-console.txt"
            $code=$LASTEXITCODE
            $ErrorActionPreference='Stop'
        } finally {
            Set-Location $ProjectRoot
            Stop-Job $monitor; Remove-Job $monitor -Force
        }
        $code | Set-Content "$outDir\$name-exit-code.txt"
        if ($name -eq 'smoke' -and $code -ne 0) { throw 'Smoke failed; inspect results/docker/smoke-console.txt.' }
        if ($code -notin @(0,99)) { throw "k6 failed with exit code $code." }
        Write-Host "Save $name-screenshot.png in results/docker."
        if ($Test -eq 'all') { Start-Sleep -Seconds 15 }
    }
} finally {
    Set-Location $ProjectRoot
    if ($null -eq $oldUrl) { Remove-Item Env:API_URL -ErrorAction SilentlyContinue } else { $env:API_URL=$oldUrl }
    if ($null -eq $oldResults) { Remove-Item Env:RESULTS_DIR -ErrorAction SilentlyContinue } else { $env:RESULTS_DIR=$oldResults }
}
Write-Host 'Finished. Run py -3.12 container/build-report.py to compare with Lab 2.'
