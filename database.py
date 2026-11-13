"""Quản lý kết nối SQL Server và phiên làm việc của người dùng."""

import os
from typing import Optional, Dict, Any
import pyodbc

# Cấu hình mặc định khớp với compose.yaml và SSMS của dự án.
MSSQL_PORT = os.environ.get("MSSQL_PORT", "1433")
SERVER_NAME = os.environ.get("DB_HOST", f"localhost,{MSSQL_PORT}")
DATABASE_NAME = os.environ.get("DB_NAME", "LibraryManagement")

PREFERRED_ODBC_DRIVERS = (
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "SQL Server",
)

VALID_EMPLOYEE_ROLES = {"THUTHU", "QUANLY"}
NON_EMPLOYEE_LOGINS = {"sa", "library_app"}

# Thông tin phiên đăng nhập hiện tại (Lưu sau khi xác thực thành công)
CURRENT_SESSION: Dict[str, Any] = {
    "login_name": "",
    "password": "",
    "user_info": None,
    "active_server": SERVER_NAME,
    "active_db": DATABASE_NAME
}

# Tương thích với khai báo trên nhánh main
connection: pyodbc.Connection | None = None


def clear_session() -> None:
    """Close the shared connection and remove credentials from memory."""
    global connection
    if connection is not None:
        try:
            connection.close()
        except pyodbc.Error:
            pass
        connection = None

    CURRENT_SESSION.update({
        "login_name": "",
        "password": "",
        "user_info": None,
        "active_server": SERVER_NAME,
        "active_db": DATABASE_NAME,
    })


def build_connection_string(
    uid: str, 
    pwd: str, 
    driver: str = "ODBC Driver 18 for SQL Server",
    server: Optional[str] = None,
    database: Optional[str] = None
) -> str:
    """Tạo chuỗi kết nối SQL Server Authentication."""
    srv = server or CURRENT_SESSION.get("active_server") or SERVER_NAME
    db = database or CURRENT_SESSION.get("active_db") or DATABASE_NAME
    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={srv};"
        f"DATABASE={db};"
        f"UID={uid};"
        f"PWD={pwd};"
        "TrustServerCertificate=yes;"
    )


def _get_sql_server_drivers() -> list[str]:
    """Return installed SQL Server drivers in preferred order."""
    installed = set(pyodbc.drivers())
    drivers = [driver for driver in PREFERRED_ODBC_DRIVERS if driver in installed]
    if not drivers:
        raise RuntimeError("Không tìm thấy ODBC Driver phù hợp để kết nối SQL Server!")
    return drivers


def _is_login_error(error: pyodbc.Error) -> bool:
    message = str(error).lower()
    return "18456" in message or "login failed" in message


def _is_driver_compatibility_error(error: pyodbc.Error) -> bool:
    """Identify local driver/TLS failures where another installed driver may work."""
    message = str(error).lower()
    return any(
        marker in message
        for marker in (
            "encryption not supported",
            "ssl security error",
            "seccreatecredentials",
            "tls",
        )
    )


def get_connection(
    uid: Optional[str] = None, 
    pwd: Optional[str] = None,
    server: Optional[str] = None,
    database: Optional[str] = None
) -> pyodbc.Connection:
    """
    Mở kết nối tới SQL Server bằng tài khoản của phiên làm việc hiện tại,
    hoặc tài khoản truyền vào. Tự động tương thích ODBC Driver 18/17.
    Tuyệt đối không hardcode mật khẩu quản trị sa trong mã nguồn.
    """
    user_id = uid if uid else CURRENT_SESSION.get("login_name")
    password = pwd if pwd else CURRENT_SESSION.get("password")

    if not user_id or not password:
        raise ValueError("Chưa có phiên làm việc! Vui lòng đăng nhập vào hệ thống.")

    target_srv = server or CURRENT_SESSION.get("active_server") or SERVER_NAME
    target_db = database or CURRENT_SESSION.get("active_db") or DATABASE_NAME

    last_error = None
    for driver in _get_sql_server_drivers():
        try:
            conn_str = build_connection_string(
                user_id, password, driver, target_srv, target_db
            )
            conn = pyodbc.connect(conn_str, timeout=3)
            global connection
            connection = conn
            return conn
        except pyodbc.Error as err:
            # Invalid credentials are definitive. Never retry them with another
            # driver, because that only delays the same rejection.
            if _is_login_error(err):
                raise
            last_error = err
            if not _is_driver_compatibility_error(err):
                raise

    if last_error:
        raise last_error
    raise RuntimeError("Không tìm thấy ODBC Driver phù hợp để kết nối SQL Server!")


