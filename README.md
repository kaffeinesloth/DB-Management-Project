# Library Management System — Project 02

Project 02 is a desktop library-management application built with Python,
CustomTkinter, SQL Server 2022, and Docker Compose. Docker supplies an isolated,
reproducible database; the Python program connects to it through Microsoft ODBC
Driver 18.

## Current status

- The Docker database setup is complete and rerunnable.
- The physical schema contains exactly the 11 tables required by the teacher.
- Database constraints, triggers, reporting views, permissions, sample data,
  contract verification, backup/restore, and smoke tests are available.
- The desktop program includes role-based login, book, reader, loan/return,
  reporting, account-administration, backup/restore, and reader catalogue
  screens.
- Employees authenticate with real SQL Server logins and receive a `QUANLY` or
  `THUTHU` dashboard. The shared `docgia` login receives read-only catalogue
  access.

## Quick start

After installing the prerequisites for your operating system:

1. Copy `.env.example` to `.env`.
2. Start Docker Desktop.
3. Run `docker compose up -d` from the project root.
4. Wait until `sqlserver` is healthy and `database-init` has exited with code 0.
5. Create the Python virtual environment and install `requirements.txt`.
6. Run `python main.py` on Windows or `python3 main.py` on macOS.

The first Docker startup downloads SQL Server and can take several minutes.
Later runs reuse the stored database volume and start much faster.

## 1. Prerequisites

Install on every team computer:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with the
  `docker compose` command
- Python 3.10 or newer
- Git
- Microsoft ODBC Driver 18 for SQL Server (required by `pyodbc`)

