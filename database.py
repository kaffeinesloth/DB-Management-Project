"""Shared database connection and session management."""

import os
import re
from typing import Optional, Dict, Any, List
import pyodbc


def _load_env_file() -> Dict[str, str]:
    """Đọc file .env nếu tồn tại mà không cần cài thêm thư viện phụ thuộc."""
    env_vars = {}
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env_vars[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass
    return env_vars


_ENV = _load_env_file()

# Cấu hình CSDL linh hoạt: Ưu tiên cổng Docker (14333/1433) hoặc máy chủ cục bộ SQLEXPRESS
PORT = os.environ.get("MSSQL_PORT") or _ENV.get("MSSQL_PORT", "14333")
DEFAULT_SERVERS = [
    f"localhost,{PORT}",
    r"localhost\SQLEXPRESS",
    "localhost,1433",
    "localhost"
]
DEFAULT_DB_NAMES = ["LibraryManagement", "QLTV"]

# Session người dùng hiện tại
CURRENT_SESSION: Dict[str, Any] = {
    "login_name": "",
    "password": "",
    "user_info": None,
    "active_server": f"localhost,{PORT}",
    "active_db": "LibraryManagement"
}

# Tương thích với khai báo gốc trên nhánh main
connection: pyodbc.Connection | None = None


def get_connection(
    uid: Optional[str] = None, 
    pwd: Optional[str] = None,
    server: Optional[str] = None,
    database: Optional[str] = None
) -> pyodbc.Connection:
    """
    Tạo kết nối tới SQL Server:
    - Nếu không truyền uid/pwd, sử dụng thông tin từ phiên đăng nhập hiện tại.
    - Hỗ trợ tự động fallback qua các ODBC Driver (18 -> 17 -> SQL Server).
    """
    user_id = uid if uid is not None else CURRENT_SESSION.get("login_name")
    password = pwd if pwd is not None else CURRENT_SESSION.get("password")

    if not user_id or not password:
        raise ValueError("Chưa có phiên làm việc! Vui lòng đăng nhập vào hệ thống.")

    target_server = server or CURRENT_SESSION.get("active_server") or f"localhost,{PORT}"
    target_db = database or CURRENT_SESSION.get("active_db") or "LibraryManagement"

    drivers = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server"
    ]

    last_error: Optional[Exception] = None

    for driver in drivers:
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={target_server};"
            f"DATABASE={target_db};"
            f"UID={user_id};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )
        try:
            conn = pyodbc.connect(conn_str, timeout=5)
            # Cập nhật kết nối dùng chung cho main
            global connection
            connection = conn
            return conn
        except Exception as err:
            last_error = err
            continue

    if last_error:
        raise last_error
    raise RuntimeError("Không tìm thấy ODBC Driver phù hợp để kết nối SQL Server!")


def test_server_connection(user: str, pwd: str) -> tuple[bool, str, str]:
    """
    Thử nghiệm kết nối qua danh sách máy chủ và tên CSDL khả dụng để tìm máy chủ đang hoạt động.
    Trả về (thành_công, server_hợp_lệ, db_hợp_lệ).
    """
    for srv in DEFAULT_SERVERS:
        for db in DEFAULT_DB_NAMES:
            try:
                conn = get_connection(uid=user, pwd=pwd, server=srv, database=db)
                conn.close()
                return True, srv, db
            except Exception:
                continue
    return False, "", ""
