#!/usr/bin/env bash

set -Eeuo pipefail

action="${1:-}"
backup_file="${2:-}"

case "${action}" in
    backup)
        if [[ -z "${backup_file}" ]]; then
            backup_file="LibraryManagement_$(date +%Y%m%d_%H%M%S).bak"
        fi
        sql_action=BACKUP
        ;;
    verify)
        if [[ -z "${backup_file}" ]]; then
            echo "Usage: $0 verify <backup-file.bak>" >&2
            exit 2
        fi
        sql_action=VERIFY
        ;;
    restore)
        if [[ -z "${backup_file}" ]]; then
            echo "Usage: CONFIRM_RESTORE=LibraryManagement $0 restore <backup-file.bak>" >&2
            exit 2
        fi
        if [[ "${CONFIRM_RESTORE:-}" != "LibraryManagement" ]]; then
            echo "Restore replaces the current database and disconnects its users." >&2
            echo "Run again with CONFIRM_RESTORE=LibraryManagement to confirm." >&2
            exit 3
        fi
        sql_action=RESTORE
        ;;
    list)
        docker compose exec -T sqlserver \
            find /var/opt/mssql/backups -maxdepth 1 -type f -name '*.bak' \
            -printf '%f\n' | sort
        exit 0
        ;;
    *)
        echo "Usage: $0 {backup|verify|restore|list} [backup-file.bak]" >&2
        exit 2
        ;;
esac

if [[ ! "${backup_file}" =~ ^[A-Za-z0-9._-]+\.bak$ || "${backup_file}" == *..* ]]; then
    echo "Backup filename must contain only letters, numbers, dots, underscores, or hyphens and end in .bak." >&2
    exit 2
fi

docker compose exec -T sqlserver \
    /opt/mssql-tools18/bin/sqlcmd \
    -S localhost \
    -U sa \
    -C \
    -b \
    -v ACTION="${sql_action}" BACKUP_FILE="${backup_file}" \
    -i /docker-init/sql/04_backup_and_restore.sql

if [[ "${action}" == "backup" ]]; then
    echo "Created and verified ${backup_file}."
fi
