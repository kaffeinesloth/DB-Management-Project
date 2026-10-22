# Library Management System — Project 02

Project 02 is the shared foundation for the team's final project. It contains a
verified SQL Server database baseline and a Python/CustomTkinter interface
scaffold.

## Current status

- The Docker database setup is complete and rerunnable.
- The physical schema contains exactly the 11 tables required by the teacher.
- Database constraints, triggers, reporting views, permissions, sample data,
  contract verification, backup/restore, and smoke tests are available.
- The desktop program opens a navigation dashboard with placeholder screens.
- Login, CRUD operations, database connections, reports, and backup controls
  are **not implemented in the Python interface yet**. Disabled buttons and
  empty `*_actions.py` files are intentional module boundaries for team work.

No Python screen currently changes the database. `database.py` only declares a
future shared `pyodbc` connection.

## 1. Prerequisites

Install on every team computer:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with the
  `docker compose` command
- Python 3.10 or newer
- Git
- Microsoft ODBC Driver 18 for SQL Server, required when Python database work
  begins and when importing `database.py`

Windows users can download
[Microsoft ODBC Driver 18](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server).

On macOS, install the driver and its `unixODBC` dependency through Microsoft's
Homebrew repository:

```bash
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew trust microsoft/mssql-release
brew update
HOMEBREW_ACCEPT_EULA=Y brew install msodbcsql18 mssql-tools18
```

The `brew trust` command is required by Homebrew 6 and is safe to omit on older
Homebrew versions that do not provide it. See Microsoft's
[macOS installation guide](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/install-microsoft-odbc-driver-sql-server-macos).

Start Docker Desktop and wait until its engine is running before using any
Docker command below.

## 2. First setup on Windows

Open the project folder in VS Code and use a **PowerShell** terminal:

