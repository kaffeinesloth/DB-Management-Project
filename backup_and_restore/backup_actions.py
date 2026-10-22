"""Backup and restore validation and database operations."""

import datetime
from typing import List, Dict, Any, Optional
from database import get_connection, CURRENT_SESSION


class BackupActions:
    """Các thao tác sao lưu và phục hồi CSDL SQL Server."""

    @staticmethod
    def create_backup(custom_name: Optional[str] = None) -> str:
        """
        Tạo một bản sao lưu (Full Database Backup).
        Sử dụng thư mục backup tiêu chuẩn của SQL Server (/var/opt/mssql/backups trên Docker).
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = custom_name.strip() if custom_name and custom_name.strip() else f"backup_library_{timestamp}.bak"
        if not file_name.endswith(".bak"):
            file_name += ".bak"

        db_name = CURRENT_SESSION.get("active_db", "LibraryManagement")
        backup_path = f"/var/opt/mssql/backups/{file_name}"

        query = f"""
            BACKUP DATABASE [{db_name}]
            TO DISK = N'{backup_path}'
            WITH FORMAT, INIT, NAME = N'Library-Full-Backup-{timestamp}', SKIP, NOREWIND, NOUNLOAD, STATS = 10;
        """
        # Backup yêu cầu quyền quản trị (SA / QUANLY)
        with get_connection() as conn:
            # Tắt autocommit để thực thi lệnh DDL Backup
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute(query)
            conn.autocommit = False

        return file_name

    @staticmethod
    def get_backup_history() -> List[Dict[str, Any]]:
        """Lấy lịch sử các bản sao lưu từ msdb."""
        query = """
            SELECT TOP 20
                bs.database_name,
                bmf.physical_device_name,
                bs.backup_start_date,
                bs.backup_finish_date,
                CAST(ROUND(bs.backup_size / 1024.0 / 1024.0, 2) AS NUMERIC(10, 2)) AS SizeMB,
                bs.user_name
            FROM msdb.dbo.backupset bs
            INNER JOIN msdb.dbo.backupmediafamily bmf ON bs.media_set_id = bmf.media_set_id
            WHERE bs.type = 'D'
            ORDER BY bs.backup_finish_date DESC;
        """
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                results = []
                for r in rows:
                    d = dict(zip(cols, r))
                    # Lấy tên file ngắn gọn từ đường dẫn
                    raw_path = str(d.get("physical_device_name", ""))
                    d["filename"] = raw_path.replace("\\", "/").split("/")[-1]
                    d["date_str"] = d["backup_finish_date"].strftime("%d/%m/%Y %H:%M:%S") if d.get("backup_finish_date") else ""
                    results.append(d)
                return results
        except Exception:
            return []

    @staticmethod
    def verify_backup(file_name: str) -> bool:
        """Kiểm tra tính toàn vẹn của tệp sao lưu."""
        backup_path = f"/var/opt/mssql/backups/{file_name.strip()}"
        query = f"RESTORE VERIFYONLY FROM DISK = N'{backup_path}';"
        with get_connection() as conn:
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute(query)
            conn.autocommit = False
            return True