def dang_nhap_he_thong(login_name: str, password: str) -> Dict[str, Any]:
    """
    Xác thực đăng nhập trực tiếp qua SQL Server Authentication:
    1. Kết nối vào SQL Server bằng đúng login_name và password của người dùng.
       Kết nối duy nhất tới máy chủ và CSDL đã cấu hình.
    2. Nếu SQL Server xác thực thành công -> gọi sp_LayThongTinNhanVien với tham số @LoginName.
    3. Cập nhật vào CURRENT_SESSION để các truy vấn nghiệp vụ sau thực hiện dưới đúng quyền này.
    """
    login_clean = login_name.strip()
    # Passwords may legally contain leading/trailing spaces, so do not trim it.
    pwd_clean = password

    if not login_clean or not pwd_clean:
        raise ValueError("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!")

    # The application has one configured database. Retrying other servers after
    # a definitive login failure makes invalid credentials unnecessarily slow.
    try:
        conn = get_connection(
            login_clean,
            pwd_clean,
            server=SERVER_NAME,
            database=DATABASE_NAME,
        )
    except pyodbc.Error as err:
        if _is_login_error(err):
            raise ValueError(
                "Tên đăng nhập hoặc mật khẩu SQL Server không chính xác!"
            ) from None
        raise RuntimeError(
            f"Không thể kết nối đến SQL Server ({SERVER_NAME}). "
            "Vui lòng đảm bảo dịch vụ SQL Server đang hoạt động!"
        ) from err

    active_srv = SERVER_NAME
    active_db = DATABASE_NAME

    try:
        if login_clean.casefold() in NON_EMPLOYEE_LOGINS:
            raise ValueError("Tài khoản này không được phép đăng nhập ứng dụng.")

        cursor = conn.cursor()
        try:
            cursor.execute(
                "EXEC dbo.sp_LayThongTinNhanVien @LoginName = ?",
                (login_clean,),
            )
            row = cursor.fetchone()
        except pyodbc.Error as error:
            raise RuntimeError(
                "Không thể tải thông tin và quyền của nhân viên."
            ) from error

        if not row:
            raise ValueError(
                "Tài khoản chưa được liên kết với nhân viên hợp lệ."
            )

        role_name = str(row[2] or "").strip().upper()
        try:
            employee_id = int(row[3])
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Tài khoản chưa được liên kết với nhân viên hợp lệ."
            ) from error

        # Valid employee database users are deliberately named with MANV. This
        # rejects service/admin logins even when an older stored procedure maps
        # an unknown account to employee 1.
        database_user = str(row[1] or "").strip()
        if employee_id <= 0 or database_user != str(employee_id):
            raise ValueError(
                "Tài khoản chưa được liên kết với nhân viên hợp lệ."
            )
        if role_name not in VALID_EMPLOYEE_ROLES:
            raise ValueError("Tài khoản không có nhóm quyền hợp lệ.")

        vai_tro = "Quản lý" if role_name == "QUANLY" else "Thủ thư"
        user_info = {
            "LoginName": row[0],
            "UserName": database_user,
            "RoleName": role_name,
            "MANV": employee_id,
            "HoTen": row[4],
            "Email": row[5],
            "VaiTro": vai_tro,
        }

        # Lưu lại session kết nối của người dùng hiện tại
        CURRENT_SESSION["login_name"] = login_clean
        CURRENT_SESSION["password"] = pwd_clean
        CURRENT_SESSION["user_info"] = user_info
        CURRENT_SESSION["active_server"] = active_srv
        CURRENT_SESSION["active_db"] = active_db

        return user_info
    finally:
        try:
            conn.close()
        except pyodbc.Error:
            pass


# Hàm tương thích ngược
def kiem_tra_dang_nhap(username: str, password: str) -> Dict[str, Any]:
    return dang_nhap_he_thong(username, password)