```powershell
Copy-Item .env.example .env
docker compose config --quiet
docker compose up -d

python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

If PowerShell blocks virtual-environment activation, allow scripts for only the
current terminal and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

The helper files in `docker/*.sh` require Bash. On Windows, run them from Git
Bash or WSL while Docker Desktop is running.

## 3. First setup on macOS

Open the project folder in VS Code and use a **zsh** terminal:

```bash
cp .env.example .env
docker compose config --quiet
docker compose up -d

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

SQL Server's Linux container is x86-64. The shared `DOCKER_PLATFORM=linux/amd64`
setting enables Docker emulation on Apple Silicon; initial startup can therefore
take longer than on an x86-64 computer.

## 4. Verify the database

Initialization runs automatically after SQL Server becomes healthy:

```bash
docker compose ps -a
docker compose logs database-init
```

Successful setup means:

- `sqlserver` is `healthy`.
- `backup-volume-init` and `database-init` show `Exited (0)`.
- the initialization log contains `DATABASE_CONTRACT_OK` with 11 tables and
  ends with `Database initialization completed successfully.`

`database-init` is a one-time setup container, so it should stop after success.
Only `sqlserver` remains running.

Run the transactional behavior checks from Bash:

```bash
./docker/smoke-test.sh
```

The smoke test reads the same `.env` credentials used by Docker Compose and
rolls back all test records. Success ends with
`ALL_DATABASE_SMOKE_TESTS_PASSED`.

## 5. Shared configuration

Copy `.env.example` to `.env`; do not commit `.env`. The checked-in baseline is:

```text
SQL Server image: SQL Server 2022 CU27 on Ubuntu 22.04
Host/port:        localhost:1433
Database:         LibraryManagement
Application user: library_app
Application pass: LibraryApp_2026!
Administrator:    sa
Administrator pass: LibraryAdmin_2026!
Sample data:      enabled
Timezone:         Asia/Ho_Chi_Minh
```

The image is pinned through `MSSQL_IMAGE`; this prevents team members from
silently receiving different SQL Server builds. Coordinate changes to the
image, credentials, sample-data setting, and timezone. `MSSQL_PORT` is the host
port and may be changed locally if port 1433 is already occupied.

These credentials are only for local classroom development. Never expose this
SQL Server port to the internet or reuse the passwords elsewhere. Each team
member runs an independent local database; Docker does not create a shared
online server.

Python packages are exactly pinned in `requirements.txt` so each member installs
the same tested versions. Update those pins only as a coordinated team change.

## 6. Everyday Docker commands

Run commands from the Project 02 folder:

```bash
# Start or recreate services without deleting stored data
docker compose up -d

# View all running and completed Project 02 containers
docker compose ps -a

# Inspect initialization output
docker compose logs database-init

# Stop and remove containers while keeping database and backup volumes
docker compose down
```

Do not use `docker compose down -v` for routine shutdown. The `-v` option
permanently removes the local database and every backup stored in its Docker
backup volume.

After an intentional change to the shared SQL baseline, recreate the local
development database once so an old volume cannot hide schema drift:

```bash
docker compose down -v
docker compose up -d
docker compose logs database-init
```

## 7. Backup and restore

The maintenance helper operates on `.bak` files in the Docker backup volume:

```bash
# Create a timestamped backup
./docker/database-maintenance.sh backup

# Create a named backup
./docker/database-maintenance.sh backup team-baseline.bak

# List backups
./docker/database-maintenance.sh list

# Verify a backup without restoring it
./docker/database-maintenance.sh verify team-baseline.bak

# Restore and replace the current LibraryManagement database
CONFIRM_RESTORE=LibraryManagement \
  ./docker/database-maintenance.sh restore team-baseline.bak
```

Restore disconnects current database users and replaces the database. Backups
inside the Docker volume are deleted by `docker compose down -v`.

## 8. Teacher-document compatibility

The source document contains internal type contradictions. Project 02 follows
the detailed data dictionary and applies these consistency decisions:

- Vietnamese descriptive text uses `NVARCHAR` at the documented character
  length.
- `ISBN` is `CHAR(10)` in every referencing table.
- `MASACH` is `VARCHAR(10)` in both `SACH` and `CT_PHIEUMUON`; the document
  lists 10 and 20 respectively, which would make the foreign key inconsistent.
- `DOCGIA.DIACHI` is `NVARCHAR(100)` and `DOCGIA.DIENTHOAI` is `VARCHAR(11)`,
  matching the equivalent employee fields because the document omits them.
- `ISBN.NHAXB` and `NGANTU.KE` remain descriptive text because the required
  11-table model defines no publisher or shelf table to reference.
- `SOCMND` is unique among active cards only, allowing a lost card to receive a
  new `MADG` while preserving its inactive-card history.

The database enforces active reader cards, at most three unreturned books per
reader, valid book condition and availability, synchronized loan status, a
30-day loan period, and a 500 VND daily overdue fine in reporting views. No
publisher, shelf, fine, or notification table was added.

## 9. Project layout

```text
main.py                    Application entry point
dashboard.py               Navigation and screen switching
database.py                Future shared pyodbc connection placeholder
requirements.txt           Exact Python dependency versions
compose.yaml               Reproducible SQL Server services and volumes
.env.example               Shared local-development configuration template

login/                     Login UI and future actions
book_management/           Book UI and future actions
reader_management/         Reader UI and future actions
borrowing_and_returns/     Loan/return UI and future actions
reports/                   Report UI and future actions
backup_and_restore/        Backup/restore UI and future actions
sql/                       Schema, data, permissions, checks, and maintenance SQL
docker/                    Initialization, smoke-test, and maintenance helpers
Additional Info/           Teacher specification and lesson references
```

Normal initialization runs these scripts in order:

1. `01_create_tables.sql` — 11 tables, constraints, triggers, and report views.
2. `02_sample_data.sql` — rerunnable shared sample data when
   `LOAD_SAMPLE_DATA=true`.
3. `03_login_and_permissions.sql` — application login, database user, and role.
4. `05_verify_database.sql` — fail-fast schema and permission contract checks.

`99_smoke_test.sql` is run only by `docker/smoke-test.sh`.
`04_backup_and_restore.sql` is run only by
`docker/database-maintenance.sh`.
