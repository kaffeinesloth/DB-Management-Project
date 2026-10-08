# Library Management System — Project 02

Desktop application using Python, CustomTkinter, pyodbc, and SQL Server 2022
in Docker.

The database and basic dashboard are ready. Most application features are still
placeholders.

## 1. Install the requirements

Install on every computer:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Python 3.10 or newer
- Git, if the project is shared through Git

Start Docker Desktop and wait until its engine is running.

## 2. Setup on Windows

Open the project in VS Code and open a **PowerShell** terminal.

Create the local configuration:

```powershell
Copy-Item .env.example .env
```

Start SQL Server and create the database:

```powershell
docker compose up -d
```

Create the Python environment and install the packages:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run this command and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Start the application:

```powershell
python main.py
```

## 3. Setup on macOS

Open the project in VS Code and open its **zsh** terminal.

Create the local configuration:

```bash
cp .env.example .env
```

Start SQL Server and create the database:

```bash
docker compose up -d
```

Create the Python environment and install the packages:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Start the application:

```bash
python main.py
```

Apple Silicon Macs use Docker's x86-64 emulation. The required
`linux/amd64` setting is already included in `.env.example`.

## 4. Check the database

On Windows or macOS, run:

```bash
docker compose ps
docker compose logs database-init
```

Successful setup means:

- `sqlserver` is **healthy**.
- `database-init` shows **Exited (0)**.
- The log ends with `Database initialization completed successfully.`

`database-init` stops after finishing its work. This is normal. Only the
`sqlserver` container needs to remain running.

## 5. Shared database settings

Every group member uses the same local development settings:

```text
Server:       localhost
Port:         1433
Database:     LibraryManagement
App user:     library_app
App password: LibraryApp_2026!
Admin user:   sa
Admin pass:   LibraryAdmin_2026!
```

These are development credentials. Do not reuse them for personal accounts or
an internet-accessible database.

Each member runs a separate database on their own computer. Docker gives every
member the same structure and sample data; it does not create a shared online
server.

## 6. Start and stop later

From the project folder:

```bash
# Start the database
docker compose up -d

# Run the application after activating .venv
python main.py

# Stop the database while keeping its data
docker compose down
```

Do not use `docker compose down -v` unless you want to delete the local database
and its Docker backups.

## Project files

```text
main.py                    Starts the application
database.py                Shared database connection placeholder
dashboard.py               Main navigation
requirements.txt           Python packages
compose.yaml               Docker and SQL Server setup
.env.example               Shared team configuration

login/                     Login module
book_management/           Book module
reader_management/         Reader module
borrowing_and_returns/     Borrowing and return module
reports/                   Report module
backup_and_restore/        Backup and restore module
sql/                       Database scripts
docker/                    Database setup and maintenance scripts
```

Files ending in `_screen.py` contain interfaces. Files ending in `_actions.py`
contain validation and database operations.
