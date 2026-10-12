param([Parameter(Mandatory=$true)][string]$SourceProject)
$ErrorActionPreference='Stop'
. "$PSScriptRoot\common.ps1"
$source=Join-Path $SourceProject 'tests\performance-tests\results'
if (-not (Test-Path (Join-Path $source 'analysis.json'))) { throw 'First generate Lab 2 report to create analysis.json in that project.' }
$target=Join-Path $ProjectRoot 'results\baseline'
$backup=Join-Path $ProjectRoot "results\baseline-backup-$(Get-Date -Format yyyyMMdd-HHmmss)"
Copy-Item $target $backup -Recurse
Get-ChildItem $target -File | Remove-Item
Copy-Item "$source\*" $target -Recurse
& py -3.12 "$PSScriptRoot\write-provenance.py" --project $SourceProject --output "$target\provenance.json"
if ($LASTEXITCODE -ne 0) { throw 'Cannot record baseline provenance.' }
Write-Host 'Imported baseline; previous copy was backed up.'
