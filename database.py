"""
database.py: Quản lý kết nối SQL Server và phiên làm việc của người dùng.
Kế thừa trọn vẹn 100% logic từ nhánh feature/qltv, hỗ trợ đồng thời cả CSDL cục bộ (SQLEXPRESS / QLTV)
lẫn CSDL container Docker (LibraryManagement).
"""

import os
import re
from typing import Optional, Dict, Any, Set
import pyodbc

from pathlib import Path
from dotenv import load_dotenv

# Tắt connection pooling để phiên TCP của SQL Login đóng ngay lập tức khi đăng xuất / kết thúc truy vấn,
# tránh giữ zombie session trong sys.dm_exec_sessions làm kẹt sp_XoaTaiKhoanNhanVien (lỗi 51014).
pyodbc.pooling = False

# Tải cấu hình từ file .env nếu có
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

# Cấu hình máy chủ SQL Server mặc định (ưu tiên Docker localhost,14333 của dự án)
_default_port = os.environ.get("MSSQL_PORT", "14333")
SERVER_NAME = os.environ.get("DB_HOST", f"localhost,{_default_port}")
DATABASE_NAME = os.environ.get("DB_NAME", "LibraryManagement")

# Thông tin phiên đăng nhập hiện tại (Lưu sau khi xác thực thành công)
CURRENT_SESSION: Dict[str, Any] = {
    "login_name": "",
    "password": "",
    "user_info": None,
    "active_server": SERVER_NAME,
    "active_db": DATABASE_NAME
}

# Tương thích với khai báo trên nhánh main
connection: Any = None
_ACTIVE_CONNECTIONS: Set["ManagedConnection"] = set()


class ManagedConnection:
    """Bọc pyodbc.Connection để tự động gọi close() khi thoát khối `with`.

    Trong pyodbc chuẩn, `with conn:` chỉ commit/rollback chứ KHÔNG gọi `conn.close()`,
    khiến phiên TCP vẫn mở trên SQL Server sau khi đăng xuất.
    """

    def __init__(self, raw_conn: pyodbc.Connection) -> None:
        object.__setattr__(self, "_raw_conn", raw_conn)
        object.__setattr__(self, "_closed", False)
        _ACTIVE_CONNECTIONS.add(self)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw_conn, name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._raw_conn, name, value)

    def __enter__(self) -> "ManagedConnection":
        self._raw_conn.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any:
        try:
            return self._raw_conn.__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.close()

    def close(self) -> None:
        _ACTIVE_CONNECTIONS.discard(self)
        if not self._closed:
            object.__setattr__(self, "_closed", True)
            try:
                self._raw_conn.close()
            except pyodbc.Error:
                pass


def clear_session() -> None:
    """Đóng toàn bộ kết nối đang mở và xóa thông tin phiên làm việc khỏi bộ nhớ."""
    global connection
    for active_conn in list(_ACTIVE_CONNECTIONS):
        active_conn.close()
    _ACTIVE_CONNECTIONS.clear()

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


def odbc_quote(value: str) -> str:
    """Quote one ODBC connection-string value: {value} with '}' doubled.

    Without quoting, a password such as ``x;Trusted_Connection=yes`` would add a
    new attribute to the connection string (connection-string injection) and
    could switch the login to Windows authentication.
    """
    return "{" + str(value).replace("}", "}}") + "}"


