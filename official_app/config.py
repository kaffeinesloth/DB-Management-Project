"""SQL Server connection settings for the login demo.

Edit these values for the SQL Server instance used on your computer. Login
names and passwords are intentionally not stored here; they come from the
login form at runtime.
"""

import os

SQL_SERVER = os.getenv("QLTV_SQL_SERVER", "localhost")
DATABASE = os.getenv("QLTV_DATABASE", "QLTV")
DRIVER = os.getenv("QLTV_ODBC_DRIVER", "ODBC Driver 18 for SQL Server")
CONNECTION_TIMEOUT_SECONDS = int(os.getenv("QLTV_CONNECTION_TIMEOUT", "5"))