Windows users should install the x64 or Arm64 build of
[Microsoft ODBC Driver 18](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
that matches their Python installation. SSMS is optional and is available only
on Windows.

The macOS commands for installing the driver and its `unixODBC` dependency are
included in the macOS setup section below.

Start Docker Desktop and wait until its engine is running before using any
Docker command below. You do **not** need to install a second native SQL Server
instance: the project database runs inside Docker.

## 2. First setup on Windows

Install Docker Desktop, Git, Python 3.10+, and ODBC Driver 18. Open the cloned
project folder in VS Code and use a **PowerShell** terminal:

```powershell
Copy-Item .env.example .env
docker compose config --quiet
docker compose up -d
docker compose ps -a

python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import pyodbc; print(pyodbc.drivers())"
python main.py
```

Before starting `main.py`, confirm that `docker compose ps -a` shows:

- `sqlserver` as `Up ... (healthy)`;
- `backup-volume-init` as `Exited (0)`; and
- `database-init` as `Exited (0)`.

If PowerShell blocks virtual-environment activation, allow scripts for only the
current terminal and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

For later runs, start Docker Desktop and use:

```powershell
docker compose up -d
.venv\Scripts\Activate.ps1
python main.py
```

The helper files in `docker/*.sh` require Bash. On Windows, run those specific
scripts from Git Bash or WSL while Docker Desktop is running. Normal setup and
application startup work entirely from PowerShell.

## 3. First setup on macOS

Install Docker Desktop, Git, Python 3.10+, Homebrew, and ODBC Driver 18. Then
open the cloned project folder in Terminal or VS Code and use **zsh**:

```bash
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew trust microsoft/mssql-release
brew update
HOMEBREW_ACCEPT_EULA=Y brew install msodbcsql18 mssql-tools18
```

On Homebrew versions older than 6, `brew trust` may not exist and can be
skipped. Set up the project:

```bash
cp .env.example .env
docker compose config --quiet
docker compose up -d
docker compose ps -a

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import pyodbc; print(pyodbc.drivers())"
python3 main.py
```

The driver check must include `ODBC Driver 18 for SQL Server`. For later runs:

```bash
docker compose up -d
source .venv/bin/activate
python3 main.py
```

SQL Server's Linux container is x86-64. The shared `DOCKER_PLATFORM=linux/amd64`
setting enables Docker emulation on Apple Silicon; initial startup can therefore
take longer than on an x86-64 computer. SSMS does not run on macOS; use the
application, `sqlcmd`, or another SQL client when manual database inspection is
needed.

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
SQL Server image: SQL Server 2022 CU28 on Ubuntu 22.04
Host/port:        127.0.0.1:1433 (local machine only)
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
port and may be changed locally if port 1433 is already occupied. Because
Docker Compose reads `.env` but Python does not load it automatically, also set
the same port in the terminal before launching the application:

```powershell
# Windows PowerShell example
$env:MSSQL_PORT = "14333"
python main.py
```

```bash
# macOS example
export MSSQL_PORT=14333
python3 main.py
```

Alternatively set `DB_HOST` directly, for example
`127.0.0.1,14333`. With the standard port, no extra environment variable is
needed; the program defaults to `127.0.0.1,1433` and database
`LibraryManagement`.

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

Closing the Python window does not stop SQL Server. Use `docker compose down`
when finished, or leave the container running for the next development session.
Database contents survive `docker compose down` because they are stored in a
named Docker volume.

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
database.py                Shared pyodbc authentication and connection layer
requirements.txt           Exact Python dependency versions
compose.yaml               Reproducible SQL Server services and volumes
.env.example               Shared local-development configuration template

login/                     Login UI and authentication actions
account_management/        Employee SQL-account administration
catalog_search/            Read-only reader catalogue search
book_management/           Book-management UI and actions
reader_management/         Reader-management UI and actions
borrowing_and_returns/     Loan/return UI and actions
reports/                   Reports, statistics, and printing
backup_and_restore/        Backup/restore UI and actions
sql/                       Schema, data, permissions, checks, and maintenance SQL
docker/                    Initialization, smoke-test, and maintenance helpers
Additional Info/           Teacher specification and lesson references
```

## 10. Login and SSMS classroom demo

Start the database with `docker compose up -d`, then run `python main.py`.
The login form uses SQL Server Authentication, not a hard-coded Python user
list. The classroom accounts all use password `123456`:

| Login | Database user | Role | Dashboard access |
|---|---:|---|---|
| `admin` | `3` (Lê Mai) | `QUANLY` | All modules, including account administration |
| `nv_huong` | `1` (Nguyễn Hương) | `THUTHU` | Books, readers, loans, and reports |
| `nv_long` | `2` (Trần Long) | `THUTHU` | Books, readers, loans, and reports |
| `nv_nam` | `4` (Phạm Nam) | `THUTHU` | Books, readers, loans, and reports |
| `docgia` | Shared reader identity | `DOCGIA` | Read-only book catalogue search |

Individual rows in the `DOCGIA` table are library-card records, not individual
SQL accounts. The teacher-required `docgia` login is one shared, read-only
identity for students to search the catalogue. New employee logins can still be
created only for valid `NHANVIEN` rows.

For the SSMS part of the presentation on Windows, connect to
`127.0.0.1,1433` using **SQL Server Authentication** and one of those accounts.
Do not select an unrelated `localhost` Windows-authentication history entry.
Set **Database name** to `LibraryManagement` and enable **Trust server
certificate**. Open and execute
`sql/06_teacher_login_demo.sql`; it displays the server logins, numbered
database users, role memberships, and the identity of the currently connected
account.

### Account-management demo

Sign in as `admin`, then open **Quản Lý Tài Khoản**. The table shows every
valid `NHANVIEN` record and clearly marks whether it already has a SQL account.
Select an employee marked **Chưa có**, enter a login and a password of at least
six characters, choose `THUTHU` or `QUANLY`, and click **Tạo tài khoản**.

For deletion, select an employee marked **Đã có** and click **Xóa tài khoản**.
The active account cannot delete itself; this is enforced both in the UI and
inside SQL Server. Duplicate employee accounts and duplicate server login names
are also rejected by the stored procedure.

The create/delete procedures are certificate-signed. Managers receive execute
permission on those procedures but do not receive general server-wide login
administration permission.

To add a completely new employee, click **Thêm nhân viên + tài khoản**. Enter
the employee profile, login, password, and role in the combined form. Saving is
atomic: the program creates both the `NHANVIEN` row and SQL Server account, or
rolls back both if any validation or database step fails.

Normal initialization runs these scripts in order:

1. `01_create_tables.sql` — 11 tables, constraints, triggers, and report views.
2. `02_sample_data.sql` — rerunnable shared sample data when
   `LOAD_SAMPLE_DATA=true`.
3. `03_login_and_permissions.sql` — application login, database user, and role.
4. `05_verify_database.sql` — fail-fast schema and permission contract checks.

`99_smoke_test.sql` is run only by `docker/smoke-test.sh`.
`04_backup_and_restore.sql` is run only by
`docker/database-maintenance.sh`.

## 11. Run automated checks

Run the Python unit tests from an activated virtual environment:

```bash
python -m unittest discover -s tests -v
```

Run the database transaction and permission smoke test from Bash (Terminal on
macOS, Git Bash or WSL on Windows):

```bash
./docker/smoke-test.sh
```

The database smoke test rolls back its temporary records. A successful run ends
with `ALL_DATABASE_SMOKE_TESTS_PASSED`.

## 12. Troubleshooting

### SSMS cannot connect

- Confirm Docker Desktop is running and `docker compose ps` reports
  `sqlserver` as healthy.
- Use server name `127.0.0.1,1433`, not plain `localhost`.
- Select **SQL Server Authentication**, not Windows Authentication.
- Enable **Trust server certificate**.
- If SSMS shows a Named Pipes error for `localhost`, it is trying an unrelated
  local Windows SQL Server entry rather than this Docker project.

SSMS is Windows-only. It is optional for running the application and is mainly
useful for inspecting the database and demonstrating permissions.

### Port 1433 is already in use

Check the owner of the port:

```powershell
# Windows
Get-NetTCPConnection -LocalPort 1433 -ErrorAction SilentlyContinue
```

```bash
# macOS
lsof -nP -iTCP:1433 -sTCP:LISTEN
```

Either stop the conflicting local database or change `MSSQL_PORT` in `.env`.
If the port is changed, export the same value (or `DB_HOST`) before starting
Python as explained in **Shared configuration**.

### Python reports that no ODBC driver is available

Verify the driver from the activated environment:

```bash
python -c "import pyodbc; print(pyodbc.drivers())"
```

Install Microsoft ODBC Driver 18 if it is absent. On macOS, also ensure the
terminal, Python, unixODBC, and ODBC driver use compatible CPU architectures.

### The database is running but tables or logins are missing

Inspect the initializer output:

```bash
docker compose logs database-init
```

If initialization failed, fix the reported error and run
`docker compose up -d` again. Only use `docker compose down -v` when you
intentionally want to delete the local database and rebuild it from the SQL
scripts.

### The GUI does not open on macOS

Check that Python includes Tk support:

```bash
python3 -m tkinter
```

If this command fails, install a Python distribution with Tk support, recreate
`.venv`, and reinstall `requirements.txt`.

## Reference links

- [Docker Desktop installation](https://docs.docker.com/desktop/)
- [Microsoft ODBC Driver 18 downloads](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
- [Microsoft ODBC Driver 18 on macOS](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/install-microsoft-odbc-driver-for-sql-server-macos)
- [SQL Server Management Studio](https://learn.microsoft.com/en-us/ssms/faq)
