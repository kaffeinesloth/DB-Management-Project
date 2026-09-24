[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = $PSScriptRoot
$requirementsPath = Join-Path $repoRoot "official_app\requirements.txt"
$appPath = Join-Path $repoRoot "official_app"

function Write-Step {
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Refresh-ProcessPath {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

function Resolve-PythonExecutable {
    foreach ($commandName in @("python.exe", "python3.exe")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            try {
                $resolved = & $command.Source -c "import sys; print(sys.executable)" 2>$null
                if ($LASTEXITCODE -eq 0 -and $resolved -and (Test-Path -LiteralPath $resolved)) {
                    return (Resolve-Path -LiteralPath $resolved).Path
                }
            }
            catch {
                # Continue to the next discovery method.
            }
        }
    }

    $launcher = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if ($null -ne $launcher) {
        try {
            $resolved = & $launcher.Source -3 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $resolved -and (Test-Path -LiteralPath $resolved)) {
                return (Resolve-Path -LiteralPath $resolved).Path
            }
        }
        catch {
            # Python launcher is present but has no usable Python 3 runtime.
        }
    }

    return $null
}

function Require-Winget {
    $winget = Get-Command "winget.exe" -ErrorAction SilentlyContinue
    if ($null -eq $winget) {
        throw "Windows Package Manager (winget) is required to install missing system packages. Install or update App Installer from Microsoft Store, then rerun this script."
    }
    return $winget.Source
}

function Install-WingetPackage {
    param(
        [Parameter(Mandatory)][string]$PackageId,
        [Parameter(Mandatory)][string]$DisplayName
    )

    $winget = Require-Winget
    Write-Host "$DisplayName is missing. Installing $PackageId..." -ForegroundColor Yellow
    & $winget install `
        --id $PackageId `
        --exact `
        --silent `
        --accept-package-agreements `
        --accept-source-agreements

    if ($LASTEXITCODE -ne 0) {
        throw "winget could not install $DisplayName (exit code $LASTEXITCODE)."
    }
    Refresh-ProcessPath
}

if (-not (Test-Path -LiteralPath $requirementsPath -PathType Leaf)) {
    throw "Cannot find $requirementsPath. Run this script from a complete checkout of branch v02."
}

Write-Step "Checking Python"
$pythonExe = Resolve-PythonExecutable
if ($null -eq $pythonExe) {
    Install-WingetPackage -PackageId "Python.Python.3.12" -DisplayName "Python 3.12"
    $pythonExe = Resolve-PythonExecutable
}

if ($null -eq $pythonExe) {
    throw "Python was installed but is not visible in this PowerShell session. Close PowerShell, open it again, and rerun setup_windows.ps1."
}

& $pythonExe -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.10 or newer is required. Found: $(& $pythonExe --version)"
}
Write-Host "Using $(& $pythonExe --version) at $pythonExe" -ForegroundColor Green

Write-Step "Installing Python requirements"
& $pythonExe -m pip install --disable-pip-version-check -r $requirementsPath
if ($LASTEXITCODE -ne 0) {
    throw "Python package installation failed."
}

Write-Step "Checking Microsoft ODBC Driver 18 for SQL Server"
& $pythonExe -c "import pyodbc; raise SystemExit(0 if 'ODBC Driver 18 for SQL Server' in pyodbc.drivers() else 1)"
if ($LASTEXITCODE -ne 0) {
    Install-WingetPackage `
        -PackageId "Microsoft.msodbcsql.18" `
        -DisplayName "Microsoft ODBC Driver 18 for SQL Server"
}

& $pythonExe -c "import pyodbc; raise SystemExit(0 if 'ODBC Driver 18 for SQL Server' in pyodbc.drivers() else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "ODBC Driver 18 is still unavailable. Restart Windows if the installer requested it, then rerun this script."
}

Write-Step "Verifying application imports"
Push-Location $appPath
try {
    & $pythonExe -B -c "import tkinter, pyodbc; import config, database.connection, database.security, models.session, ui.login_window, ui.main_window, main; print('Application import check passed.')"
    if ($LASTEXITCODE -ne 0) {
        throw "Application import verification failed."
    }
}
finally {
    Pop-Location
}

Write-Host "`nPackage setup completed successfully." -ForegroundColor Green
Write-Host "Next: follow SETUP_GUIDE.md to configure SQL Server, create QLTV, and create the demo accounts."
Write-Host "This script did not change SQL Server or store any database passwords."

