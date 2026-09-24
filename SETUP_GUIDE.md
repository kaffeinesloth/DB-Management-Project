# QLTV Login Demo Setup Guide

This is the simplest repeatable setup for another Windows laptop. SQL Server runs in Docker on port `14330`; the Tkinter application runs normally on Windows. The laptop's existing SQL Server installation is not changed or used by this Docker setup.

## What Docker creates

The Docker initialization creates:

- the `QLTV` database and all 11 project tables;
- employees Nguyễn Trọng Hoàng (`MANV` 1) and Trần Thị Mai (`MANV` 2);
- database roles `QLTV_MANAGER` and `QLTV_STAFF`;
- SQL logins `nguyen_trong_hoang` and `tran_thi_mai`;
- numeric database users `1` and `2` mapped to the employee IDs;
- the required role memberships and permissions.

Database data is stored in a named Docker volume and survives normal container stops and recreation.

## 1. Download branch v02

For a new clone:

```powershell
git clone -b v02 https://github.com/kaffeinesloth/DB-Management-Project.git
cd DB-Management-Project
```

For an existing clone:

```powershell
git fetch origin
git switch v02
git pull --ff-only origin v02
```

Run all remaining commands from the repository root.

## 2. Install the required software and packages

Open PowerShell and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup_windows.ps1 -IncludeDocker
```

The execution-policy change applies only to the current PowerShell window.

The script checks and installs missing components:

- Python 3.12;
- Python packages from `official_app\requirements.txt`;
- Microsoft ODBC Driver 18 for SQL Server;
- Docker Desktop when `-IncludeDocker` is supplied.

If Docker Desktop is newly installed, restart Windows if requested. Start Docker Desktop and wait until it reports that the engine is running. Then rerun:

```powershell
.\setup_windows.ps1 -IncludeDocker
```

Docker Desktop uses WSL 2. If Docker reports that WSL is missing or outdated, open an Administrator PowerShell window and run:

```powershell
wsl --install
wsl --update
```

Restart Windows afterward if requested.

## 3. Create the private environment file

Create `.env` from the provided template:

```powershell
Copy-Item .env.example .env
notepad .env
```

Replace every `CHANGE_ME` password:

```dotenv
SQL_PORT=14330
MSSQL_SA_PASSWORD=replace_with_a_strong_admin_password
QLTV_MANAGER_PASSWORD=replace_with_a_strong_manager_password
QLTV_STAFF_PASSWORD=replace_with_a_strong_staff_password
```

Each password must contain 8-128 characters and should include uppercase letters, lowercase letters, numbers, and symbols. To avoid PowerShell, Compose, shell, and SQL quoting problems, use only letters, numbers, and these symbols: `_ ! @ % + = . , : -`.

The `.env` file is ignored by Git. Never commit it or send it to another person.

## 4. Start and initialize the Docker database

Run:

```powershell
.\start_docker_database.ps1
```

The first run downloads the official SQL Server 2022 image, starts SQL Server, waits for it to become healthy, and initializes the complete login demonstration. The image download can take several minutes.

The script is safe to run again. If the named volume is already initialized, it verifies the marker and makes no database changes.

Equivalent Docker Compose commands are:

```powershell
docker compose up -d --wait sqlserver
docker compose run --rm db-init
```

Check container status:

```powershell
docker compose ps
```

View SQL Server logs:

```powershell
docker compose logs --tail 100 sqlserver
```

## 5. Run the application

Run:

```powershell
.\run_docker_app.ps1
```

That script reads `SQL_PORT` from `.env`, sets the application server to `localhost,14330`, and launches:

```powershell
python -B official_app\main.py
```

### Manager login

```text
Login Name: nguyen_trong_hoang
Password: the QLTV_MANAGER_PASSWORD value from .env
Employee: Nguyễn Trọng Hoàng
Database User: 1
Role: QLTV_MANAGER
```

### Staff login

```text
Login Name: tran_thi_mai
Password: the QLTV_STAFF_PASSWORD value from .env
Employee: Trần Thị Mai
Database User: 2
Role: QLTV_STAFF
```

## 6. Connect with SSMS

SSMS remains installed on Windows and connects to the container over the mapped port.

Use:

```text
Server name: localhost,14330
Authentication: SQL Server Authentication
Trust server certificate: enabled
```

Log in with `sa` and `MSSQL_SA_PASSWORD`, or use either application login above. The laptop's normal SQL Server instance remains separate from this container.

## Everyday Docker commands

Stop the containers without deleting database data:

```powershell
docker compose down
```

Start the database again and verify initialization:

```powershell
.\start_docker_database.ps1
```

Show running containers:

```powershell
docker compose ps
```

Follow live SQL Server logs:

```powershell
docker compose logs -f sqlserver
```

Download a newer SQL Server 2022 image and recreate the container while preserving the volume:

```powershell
docker compose pull
docker compose up -d --wait sqlserver
```

## Completely reset the Docker database

Warning: the following command permanently deletes the Docker `QLTV` database and all data stored in its volume:

```powershell
docker compose down -v
```

Recreate everything afterward:

```powershell
.\start_docker_database.ps1
```

Do not use `-v` when you want to preserve database data.

## Password changes after initialization

Changing a password in `.env` does not automatically change an existing SQL login because the initialized volume is preserved.

For a disposable classroom database, the simplest option is:

```powershell
docker compose down -v
.\start_docker_database.ps1
```

This deletes and rebuilds the Docker database using the new `.env` passwords.

## Troubleshooting

### Docker Desktop is not running

Start Docker Desktop from the Windows Start menu and wait for the engine to become ready. Then rerun:

```powershell
.\start_docker_database.ps1
```

### Port 14330 is already in use

Edit `.env` and choose another unused port:

```dotenv
SQL_PORT=14331
```

Then run the startup and application scripts again. `run_docker_app.ps1` reads the new port automatically.

### The initialization rejects CHANGE_ME passwords

Open `.env` and replace all placeholder values with strong passwords, then rerun the startup script.

### QLTV exists without the Docker marker

This means initialization stopped partway through or the volume contains an unrelated database. For a disposable setup, reset it:

```powershell
docker compose down -v
.\start_docker_database.ps1
```

### Login failed with SQL Server error 18456

Confirm that the password matches `.env`. If `.env` was changed after the first initialization, reset the volume or alter the SQL login password manually.

### No module named pyodbc

Run:

```powershell
.\setup_windows.ps1 -IncludeDocker
```

### View initialization output again

Run the idempotent initialization service:

```powershell
docker compose run --rm db-init
```
