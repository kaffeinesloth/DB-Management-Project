#!/usr/bin/env bash
set -euo pipefail

: "${MSSQL_SA_PASSWORD:?MSSQL_SA_PASSWORD is required}"
: "${QLTV_MANAGER_PASSWORD:?QLTV_MANAGER_PASSWORD is required}"
: "${QLTV_STAFF_PASSWORD:?QLTV_STAFF_PASSWORD is required}"

for variable_name in MSSQL_SA_PASSWORD QLTV_MANAGER_PASSWORD QLTV_STAFF_PASSWORD; do
    value="${!variable_name}"
    if [[ "$value" == *"CHANGE_ME"* ]]; then
        echo "ERROR: Replace every CHANGE_ME password in .env before initialization." >&2
        exit 2
    fi
    if (( ${#value} < 8 || ${#value} > 128 )); then
        echo "ERROR: $variable_name must contain 8-128 characters." >&2
        exit 2
    fi
    if [[ ! "$value" =~ ^[A-Za-z0-9_!@%+=.,:-]+$ ]]; then
        echo "ERROR: $variable_name contains an unsupported character." >&2
        echo "Use only letters, numbers, and these symbols: _ ! @ % + = . , : -" >&2
        exit 2
    fi
done

if [[ -x /opt/mssql-tools18/bin/sqlcmd ]]; then
    SQLCMD=/opt/mssql-tools18/bin/sqlcmd
elif [[ -x /opt/mssql-tools/bin/sqlcmd ]]; then
    SQLCMD=/opt/mssql-tools/bin/sqlcmd
else
    echo "ERROR: sqlcmd was not found in the SQL Server image." >&2
    exit 3
fi

export SQLCMDPASSWORD="$MSSQL_SA_PASSWORD"
SQLCMD_BASE=("$SQLCMD" -S sqlserver -U sa -C -b)

echo "Waiting for SQL Server..."
ready=0
for _ in $(seq 1 60); do
    if "${SQLCMD_BASE[@]}" -Q "SELECT 1" -o /dev/null >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 2
done

if [[ "$ready" -ne 1 ]]; then
    echo "ERROR: SQL Server did not become ready within 120 seconds." >&2
    exit 4
fi

database_exists=$("${SQLCMD_BASE[@]}" -h -1 -W -Q \
    "SET NOCOUNT ON; SELECT CASE WHEN DB_ID(N'QLTV') IS NULL THEN 0 ELSE 1 END;" \
    | tr -d '\r[:space:]')

if [[ "$database_exists" == "1" ]]; then
    setup_complete=$("${SQLCMD_BASE[@]}" -h -1 -W -Q \
        "SET NOCOUNT ON; SELECT COUNT(*) FROM QLTV.sys.extended_properties WHERE class = 0 AND name = N'QLTV_DOCKER_SETUP_VERSION' AND CONVERT(nvarchar(128), value) = N'1';" \
        | tr -d '\r[:space:]')

    if [[ "$setup_complete" == "1" ]]; then
        echo "QLTV Docker database is already initialized; no changes were made."
        exit 0
    fi

    echo "ERROR: QLTV exists without the Docker initialization marker." >&2
    echo "For a disposable Docker database, run: docker compose down -v" >&2
    echo "Then run the startup command again. The -v option deletes Docker database data." >&2
    exit 5
fi

echo "Creating the QLTV database and 11 tables..."
"${SQLCMD_BASE[@]}" -i /setup/00_schema.sql

echo "Adding the two employee records..."
"${SQLCMD_BASE[@]}" -i /setup/01_seed_employees.sql

echo "Creating application roles and permissions..."
"${SQLCMD_BASE[@]}" -i /setup/02_security_setup.sql

echo "Creating SQL logins, database users, and role memberships..."
"${SQLCMD_BASE[@]}" \
    -v MANAGER_PASSWORD="$QLTV_MANAGER_PASSWORD" STAFF_PASSWORD="$QLTV_STAFF_PASSWORD" \
    -i /setup/03_create_accounts.sql

echo "Recording successful Docker initialization..."
"${SQLCMD_BASE[@]}" -i /setup/04_mark_initialized.sql

echo "Verifying the completed security mapping..."
"${SQLCMD_BASE[@]}" -W -Q \
    "USE QLTV; SELECT u.name AS database_user, r.name AS database_role FROM sys.database_role_members rm JOIN sys.database_principals r ON r.principal_id = rm.role_principal_id JOIN sys.database_principals u ON u.principal_id = rm.member_principal_id WHERE r.name IN (N'QLTV_MANAGER', N'QLTV_STAFF') ORDER BY u.name;"

echo "QLTV Docker initialization completed successfully."
