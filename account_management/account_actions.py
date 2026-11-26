"""Database operations for employee SQL Server accounts."""

import re
import unicodedata
from typing import Any, Dict, List

from database import CURRENT_SESSION, get_connection


VALID_ACCOUNT_ROLES = {"THUTHU", "QUANLY"}
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^[0-9]{10,11}$")
MAX_LOGIN_LENGTH = 128
MAX_PASSWORD_LENGTH = 128


def _is_valid_person_name(value: str) -> bool:
    """Allow Unicode letters and ordinary name punctuation, but not digits."""
    allowed_punctuation = {" ", "-", "'", "’", "."}
    has_letter = False
    for character in value:
        category = unicodedata.category(character)
        if category.startswith("L"):
            has_letter = True
        elif category.startswith("M") or character in allowed_punctuation:
            continue
        else:
            return False
    return has_letter


def validate_account_input(
    employee_id: int, login_name: str, password: str, role_name: str
) -> tuple[int, str, str, str]:
    """Validate and normalize account data before sending it to SQL Server."""
    try:
        normalized_id = int(employee_id)
    except (TypeError, ValueError) as error:
        raise ValueError("Mã nhân viên phải là số nguyên hợp lệ.") from error
    if not isinstance(login_name, str):
        raise ValueError("Tên đăng nhập không hợp lệ.")
    if not isinstance(password, str):
        raise ValueError("Mật khẩu không hợp lệ.")
    if not isinstance(role_name, str):
        raise ValueError("Nhóm quyền không hợp lệ.")
    normalized_login = login_name.strip()
    normalized_role = role_name.strip().upper()
    if normalized_id <= 0:
        raise ValueError("Mã nhân viên phải lớn hơn 0.")
    if not normalized_login:
        raise ValueError("Tên đăng nhập không được để trống.")
    normalized_login = validate_login_name(normalized_login)
    if len(password) < 6:
        raise ValueError("Mật khẩu phải có ít nhất 6 ký tự.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError("Mật khẩu tối đa 128 ký tự.")
    if normalized_role not in VALID_ACCOUNT_ROLES:
        raise ValueError("Nhóm quyền chỉ có thể là THUTHU hoặc QUANLY.")
    return normalized_id, normalized_login, password, normalized_role


def validate_new_employee(
    family_name: str,
    given_name: str,
    gender: bool,
    address: str,
    phone: str,
    email: str,
    login_name: str,
    password: str,
    role_name: str,
) -> Dict[str, Any]:
    """Validate a new employee and their requested account as one form."""
    family_name = unicodedata.normalize("NFC", family_name.strip())
    given_name = unicodedata.normalize("NFC", given_name.strip())
    address = address.strip()
    phone = phone.strip()
    email = email.strip().lower()
    if not family_name or len(family_name) > 50:
        raise ValueError("Họ nhân viên là bắt buộc và tối đa 50 ký tự.")
    if not _is_valid_person_name(family_name):
        raise ValueError("Họ nhân viên chỉ được chứa chữ cái và dấu tên hợp lệ.")
    if not given_name or len(given_name) > 12:
        raise ValueError("Tên nhân viên là bắt buộc và tối đa 12 ký tự.")
    if not _is_valid_person_name(given_name):
        raise ValueError("Tên nhân viên chỉ được chứa chữ cái và dấu tên hợp lệ.")
    if address and len(address) > 100:
        raise ValueError("Địa chỉ tối đa 100 ký tự.")
    if phone and not PHONE_PATTERN.fullmatch(phone):
        raise ValueError("Điện thoại phải gồm 10 đến 11 chữ số.")
    if email and (len(email) > 50 or not EMAIL_PATTERN.fullmatch(email)):
        raise ValueError("Email không hợp lệ hoặc dài quá 50 ký tự.")
    _, login_name, password, role_name = validate_account_input(
        1, login_name, password, role_name
    )
    return {
        "family_name": family_name,
        "given_name": given_name,
        "gender": bool(gender),
        "address": address,
        "phone": phone,
        "email": email,
        "login_name": login_name,
        "password": password,
        "role_name": role_name,
    }


def _fetch_employee_accounts(without_account_only: bool = False) -> List[Dict[str, Any]]:
    """Run sp_DanhSachTaiKhoanNhanVien; filtering happens on SQL Server."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if without_account_only:
            cursor.execute("EXEC dbo.sp_DanhSachTaiKhoanNhanVien @ChuaCoTaiKhoan=?", 1)
        else:
            cursor.execute("EXEC dbo.sp_DanhSachTaiKhoanNhanVien")
        return [
            {
                "MANV": row[0],
                "HoTen": row[1],
                "Email": row[2] or "",
                "DaCoTaiKhoan": bool(row[3]),
                "LoginName": row[4] or "",
                "RoleName": row[5] or "",
            }
            for row in cursor.fetchall()
        ]


def list_employee_accounts() -> List[Dict[str, Any]]:
    return _fetch_employee_accounts()


def create_employee_account(
    employee_id: int, login_name: str, password: str, role_name: str
) -> None:
    employee_id, login_name, password, role_name = validate_account_input(
        employee_id, login_name, password, role_name
    )
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "EXEC dbo.sp_TaoTaiKhoanNhanVien @MANV=?, @LoginName=?, @Password=?, @RoleName=?",
            employee_id,
            login_name,
            password,
            role_name,
        )
        conn.commit()


def delete_employee_account(employee_id: int) -> None:
    try:
        employee_id = int(employee_id)
    except (TypeError, ValueError) as error:
        raise ValueError("Mã nhân viên phải là số nguyên hợp lệ.") from error
    if employee_id <= 0:
        raise ValueError("Mã nhân viên phải lớn hơn 0.")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("EXEC dbo.sp_XoaTaiKhoanNhanVien @MANV=?", employee_id)
        conn.commit()


LOGIN_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.]{2,49}$")
DEFAULT_RESET_PASSWORD = "123456"


def validate_login_name(login_name: str) -> str:
    """The manager types the login name; the app never builds it by concatenation."""
    login = (login_name or "").strip()
    if not LOGIN_PATTERN.fullmatch(login):
        raise ValueError(
            "Tên đăng nhập phải bắt đầu bằng chữ cái, dài 3-50 ký tự, "
            "chỉ gồm chữ, số, dấu chấm hoặc gạch dưới."
        )
    return login


def list_employees_without_account() -> List[Dict[str, Any]]:
    """Employees eligible for a new account (1 employee - 1 account).

    Reuses sp_DanhSachTaiKhoanNhanVien (EXECUTE AS OWNER) because reading other
    users from sys.database_principals needs elevated metadata visibility; a
    plain VIEW would see no accounts and list everyone as eligible.
    The "no account yet" filter runs on SQL Server (@ChuaCoTaiKhoan = 1).
    """
    return _fetch_employee_accounts(without_account_only=True)


def change_own_password(old_password: str, new_password: str, confirm_password: str) -> None:
    """Change the password of the CURRENTLY logged-in login (old password required)."""
    if not old_password:
        raise ValueError("Vui lòng nhập mật khẩu cũ.")
    if len(new_password) < 6:
        raise ValueError("Mật khẩu mới phải có ít nhất 6 ký tự.")
    if new_password != confirm_password:
        raise ValueError("Xác nhận mật khẩu mới không khớp.")
    if new_password == old_password:
        raise ValueError("Mật khẩu mới phải khác mật khẩu cũ.")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("EXEC dbo.sp_DoiMatKhau @OldPassword=?, @NewPassword=?",
                       old_password, new_password)
        conn.commit()
    # Every later query opens a new connection with the session password.
    CURRENT_SESSION["password"] = new_password


def reset_employee_password(login_name: str) -> str:
    """Manager resets another employee's password to the default value.

    The LoginName shown in the account list is passed straight to the stored
    procedure; SQL Server checks that it belongs to an employee account.
    """
    if not isinstance(login_name, str) or not login_name.strip():
        raise ValueError("Vui lòng chọn tài khoản cần reset mật khẩu.")
    login = login_name.strip()
    if len(login) > MAX_LOGIN_LENGTH:
        raise ValueError("Tên đăng nhập tối đa 128 ký tự.")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("EXEC dbo.sp_ResetMatKhauNhanVien @LoginName=?", login)
        conn.commit()
    return DEFAULT_RESET_PASSWORD


def change_account_role(employee_id: int, role_name: str) -> None:
    employee_id = _positive_id(employee_id)
    role = (role_name or "").strip().upper()
    if role not in VALID_ACCOUNT_ROLES:
        raise ValueError("Nhóm quyền chỉ có thể là THUTHU hoặc QUANLY.")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("EXEC dbo.sp_DoiNhomQuyenTaiKhoan @MANV=?, @RoleName=?", employee_id, role)
        conn.commit()


def _positive_id(employee_id: Any) -> int:
    try:
        value = int(employee_id)
    except (TypeError, ValueError) as error:
        raise ValueError("Mã nhân viên phải là số nguyên hợp lệ.") from error
    if value <= 0:
        raise ValueError("Mã nhân viên phải lớn hơn 0.")
    return value


def create_employee_with_account(
    family_name: str,
    given_name: str,
    gender: bool,
    address: str,
    phone: str,
    email: str,
    login_name: str,
    password: str,
    role_name: str,
) -> int:
    """Atomically create NHANVIEN and its SQL Server account."""
    data = validate_new_employee(
        family_name, given_name, gender, address, phone, email,
        login_name, password, role_name,
    )
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            EXEC dbo.sp_TaoNhanVienVaTaiKhoan
                @HONV=?, @TENNV=?, @GIOITINH=?, @DIACHI=?, @DIENTHOAI=?,
                @EMAIL=?, @LoginName=?, @Password=?, @RoleName=?
            """,
            data["family_name"], data["given_name"], data["gender"],
            data["address"] or None, data["phone"] or None, data["email"] or None,
            data["login_name"], data["password"], data["role_name"],
        )
        row = cursor.fetchone()
        if not row:
            conn.rollback()
            raise RuntimeError("Không nhận được mã nhân viên sau khi tạo.")
        conn.commit()
        return int(row[0])
