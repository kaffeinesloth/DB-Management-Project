"""Create SQL Server connections from credentials entered in the UI."""

from __future__ import annotations

import pyodbc

from config import CONNECTION_TIMEOUT_SECONDS, DATABASE, DRIVER, SQL_SERVER


def _odbc_value(value: str) -> str:
    """Quote an ODBC connection-string value and escape closing braces."""
    return "{" + value.replace("}", "}}") + "}"


def build_connection_string(login_name: str, password: str) -> str:
    """Build a SQL Server Authentication connection string.

    The exact login name and password supplied by the user are used. No admin
    credentials or fallback account is involved.
    """
    return (
        f"DRIVER={_odbc_value(DRIVER)};"
        f"SERVER={_odbc_value(SQL_SERVER)};"
        f"DATABASE={_odbc_value(DATABASE)};"
        f"UID={_odbc_value(login_name)};"
        f"PWD={_odbc_value(password)};"
        "TrustServerCertificate=yes;"
        f"Connection Timeout={CONNECTION_TIMEOUT_SECONDS};"
    )


def open_user_connection(login_name: str, password: str) -> pyodbc.Connection:
    """Authenticate to SQL Server and return the user's live connection."""
    return pyodbc.connect(
        build_connection_string(login_name, password),
        autocommit=False,
    )

