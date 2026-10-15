import pyodbc
from typing import Optional, Dict, Any

# Cấu hình máy chủ SQL Server
SERVER_NAME = r"localhost\SQLEXPRESS"
DATABASE_NAME = "QLTV"

# Thông tin phiên đăng nhập hiện tại (Lưu sau khi xác thực thành công)
CURRENT_SESSION = {
    "login_name": "",
    "password": "",
    "user_info": None
}

def build_connection_string(uid: str, pwd: str, driver: str = "ODBC Driver 18 for SQL Server") -> str:
    """Tạo chuỗi kết nối SQL Server Authentication."""
    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={SERVER_NAME};"
        f"DATABASE={DATABASE_NAME};"
        f"UID={uid};"
        f"PWD={pwd};"
        "TrustServerCertificate=yes;"
    )

def get_connection(uid: Optional[str] = None, pwd: Optional[str] = None):
    """
    Mở kết nối tới SQL Server bằng tài khoản của phiên làm việc hiện tại,
    hoặc tài khoản truyền vào. Tự động tương thích ODBC Driver 18/17.
    Tuyệt đối không hardcode mật khẩu quản trị sa trong mã nguồn.
    """
    user_id = uid if uid else CURRENT_SESSION.get("login_name")
    password = pwd if pwd else CURRENT_SESSION.get("password")

    if not user_id or not password:
        raise ValueError("Chưa có phiên làm việc! Vui lòng đăng nhập vào hệ thống.")

    drivers = [
        "ODBC Driver 18 for SQL Server", 
        "ODBC Driver 17 for SQL Server", 
        "SQL Server"
    ]
    last_err = None

    for driver in drivers:
        try:
            conn_str = build_connection_string(user_id, password, driver)
            return pyodbc.connect(conn_str)
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
    2. Nếu SQL Server xác thực thành công -> gọi sp_LayThongTinNhanVien với tham số @LoginName.
       (Khắc phục lỗi: dùng tham số đầu vào rõ ràng thay vì lấy context ngầm).
    3. Cập nhật vào CURRENT_SESSION để các truy vấn nghiệp vụ sau thực hiện dưới đúng quyền này.
    """
    login_clean = login_name.strip()
    pwd_clean = password.strip()

    if not login_clean or not pwd_clean:
        raise ValueError("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!")

    try:
        # Bước 1: Thử kết nối trực tiếp bằng Login của người dùng
        conn = get_connection(login_clean, pwd_clean)
    except pyodbc.Error as err:
        err_msg = str(err)
        if "18456" in err_msg or "Login failed" in err_msg:
            raise ValueError("Tên đăng nhập hoặc mật khẩu SQL Server không chính xác!")
        raise RuntimeError(f"Không thể kết nối đến SQL Server ({SERVER_NAME}): {err_msg}")

    try:
        # Bước 2: Gọi Stored Procedure truyền tham số @LoginName
        cursor = conn.cursor()
        try:
            cursor.execute("EXEC dbo.sp_LayThongTinNhanVien @LoginName = ?", (login_clean,))
        except Exception:
            # Dự phòng nếu CSDL chưa nạp SP mới
            cursor.execute("EXEC dbo.sp_LayThongTinHienTai")

        row = cursor.fetchone()

        if not row:
            conn.close()
            raise RuntimeError("Không thể truy vấn thông tin định danh người dùng từ CSDL!")

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

        # Lưu lại session kết nối của người dùng hiện tại
        CURRENT_SESSION["login_name"] = login_clean
        CURRENT_SESSION["password"] = pwd_clean
        CURRENT_SESSION["user_info"] = user_info

        conn.close()
        return user_info
    except Exception as ex:
        conn.close()
        raise RuntimeError(f"Lỗi khi nạp quyền người dùng: {ex}")

# Hàm tương thích ngược
def kiem_tra_dang_nhap(username: str, password: str):
    return dang_nhap_he_thong(username, password)