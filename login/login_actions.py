"""Authentication logic and SQL Server session verification."""

from typing import Dict, Any, Optional
import pyodbc
from database import get_connection, test_server_connection, CURRENT_SESSION


def authenticate(username: str, password: str) -> Dict[str, Any]:
    """
    Xác thực tài khoản người dùng trực tiếp qua SQL Server Authentication:
    1. Kiểm tra thông tin đăng nhập với máy chủ SQL Server.
    2. Nhận diện quyền hạn (QUANLY / THUTHU / DOCGIA) và thông tin nhân viên.
    3. Thiết lập phiên làm việc trong database.CURRENT_SESSION.
    """
    user_clean = username.strip()
    pwd_clean = password.strip()

    if not user_clean or not pwd_clean:
        raise ValueError("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!")

    # 1. Thử kết nối qua máy chủ hiện hành hoặc auto-detect
    success, valid_srv, valid_db = test_server_connection(user_clean, pwd_clean)
    if not success:
        raise ValueError("Tên đăng nhập hoặc mật khẩu SQL Server không chính xác!")

    CURRENT_SESSION["active_server"] = valid_srv
    CURRENT_SESSION["active_db"] = valid_db

    # 2. Lấy thông tin định danh và quyền hạn
    user_info = _resolve_user_identity(user_clean, pwd_clean, valid_srv, valid_db)

    # 3. Lưu vào session
    CURRENT_SESSION["login_name"] = user_clean
    CURRENT_SESSION["password"] = pwd_clean
    CURRENT_SESSION["user_info"] = user_info

    return user_info


def _resolve_user_identity(user: str, pwd: str, srv: str, db: str) -> Dict[str, Any]:
    """Nhận diện vai trò người dùng (QUANLY, THUTHU, DOCGIA)."""
    user_upper = user.upper()

    # Tài khoản quản trị Docker mặc định hoặc tài khoản SA
    if user in ["sa", "library_app", "admin"]:
        role = "QUANLY"
        ten_hien_thi = "Ban Quản Lý Thư Viện" if user != "library_app" else "Nhóm Phát Triển (library_app)"
        return {
            "LoginName": user,
            "UserName": user,
            "RoleName": role,
            "MANV": 1,
            "HoTen": ten_hien_thi,
            "Email": f"{user}@thuvien.edu.vn",
            "VaiTro": "Quản lý (Admin)"
        }

    # Thử gọi Stored Procedure nếu CSDL có sẵn
    conn = get_connection(user, pwd, srv, db)
    try:
        cursor = conn.cursor()
        try:
            cursor.execute("EXEC dbo.sp_LayThongTinNhanVien @LoginName = ?", (user,))
            row = cursor.fetchone()
            if row:
                role_name = row[2]
                vai_tro = "Quản lý" if role_name == "QUANLY" else ("Độc giả" if role_name == "DOCGIA" else "Thủ thư")
                if len(row) > 6 and row[6]:
                    vai_tro = row[6]
                return {
                    "LoginName": row[0],
                    "UserName": row[1],
                    "RoleName": role_name,
                    "MANV": row[3],
                    "HoTen": row[4],
                    "Email": row[5],
                    "VaiTro": vai_tro
                }
        except Exception:
            pass

        # Tra cứu tên trong bảng NHANVIEN
        try:
            cursor.execute("SELECT TOP 1 MANV, HONV, TENNV, EMAILNV FROM dbo.NHANVIEN;")
            nv_row = cursor.fetchone()
            manv = nv_row[0] if nv_row else 1
            hoten = f"{nv_row[1]} {nv_row[2]}" if nv_row else user
            email = nv_row[3] if nv_row and len(nv_row) > 3 else f"{user}@thuvien.edu.vn"
        except Exception:
            manv = 1
            hoten = user
            email = f"{user}@thuvien.edu.vn"

        # Phân loại theo tên login
        if "DOCGIA" in user_upper:
            role = "DOCGIA"
            vai_tro = "Bạn đọc (Tra cứu)"
        elif "NV" in user_upper or "THUTHU" in user_upper:
            role = "THUTHU"
            vai_tro = "Thủ thư phục vụ"
        else:
            role = "QUANLY"
            vai_tro = "Quản lý thư viện"

        return {
            "LoginName": user,
            "UserName": user,
            "RoleName": role,
            "MANV": manv,
            "HoTen": hoten,
            "Email": email,
            "VaiTro": vai_tro
        }
    finally:
        conn.close()
