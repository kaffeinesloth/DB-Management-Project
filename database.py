"""Shared SQL Server connection.

Settings come from environment variables, then the project's .env file, then
.env.example (the shared classroom baseline). Keys used:
  DB_HOST (default localhost), MSSQL_PORT (default 1433),
  DB_NAME (default LibraryManagement), APP_DB_USER, APP_DB_PASSWORD,
  DB_DRIVER (default: newest installed "ODBC Driver NN for SQL Server").
"""

import os
from pathlib import Path

import pyodbc


PROJECT_ROOT = Path(__file__).resolve().parent

connection: pyodbc.Connection | None = None


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_settings() -> dict[str, str]:
    settings = _read_env_file(PROJECT_ROOT / ".env.example")
    settings.update(_read_env_file(PROJECT_ROOT / ".env"))
    settings.update({key: value for key, value in os.environ.items() if value})
    return settings


def _pick_driver(settings: dict[str, str]) -> str:
    if settings.get("DB_DRIVER"):
        return settings["DB_DRIVER"]
    candidates = [
        name for name in pyodbc.drivers()
        if name.startswith("ODBC Driver") and name.endswith("for SQL Server")
    ]
    if not candidates:
        raise RuntimeError(
            "No 'ODBC Driver NN for SQL Server' is installed. "
            "Install Microsoft ODBC Driver 18 for SQL Server."
        )
    return max(candidates, key=lambda name: int("".join(filter(str.isdigit, name)) or 0))


def build_connection_string(settings: dict[str, str] | None = None) -> str:
    settings = settings if settings is not None else load_settings()
    user = settings.get("APP_DB_USER")
    password = settings.get("APP_DB_PASSWORD")
    if not user or not password:
        raise RuntimeError("APP_DB_USER and APP_DB_PASSWORD must be set (see .env.example).")
    host = settings.get("DB_HOST", "localhost")
    port = settings.get("MSSQL_PORT", "1433")
    return (
        f"DRIVER={{{_pick_driver(settings)}}};"
        f"SERVER={host},{port};"
        f"DATABASE={settings.get('DB_NAME', 'LibraryManagement')};"
        f"UID={user};PWD={{{password.replace('}', '}}')}}};"
        "Encrypt=yes;TrustServerCertificate=yes;"
    )


def get_connection() -> pyodbc.Connection:
    """Return the shared connection, opening (or reopening) it when needed."""
    global connection
    if connection is not None:
        try:
            connection.cursor().execute("SELECT 1").fetchone()
            return connection
        except pyodbc.Error:
            close_connection()
    connection = pyodbc.connect(build_connection_string(), timeout=5, autocommit=True)
    return connection


def close_connection() -> None:
    global connection
    if connection is not None:
        try:
            connection.close()
        except pyodbc.Error:
            pass
        connection = None
