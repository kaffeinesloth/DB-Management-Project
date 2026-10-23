"""
database.py: Quản lý kết nối SQL Server và phiên làm việc của người dùng.
Kế thừa trọn vẹn 100% logic từ nhánh feature/qltv, hỗ trợ đồng thời cả CSDL cục bộ (SQLEXPRESS / QLTV)
lẫn CSDL container Docker (LibraryManagement).
"""

import os
from typing import Optional, Dict, Any
import pyodbc

# Cấu hình máy chủ SQL Server mặc định (ưu tiên SQLEXPRESS của đề tài)
SERVER_NAME = r"localhost\SQLEXPRESS"
DATABASE_NAME = "QLTV"

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
            conn = pyodbc.connect(conn_str, timeout=3)
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
    pwd_clean = password.strip()

    if not login_clean or not pwd_clean:
        raise ValueError("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!")

    # Danh sách các cấu hình CSDL khả dụng để tự động nhận diện
    candidate_servers = [
        (r"localhost\SQLEXPRESS", "QLTV"),
        ("localhost,1433", "QLTV"),
        ("localhost", "QLTV"),
        (f"localhost,{os.environ.get('MSSQL_PORT', '14333')}", "LibraryManagement"),
        ("localhost,1433", "LibraryManagement"),
        (r"localhost\SQLEXPRESS", "LibraryManagement"),
    ]

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
            vai_tro = "Quản lý" if role_name == "QUANLY" else ("Độc giả" if role_name == "DOCGIA" else "Thủ thư")
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
            role_name = "QUANLY" if login_clean in ["admin", "sa", "library_app"] else ("DOCGIA" if "docgia" in login_clean.lower() else "THUTHU")
            vai_tro = "Quản lý" if role_name == "QUANLY" else ("Độc giả" if role_name == "DOCGIA" else "Thủ thư")
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
