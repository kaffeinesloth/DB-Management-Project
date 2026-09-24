"""Read the authenticated SQL Server identity and build an application session."""

from __future__ import annotations

from typing import NoReturn

import pyodbc

from database.connection import open_user_connection
from models.session import UserSession


class LoginDemoError(Exception):
    """A safe, user-facing login error."""


class BadCredentialsError(LoginDemoError):
    pass


class ServerUnavailableError(LoginDemoError):
    pass


class DatabaseUnavailableError(LoginDemoError):
    pass


class DatabaseUserMissingError(LoginDemoError):
    pass


class InvalidEmployeeMappingError(LoginDemoError):
    pass


class EmployeeNotFoundError(LoginDemoError):
    pass


class NoApplicationRoleError(LoginDemoError):
    pass


def _error_text(error: pyodbc.Error) -> str:
    return " ".join(str(part) for part in error.args).lower()


def _raise_connection_error(error: pyodbc.Error) -> NoReturn:
    """Translate driver details into messages that are safe for the UI."""
    detail = _error_text(error)

    if "18456" in detail or "login failed" in detail:
        raise BadCredentialsError(
            "Tên đăng nhập hoặc mật khẩu SQL Server không đúng."
        ) from error

    if "4060" in detail or "cannot open database" in detail:
        raise DatabaseUnavailableError(
            "Không thể mở cơ sở dữ liệu đã cấu hình. Hãy kiểm tra tên database "
            "và quyền truy cập của tài khoản."
        ) from error

    raise ServerUnavailableError(
        "Không thể kết nối tới SQL Server. Hãy kiểm tra tên server, dịch vụ "
        "SQL Server, driver ODBC và kết nối mạng."
    ) from error


def _read_identity(connection: pyodbc.Connection) -> tuple[str, str, str]:
    cursor = connection.cursor()
    cursor.execute(
        "SELECT ORIGINAL_LOGIN() AS original_login, "
        "SUSER_SNAME() AS current_login, USER_NAME() AS database_user;"
    )
    row = cursor.fetchone()

    if row is None or row[2] in (None, "guest"):
        raise DatabaseUserMissingError(
            "Login đã được SQL Server xác thực nhưng chưa có database user hợp lệ."
        )

    return str(row[0]), str(row[1]), str(row[2])


def _read_roles(connection: pyodbc.Connection) -> list[str]:
    """Return direct, non-public, non-fixed database role memberships."""
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT role_principal.name
        FROM sys.database_role_members AS membership
        INNER JOIN sys.database_principals AS role_principal
            ON role_principal.principal_id = membership.role_principal_id
        INNER JOIN sys.database_principals AS member_principal
            ON member_principal.principal_id = membership.member_principal_id
        WHERE member_principal.principal_id = USER_ID()
          AND role_principal.name <> N'public'
          AND role_principal.is_fixed_role = 0
        ORDER BY role_principal.name;
        """
    )
    return [str(row[0]) for row in cursor.fetchall()]


def _read_employee(
    connection: pyodbc.Connection, original_login: str
) -> tuple[int, str]:
    """Map the authenticated SQL login to NHANVIEN.MANV."""
    try:
        employee_id = int(original_login)
    except (TypeError, ValueError) as error:
        raise InvalidEmployeeMappingError(
            "Login SQL phải trùng với MANV dạng số (ví dụ: login [1] cho MANV 1)."
        ) from error

    if employee_id <= 0 or str(employee_id) != original_login.strip():
        raise InvalidEmployeeMappingError(
            "Login SQL phải trùng chính xác với MANV dạng số."
        )

    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT MANV, HONV, TENNV
        FROM dbo.NHANVIEN
        WHERE MANV = ?;
        """,
        (employee_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise EmployeeNotFoundError(
            f"Không tìm thấy nhân viên có MANV = {employee_id}."
        )

    full_name = " ".join(
        part.strip() for part in (str(row[1] or ""), str(row[2] or "")) if part.strip()
    )
    return int(row[0]), full_name or "(Chưa có họ tên)"


def authenticate(login_name: str, password: str) -> tuple[UserSession, pyodbc.Connection]:
    """Authenticate once and keep that same connection for the whole session."""
    try:
        connection = open_user_connection(login_name, password)
    except pyodbc.Error as error:
        _raise_connection_error(error)

    try:
        original_login, _current_login, database_user = _read_identity(connection)
        roles = _read_roles(connection)
        if not roles:
            raise NoApplicationRoleError(
                "Database user chưa thuộc application role nào."
            )

        employee_id, full_name = _read_employee(connection, original_login)
        session = UserSession(
            login_name=original_login,
            database_user=database_user,
            employee_id=employee_id,
            full_name=full_name,
            roles=roles,
        )
        return session, connection
    except LoginDemoError:
        connection.close()
        raise
    except pyodbc.Error as error:
        connection.close()
        detail = _error_text(error)
        if "916" in detail or "database principal" in detail:
            raise DatabaseUserMissingError(
                "Login chưa được ánh xạ đúng tới database user."
            ) from error
        raise LoginDemoError(
            "Đăng nhập thành công nhưng không thể đọc thông tin bảo mật hoặc nhân viên."
        ) from error
    except Exception as error:
        connection.close()
        raise LoginDemoError(
            "Đã xảy ra lỗi khi tạo phiên đăng nhập."
        ) from error

