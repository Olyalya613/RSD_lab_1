$ErrorActionPreference = 'Stop'
$psqlCommand = Get-Command psql -ErrorAction SilentlyContinue
if ($psqlCommand) { $psql = $psqlCommand.Source }
else {
    $candidates = Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\psql.exe' -ErrorAction SilentlyContinue
    $psql = $candidates | Sort-Object { [int] $_.Directory.Parent.Name } -Descending | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $psql) { throw 'Install native PostgreSQL for Windows first. See START_HERE_UA.md.' }
$password = Read-Host 'Enter the postgres administrator password chosen during installation' -AsSecureString
$env:PGPASSWORD = (New-Object System.Net.NetworkCredential('', $password)).Password
try {
    & $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -f "$PSScriptRoot\init-db.sql"
    if ($LASTEXITCODE -ne 0) { throw 'Database initialization failed. Check password and PostgreSQL service.' }
} finally { Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue }
Write-Host 'Database traveler_lab2 is ready.'
