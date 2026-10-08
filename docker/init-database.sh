#!/usr/bin/env bash

set -Eeuo pipefail

database_host="${DB_HOST:-sqlserver}"
load_sample_data="${LOAD_SAMPLE_DATA:-true}"
app_db_user="${APP_DB_USER:-}"
app_db_password="${APP_DB_PASSWORD:-}"

if [[ ! "${app_db_user}" =~ ^[A-Za-z][A-Za-z0-9_]{0,127}$ ]]; then
    echo "APP_DB_USER must start with a letter and contain only letters, numbers, and underscores." >&2
    exit 1
fi

if [[ ${#app_db_password} -lt 8 ]]; then
    echo "APP_DB_PASSWORD must contain at least 8 characters." >&2
    exit 1
fi

if [[ "${app_db_password}" == *'$('* || "${app_db_password}" == *$'\n'* || "${app_db_password}" == *$'\r'* ]]; then
    echo "APP_DB_PASSWORD must not contain \$(, carriage returns, or newlines." >&2
    exit 1
fi

# Escape apostrophes before sqlcmd substitutes the password into an N'...'
# T-SQL string literal. The password itself is never printed.
app_db_password_sql=${app_db_password//\'/\'\'}

if [[ -x /opt/mssql-tools18/bin/sqlcmd ]]; then
    sqlcmd=/opt/mssql-tools18/bin/sqlcmd
elif [[ -x /opt/mssql-tools/bin/sqlcmd ]]; then
    sqlcmd=/opt/mssql-tools/bin/sqlcmd
else
    echo "sqlcmd was not found in the SQL Server image." >&2
    exit 1
fi

echo "Waiting for SQL Server to accept connections..."
for attempt in {1..60}; do
    if "${sqlcmd}" -S "${database_host}" -U sa -C -Q "SELECT 1" >/dev/null 2>&1; then
        break
    fi

    if [[ "${attempt}" -eq 60 ]]; then
        echo "SQL Server did not become ready in time." >&2
        exit 1
    fi

    sleep 2
done

run_script() {
    local script_path="$1"
    echo "Running $(basename "${script_path}")..."
    "${sqlcmd}" \
        -S "${database_host}" \
        -U sa \
        -C \
        -b \
        -r 1 \
        -i "${script_path}"
}

run_script /docker-init/sql/01_create_tables.sql

if [[ "${load_sample_data,,}" == "true" ]]; then
    run_script /docker-init/sql/02_sample_data.sql
else
    echo "Skipping sample data because LOAD_SAMPLE_DATA=${load_sample_data}."
fi

echo "Running 03_login_and_permissions.sql..."
"${sqlcmd}" \
    -S "${database_host}" \
    -U sa \
    -C \
    -b \
    -r 1 \
    -v APP_DB_USER="${app_db_user}" APP_DB_PASSWORD="${app_db_password_sql}" \
    -i /docker-init/sql/03_login_and_permissions.sql

echo "Database initialization completed successfully."