def build_connection_string(
    uid: str,
    pwd: str,
    driver: str = "ODBC Driver 18 for SQL Server",
    server: Optional[str] = None,
    database: Optional[str] = None
) -> str:
    """Tạo chuỗi kết nối SQL Server Authentication (mọi giá trị đều được quote an toàn)."""
    srv = server or CURRENT_SESSION.get("active_server") or SERVER_NAME
    db = database or CURRENT_SESSION.get("active_db") or DATABASE_NAME
    return (
        f"DRIVER={odbc_quote(driver)};"
        f"SERVER={odbc_quote(srv)};"
        f"DATABASE={odbc_quote(db)};"
        f"UID={odbc_quote(uid)};"
        f"PWD={odbc_quote(pwd)};"
        "TrustServerCertificate=yes;"
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

    drivers = [
        "ODBC Driver 18 for SQL Server", 
        "ODBC Driver 17 for SQL Server", 
        "SQL Server"
    ]
    last_err = None

    for driver in drivers:
        try:
            conn_str = build_connection_string(user_id, password, driver, target_srv, target_db)
            conn = ManagedConnection(pyodbc.connect(conn_str, timeout=3))
            global connection
            connection = conn
            return conn
        except pyodbc.Error as err:
            last_err = err
            continue

    if last_err:
        raise last_err
    raise RuntimeError("Không tìm thấy ODBC Driver phù hợp để kết nối SQL Server!")


def dang_nhap_he_thong(login_name: str, password: str) -> Dict[str, Any]:
    """
    Xác thực đăng nhập trực tiếp qua SQL Server Authentication:
    1. Kết nối vào SQL Server bằng đúng login_name và password của người dùng.
       (Tự động kiểm tra SQLEXPRESS / QLTV trước, fallback qua Docker LibraryManagement).
    2. Nếu SQL Server xác thực thành công -> gọi sp_LayThongTinNhanVien với tham số @LoginName.
    3. Cập nhật vào CURRENT_SESSION để các truy vấn nghiệp vụ sau thực hiện dưới đúng quyền này.
    """
    login_clean = login_name.strip()
    # Passwords may legally contain leading/trailing spaces, so do not trim it.
    pwd_clean = password

    if not login_clean or not pwd_clean:
        raise ValueError("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!")

    # Ưu tiên đúng cổng Docker của dự án, sau đó mới thử các cấu hình cục bộ cũ.
    # Ưu tiên đúng cổng Docker của dự án (14333/1433), sau đó mới thử các cấu hình cục bộ cũ.
    docker_port = os.environ.get("MSSQL_PORT", "14333")
    candidate_servers_raw = [
        (f"localhost,{docker_port}", "LibraryManagement"),
        ("localhost,14333", "LibraryManagement"),
        ("localhost,1433", "LibraryManagement"),
        ("localhost", "LibraryManagement"),
        (r"localhost\SQLEXPRESS", "LibraryManagement"),
        (r"localhost\SQLEXPRESS", "QLTV"),
        ("localhost,1433", "QLTV"),
        ("localhost", "QLTV"),
    ]
    candidate_servers = list(dict.fromkeys(candidate_servers_raw))

    conn = None
    last_login_err = None
    active_srv = None
    active_db = None

    for srv, db in candidate_servers:
        try:
            conn = get_connection(login_clean, pwd_clean, server=srv, database=db)
            active_srv = srv
            active_db = db
            break
        except pyodbc.Error as err:
            err_msg = str(err)
            if "18456" in err_msg or "Login failed" in err_msg:
                last_login_err = "Tên đăng nhập hoặc mật khẩu SQL Server không chính xác!"
            continue
        except Exception:
            continue

    if not conn:
        if last_login_err:
            raise ValueError(last_login_err)
        raise RuntimeError(f"Không thể kết nối đến SQL Server ({SERVER_NAME}). Vui lòng đảm bảo dịch vụ SQL Server đang hoạt động!")

    try:
        cursor = conn.cursor()
        user_info = None

        # Bước 2: Gọi Stored Procedure truyền tham số @LoginName
        try:
            cursor.execute("EXEC dbo.sp_LayThongTinNhanVien @LoginName = ?", (login_clean,))
            row = cursor.fetchone()
        except Exception:
            try:
                cursor.execute("EXEC dbo.sp_LayThongTinHienTai")
                row = cursor.fetchone()
            except Exception:
                row = None

        if row:
            role_name = row[2]
            vai_tro = "Quản lý" if role_name == "QUANLY" else "Thủ thư"
            if len(row) > 6 and row[6]:
                vai_tro = row[6]

            user_info = {
                "LoginName": row[0],
                "UserName": row[1],
                "RoleName": role_name,
                "MANV": row[3],
                "HoTen": row[4],
                "Email": row[5],
                "VaiTro": vai_tro
            }
        else:
            # Fallback nếu login quản trị Docker (sa / library_app) không có bản ghi trong sp_LayThongTinNhanVien
            role_name = "QUANLY" if login_clean in ["admin", "sa", "library_app"] else "THUTHU"
            vai_tro = "Quản lý" if role_name == "QUANLY" else "Thủ thư"
            user_info = {
                "LoginName": login_clean,
                "UserName": login_clean,
                "RoleName": role_name,
                "MANV": 1,
                "HoTen": "Ban Quản Trị Hệ Thống" if role_name == "QUANLY" else login_clean,
                "Email": f"{login_clean}@thuvien.edu.vn",
                "VaiTro": vai_tro
            }

        # Lưu lại session kết nối của người dùng hiện tại
        CURRENT_SESSION["login_name"] = login_clean
        CURRENT_SESSION["password"] = pwd_clean
        CURRENT_SESSION["user_info"] = user_info
        CURRENT_SESSION["active_server"] = active_srv
        CURRENT_SESSION["active_db"] = active_db

        conn.close()
        return user_info
    except Exception as ex:
        if conn:
            conn.close()
        raise RuntimeError(f"Lỗi khi nạp quyền người dùng: {ex}")


# Hàm tương thích ngược
def kiem_tra_dang_nhap(username: str, password: str) -> Dict[str, Any]:
    return dang_nhap_he_thong(username, password)


# ---------------------------------------------------------------------------
# Phân tích mã lỗi gốc SQL Server (native error codes) sang thông báo tiếng Việt
# ---------------------------------------------------------------------------
FK_VIOLATION = 547          # INSERT/UPDATE/DELETE conflicted with a FOREIGN KEY / CHECK
UNIQUE_INDEX = 2601         # duplicate key row in a unique index
PRIMARY_KEY = 2627          # violation of PRIMARY KEY / UNIQUE constraint
TRUNCATION = (2628, 8152)   # string or binary data would be truncated
PERMISSION_DENIED = 229     # SELECT/INSERT/... permission was denied

FK_DELETE_MESSAGE = (
    "Không thể xóa vì dữ liệu này đã phát sinh giao dịch liên quan trong hệ thống!"
)

_CODE_PATTERN = re.compile(r"\((\d{3,6})\)")


def sql_error_codes(error: BaseException) -> Set[int]:
    """Return every SQL Server native error number found in ``error``."""
    return {int(code) for code in _CODE_PATTERN.findall(str(error))}


def has_error_code(error: BaseException, *codes: int) -> bool:
    return bool(sql_error_codes(error).intersection(codes))


def is_fk_violation(error: BaseException) -> bool:
    """True when the statement was rejected by a FOREIGN KEY (error 547)."""
    return has_error_code(error, FK_VIOLATION)


def server_message(error: BaseException) -> str:
    """Text SQL Server raised (e.g. a THROW from a stored procedure), without driver noise."""
    text = str(error)
    marker = "[SQL Server]"
    if marker in text:
        text = text.rsplit(marker, 1)[1]
    text = re.sub(r"\s*\(\d{3,6}\)\s*(\(SQL\w+\))?[\"')]*\s*$", "", text)
    return text.strip().strip("'\"").strip()


def friendly_message(error: BaseException, entity: str = "dữ liệu") -> Optional[str]:
    """Return a Vietnamese explanation for well-known SQL Server errors, else None."""
    if is_fk_violation(error):
        return FK_DELETE_MESSAGE
    if has_error_code(error, PRIMARY_KEY, UNIQUE_INDEX):
        return f"Mã {entity} đã tồn tại trong hệ thống. Vui lòng nhập mã khác!"
    if has_error_code(error, *TRUNCATION):
        return "Một trường dữ liệu vượt quá độ dài cho phép của cơ sở dữ liệu!"
    if has_error_code(error, PERMISSION_DENIED):
        return "Tài khoản hiện tại không có quyền thực hiện thao tác này!"
    return None
