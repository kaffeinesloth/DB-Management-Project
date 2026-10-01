import pyodbc
from typing import Optional, Dict, Any

# Cấu hình máy chủ SQL Server
SERVER_NAME = r"localhost\SQLEXPRESS"
DATABASE_NAME = "QLTV"

# Thông tin phiên đăng nhập hiện tại
CURRENT_SESSION = {
    "login_name": "sa",
    "password": "Admin@123",
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
    hoặc tài khoản truyền vào.
    """
    user_id = uid if uid else CURRENT_SESSION["login_name"]
    password = pwd if pwd else CURRENT_SESSION["password"]

    try:
        conn_str = build_connection_string(user_id, password, "ODBC Driver 18 for SQL Server")
        return pyodbc.connect(conn_str)
    except pyodbc.Error:
        conn_str_17 = build_connection_string(user_id, password, "ODBC Driver 17 for SQL Server")
        return pyodbc.connect(conn_str_17)

def tra_cuu_nhan_vien_nhanh(login_name: str) -> Optional[Dict[str, Any]]:
    """
    Tra cứu thông tin nhân viên theo Login Name (để auto hiện Employee ID khi người dùng gõ username).
    """
    if not login_name or not login_name.strip():
        return None

    try:
        with get_connection("sa", "Admin@123") as conn:
            cursor = conn.cursor()
            cursor.execute("EXEC dbo.sp_TraCuuNhanVienTheoLogin @LoginName = ?", (login_name.strip(),))
            row = cursor.fetchone()
            if row:
                return {
                    "MANV": row[0],
                    "HoTen": row[1],
                    "Email": row[2],
                    "LoginName": row[3],
                    "RoleName": row[4]
                }
            return None
    except Exception:
        return None

def dang_nhap_he_thong(login_name: str, password: str) -> Dict[str, Any]:
    """
    Xác thực đăng nhập trực tiếp qua SQL Server Authentication:
    1. Kết nối vào SQL Server bằng đúng login_name và password của người dùng.
    2. Nếu SQL Server xác thực thành công -> gọi sp_LayThongTinHienTai để lấy:
       - LoginName (cấp Server: SUSER_SNAME)
       - UserName (cấp Database: USER_NAME)
       - RoleName (Nhóm quyền: QUANLY / THUTHU)
       - MANV (Mã nhân viên / Employee ID)
       - HoTen
    3. Cập nhật vào CURRENT_SESSION để các truy vấn sau thực hiện dưới quyền này.
    """
    login_clean = login_name.strip()
    pwd_clean = password.strip()

    try:
        # Bước 1: Thử kết nối trực tiếp bằng Login của người dùng
        conn = get_connection(login_clean, pwd_clean)
    except pyodbc.Error as err:
        # Lỗi 18456 là lỗi xác thực sai Login hoặc Password của SQL Server
        err_msg = str(err)
        if "18456" in err_msg or "Login failed" in err_msg:
            raise ValueError("Tên đăng nhập hoặc mật khẩu SQL Server không chính xác!")
        raise RuntimeError(f"Không thể kết nối đến SQL Server: {err_msg}")

    try:
        # Bước 2: Gọi Stored Procedure lấy thông tin định danh & nhóm quyền
        cursor = conn.cursor()
        cursor.execute("EXEC dbo.sp_LayThongTinHienTai")
        row = cursor.fetchone()

        user_info = {
            "LoginName": row[0],
            "UserName": row[1],
            "RoleName": row[2],
            "MANV": row[3],
            "HoTen": row[4],
            "Email": row[5],
            "VaiTro": "Quản lý" if row[2] == "QUANLY" else "Thủ thư"
        }

        # Lưu lại session kết nối của người dùng hiện tại
        CURRENT_SESSION["login_name"] = login_clean
        CURRENT_SESSION["password"] = pwd_clean
        CURRENT_SESSION["user_info"] = user_info

        conn.close()
        return user_info
    except Exception as ex:
        conn.close()
        raise RuntimeError(f"Lỗi truy vấn thông tin định danh: {ex}")

# Hàm tương thích ngược với code cũ
def kiem_tra_dang_nhap(username: str, password: str):
    return dang_nhap_he_thong(username, password)

if __name__ == "__main__":
    try:
        info = dang_nhap_he_thong("admin", "Admin@123")
        print("Đăng nhập thành công:", info)
    except Exception as e:
        print("Lỗi:", e)