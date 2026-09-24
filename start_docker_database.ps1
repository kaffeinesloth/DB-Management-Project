[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $PSScriptRoot

if (-not (Test-Path -LiteralPath ".env" -PathType Leaf)) {
    throw "Missing .env. Run 'Copy-Item .env.example .env', edit all passwords, then retry."
}

if ($null -eq (Get-Command "docker.exe" -ErrorAction SilentlyContinue)) {
    throw "Docker is not installed. Run '.\setup_windows.ps1 -IncludeDocker' first."
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is not running. Start Docker Desktop and wait until it is ready."
}

Write-Host "Starting SQL Server container..." -ForegroundColor Cyan
docker compose up -d --wait sqlserver
if ($LASTEXITCODE -ne 0) {
    throw "SQL Server container failed to become healthy. Run 'docker compose logs sqlserver'."
}

Write-Host "Initializing or verifying QLTV..." -ForegroundColor Cyan
docker compose run --rm db-init
if ($LASTEXITCODE -ne 0) {
    throw "Database initialization failed. Review the output above."
}

$port = 14330
$portLine = Get-Content -LiteralPath ".env" | Where-Object { $_ -match '^\s*SQL_PORT\s*=\s*\d+\s*$' } | Select-Object -Last 1
if ($portLine -match '=\s*(\d+)\s*$') {
    $port = [int]$Matches[1]
}

Write-Host "`nDocker database is ready." -ForegroundColor Green
Write-Host "SQL Server address: localhost,$port"
Write-Host "Next command: .\run_docker_app.ps1"

