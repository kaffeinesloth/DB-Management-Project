[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $PSScriptRoot

if (-not (Test-Path -LiteralPath ".env" -PathType Leaf)) {
    throw "Missing .env. Complete the Docker setup in SETUP_GUIDE.md first."
}

$port = 14330
$portLine = Get-Content -LiteralPath ".env" | Where-Object { $_ -match '^\s*SQL_PORT\s*=\s*\d+\s*$' } | Select-Object -Last 1
if ($portLine -match '=\s*(\d+)\s*$') {
    $port = [int]$Matches[1]
}

$env:QLTV_SQL_SERVER = "localhost,$port"
Write-Host "Starting the Tkinter app against $env:QLTV_SQL_SERVER..." -ForegroundColor Cyan
python -B official_app\main.py

