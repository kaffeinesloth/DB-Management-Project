"""Database operations for employee SQL Server accounts."""

import re
from typing import Any, Dict, List

from database import get_connection


VALID_ACCOUNT_ROLES = {"THUTHU", "QUANLY"}
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^\d{10,11}$")


def validate_account_input(
    employee_id: int, login_name: str, password: str, role_name: str
) -> tuple[int, str, str, str]:
    """Validate and normalize account data before sending it to SQL Server."""
    try:
        normalized_id = int(employee_id)
    except (TypeError, ValueError) as error:
        raise ValueError("Mã nhân viên phải là số nguyên hợp lệ.") from error
    normalized_login = login_name.strip()
    normalized_role = role_name.strip().upper()
    if normalized_id <= 0:
        raise ValueError("Mã nhân viên phải lớn hơn 0.")
    if not normalized_login:
        raise ValueError("Tên đăng nhập không được để trống.")
    if len(password) < 6:
        raise ValueError("Mật khẩu phải có ít nhất 6 ký tự.")
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
    family_name = family_name.strip()
    given_name = given_name.strip()
    address = address.strip()
    phone = phone.strip()
    email = email.strip().lower()
    if not family_name or len(family_name) > 50:
        raise ValueError("Họ nhân viên là bắt buộc và tối đa 50 ký tự.")
    if not given_name or len(given_name) > 12:
        raise ValueError("Tên nhân viên là bắt buộc và tối đa 12 ký tự.")
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


def list_employee_accounts() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
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
        conn.commit()
        return int(row[0])
