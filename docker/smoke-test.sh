#!/usr/bin/env bash

set -Eeuo pipefail

# Use the database-init service so Docker Compose resolves APP_DB_USER and
# APP_DB_PASSWORD from the same .env file used to create the database.
docker compose run --rm --no-deps --entrypoint /bin/bash database-init -c '
    if [[ -x /opt/mssql-tools18/bin/sqlcmd ]]; then
        sqlcmd=/opt/mssql-tools18/bin/sqlcmd
    elif [[ -x /opt/mssql-tools/bin/sqlcmd ]]; then
        sqlcmd=/opt/mssql-tools/bin/sqlcmd
    else
        echo "sqlcmd was not found in the SQL Server image." >&2
        exit 1
    fi

    export SQLCMDPASSWORD="${APP_DB_PASSWORD}"
    exec "${sqlcmd}" \
        -S "${DB_HOST:-sqlserver}" \
        -U "${APP_DB_USER}" \
        -C \
        -b \
        -I \
        -i /docker-init/sql/99_smoke_test.sql
'
