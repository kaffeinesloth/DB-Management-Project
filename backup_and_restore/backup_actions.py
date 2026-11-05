"""Backup and restore database operations (DAO layer).

Toàn bộ lệnh BACKUP / RESTORE được gửi qua một kết nối RIÊNG tới database
[master] với autocommit = True (BACKUP/RESTORE không được chạy trong
transaction) và query timeout = 300 giây.
"""

import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import pyodbc

from database import CURRENT_SESSION, get_connection

# Thư mục backup bên trong container SQL Server (Docker volume sqlserver-backups)
BACKUP_DIR = os.environ.get("BACKUP_DIR", "/var/opt/mssql/backups")

# Timeout (giây) cho các lệnh BACKUP / VERIFY / RESTORE
MAINTENANCE_TIMEOUT = 300

_SAFE_DB_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")


def _db_name() -> str:
    """Tên CSDL đang làm việc; được kiểm tra để ghép an toàn vào [..]."""
    name = CURRENT_SESSION.get("active_db") or "LibraryManagement"
    if not _SAFE_DB_NAME.match(name):
        raise ValueError(f"Tên CSDL không hợp lệ: {name!r}")
    return name


def get_backup_path() -> str:
    """Đường dẫn tệp .bak cố định, ví dụ /var/opt/mssql/backups/LibraryManagement.bak."""
    return f"{BACKUP_DIR.rstrip('/')}/{_db_name()}.bak"


def _open_master_connection() -> pyodbc.Connection:
    """Kết nối độc lập tới [master] dành cho BACKUP / RESTORE."""
    conn = get_connection(database="master")
    conn.autocommit = True
    conn.timeout = MAINTENANCE_TIMEOUT
    return conn


def _drain(cursor: pyodbc.Cursor) -> None:
    """Đọc hết các result set / thông báo của BACKUP-RESTORE.

    Nếu đóng cursor trước khi SQL Server gửi xong các thông báo tiến độ,
    lệnh BACKUP/RESTORE có thể bị hủy giữa chừng.
    """
    while cursor.nextset():
        pass


class BackupActions:
    """Các thao tác sao lưu và phục hồi CSDL SQL Server."""

    @staticmethod
    def get_backup_history() -> List[Dict[str, Any]]:
        """Đọc lịch sử sao lưu từ VIEW dbo.v_LichSuBackup (bản mới nhất ở đầu).

        Chỉ lấy các bản nằm trong tệp .bak cố định của ứng dụng, vì RESTORE
        dùng WITH FILE = position trên đúng tệp này.
        """
        query = """
            SELECT position, TenBanSaoLuu, DienGiai, NgayGioBackup,
                   KichThuocMB, NguoiSaoLuu, physical_device_name
            FROM dbo.v_LichSuBackup
            WHERE REPLACE(physical_device_name, '\', '/') = REPLACE(?, '\', '/')
            ORDER BY NgayGioBackup DESC, position DESC;
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (get_backup_path(),))
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def create_backup(overwrite_old: bool = False, description: str = "") -> str:
        """FULL BACKUP vào tệp cố định.

        overwrite_old = True  -> WITH FORMAT, INIT : xóa các bản cũ, bắt đầu lại từ Bản 1.
        overwrite_old = False -> WITH NOINIT       : nối tiếp bản mới vào cuối tệp.

        Trả về đường dẫn tệp .bak đã ghi.
        """
        db = _db_name()
        path = get_backup_path()
        note = (description or "").strip()
        stamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        name = (note or f"{db} - Full Backup {stamp}")[:128]
        desc = (note or f"Sao lưu toàn bộ CSDL {db} lúc {stamp}")[:255]

        if overwrite_old:
            options = f"FORMAT, INIT, MEDIANAME = N'{db}_Backup', "
        else:
            options = "NOINIT, "

        sql = f"""
            DECLARE @path NVARCHAR(260) = ?, @name NVARCHAR(128) = ?, @desc NVARCHAR(255) = ?;
            BACKUP DATABASE [{db}]
                TO DISK = @path
                WITH {options}NAME = @name, DESCRIPTION = @desc, CHECKSUM;
        """
        conn = _open_master_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (path, name, desc))
            _drain(cursor)
        finally:
            conn.close()
        return path

    @staticmethod
    def verify_backup(position: int) -> bool:
        """RESTORE VERIFYONLY ... WITH FILE = position. Ném lỗi nếu bản sao lưu hỏng."""
        pos = int(position)
        if pos < 1:
            raise ValueError("Vị trí bản sao lưu phải >= 1.")

        sql = """
            DECLARE @path NVARCHAR(260) = ?, @pos INT = ?;
            RESTORE VERIFYONLY FROM DISK = @path WITH FILE = @pos, CHECKSUM;
        """
        conn = _open_master_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (get_backup_path(), pos))
            _drain(cursor)
        finally:
            conn.close()
        return True

    @staticmethod
    def restore_backup(position: int) -> bool:
        """Phục hồi CSDL về bản sao lưu thứ `position` trong tệp .bak.

        Chạy từ [master] trên kết nối độc lập:
          1. ALTER DATABASE ... SET SINGLE_USER WITH ROLLBACK IMMEDIATE
          2. RESTORE DATABASE ... WITH FILE = position, REPLACE, RECOVERY
          3. ALTER DATABASE ... SET MULTI_USER
        Khối TRY...CATCH luôn trả CSDL về MULTI_USER nếu có lỗi giữa chừng.
        """
        pos = int(position)
        if pos < 1:
            raise ValueError("Vị trí bản sao lưu phải >= 1.")

        db = _db_name()
        sql = f"""
            SET NOCOUNT ON;
            DECLARE @path NVARCHAR(260) = ?, @pos INT = ?;
            BEGIN TRY
                ALTER DATABASE [{db}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;

                RESTORE DATABASE [{db}]
                    FROM DISK = @path
                    WITH FILE = @pos, REPLACE, RECOVERY;

                ALTER DATABASE [{db}] SET MULTI_USER;
            END TRY
            BEGIN CATCH
                BEGIN TRY
                    IF DB_ID(N'{db}') IS NOT NULL
                        ALTER DATABASE [{db}] SET MULTI_USER;
                END TRY
                BEGIN CATCH
                END CATCH;
                THROW;
            END CATCH;
        """
        conn = _open_master_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (get_backup_path(), pos))
            _drain(cursor)
        except Exception:
            # Lưới an toàn phía ứng dụng: nếu lỗi xảy ra ngoài khối CATCH
            # (mất kết nối, timeout...) vẫn cố mở lại MULTI_USER.
            BackupActions._ensure_multi_user(db)
            raise
        finally:
            conn.close()
        return True

    @staticmethod
    def _ensure_multi_user(db: str) -> None:
        try:
            conn = _open_master_connection()
        except Exception:
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_access_desc FROM sys.databases WHERE name = ?", (db,)
            )
            row = cursor.fetchone()
            if row and row[0] != "MULTI_USER":
                cursor.execute(f"ALTER DATABASE [{db}] SET MULTI_USER;")
        except Exception:
            pass
        finally:
            conn.close()
