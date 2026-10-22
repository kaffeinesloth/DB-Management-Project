"""Reader validation and database operations."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from database import get_connection


class ReaderActions:
    """Các thao tác nghiệp vụ và truy vấn CSDL liên quan đến Độc Giả & Thẻ Thư Viện."""

    @staticmethod
    def get_all(limit: int = 100) -> List[Dict[str, Any]]:
        """Lấy danh sách tất cả độc giả trong hệ thống."""
        query = f"""
            SELECT TOP ({int(limit)})
                MADG, HODG, TENDG, EMAILDG, SOCMND, GIOITINH, 
                CONVERT(VARCHAR(10), NGAYSINH, 103) AS NgaySinh,
                DIACHI, DIENTHOAI, 
                CONVERT(VARCHAR(10), NGAYLAMTHE, 103) AS NgayLamThe,
                CONVERT(VARCHAR(10), NGAYHETHAN, 103) AS NgayHetHan,
                HOATDONG
            FROM dbo.DOCGIA
            ORDER BY MADG DESC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def search(keyword: str) -> List[Dict[str, Any]]:
        """Tìm kiếm độc giả theo Tên, Họ, CMND/CCCD hoặc Số điện thoại."""
        pattern = f"%{keyword.strip()}%"
        query = """
            SELECT MADG, HODG, TENDG, EMAILDG, SOCMND, GIOITINH, 
                   CONVERT(VARCHAR(10), NGAYSINH, 103) AS NgaySinh,
                   DIACHI, DIENTHOAI, 
                   CONVERT(VARCHAR(10), NGAYLAMTHE, 103) AS NgayLamThe,
                   CONVERT(VARCHAR(10), NGAYHETHAN, 103) AS NgayHetHan,
                   HOATDONG
            FROM dbo.DOCGIA
            WHERE TENDG LIKE ? 
               OR HODG LIKE ? 
               OR SOCMND LIKE ? 
               OR DIENTHOAI LIKE ?
               OR EMAILDG LIKE ?
            ORDER BY MADG DESC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (pattern, pattern, pattern, pattern, pattern))
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def check_cmnd_exists(socmnd: str, exclude_id: Optional[int] = None) -> bool:
        """Kiểm tra số CMND/CCCD đã tồn tại trên thẻ đang hoạt động hay chưa."""
        query = "SELECT COUNT(*) FROM dbo.DOCGIA WHERE SOCMND = ? AND HOATDONG = 1"
        params = [socmnd.strip()]
        if exclude_id:
            query += " AND MADG != ?"
            params.append(exclude_id)
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0] > 0

    @staticmethod
    def check_email_exists(email: str, exclude_id: Optional[int] = None) -> bool:
        """Kiểm tra email đã tồn tại trên thẻ đang hoạt động hay chưa."""
        if not email or not email.strip():
            return False
        query = "SELECT COUNT(*) FROM dbo.DOCGIA WHERE EMAILDG = ? AND HOATDONG = 1"
        params = [email.strip()]
        if exclude_id:
            query += " AND MADG != ?"
            params.append(exclude_id)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0] > 0

    @staticmethod
    def insert(data: Dict[str, Any]) -> int:
        """Thêm mới độc giả vào CSDL. Trả về MADG vừa được tạo tự động."""
        query = """
            INSERT INTO dbo.DOCGIA (
                HODG, TENDG, EMAILDG, SOCMND, GIOITINH, 
                NGAYSINH, DIACHI, DIENTHOAI, NGAYLAMTHE, NGAYHETHAN, HOATDONG
            )
            OUTPUT INSERTED.MADG
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                data["HODG"],
                data["TENDG"],
                data.get("EMAILDG"),
                data.get("SOCMND"),
                data.get("GIOITINH", 1),
                data.get("NGAYSINH"),
                data.get("DIACHI"),
                data.get("DIENTHOAI"),
                data.get("NGAYLAMTHE", datetime.now()),
                data.get("NGAYHETHAN"),
                data.get("HOATDONG", 1)
            ))
            new_id = cursor.fetchone()[0]
            conn.commit()
            return new_id

    @staticmethod
    def gia_han_the(madg: int, so_thang: int = 12) -> bool:
        """Gia hạn thẻ thêm số tháng quy định."""
        query = """
            UPDATE dbo.DOCGIA
            SET NGAYHETHAN = DATEADD(MONTH, ?, 
                CASE 
                    WHEN NGAYHETHAN IS NULL OR NGAYHETHAN < GETDATE() THEN GETDATE()
                    ELSE NGAYHETHAN 
                END
            ),
            HOATDONG = 1
            WHERE MADG = ?;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (so_thang, madg))
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def toggle_trang_thai(madg: int, hoat_dong: bool) -> bool:
        """Bật/tắt trạng thái hoạt động của thẻ độc giả."""
        query = "UPDATE dbo.DOCGIA SET HOATDONG = ? WHERE MADG = ?;"
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (1 if hoat_dong else 0, madg))
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def cap_lai_the_mat(old_madg: int, new_data: Dict[str, Any]) -> int:
        """Nghiệp vụ mất thẻ: Khóa thẻ cũ và cấp thẻ mới với MADG mới."""
        query_deactivate = "UPDATE dbo.DOCGIA SET HOATDONG = 0 WHERE MADG = ?;"
        query_insert = """
            INSERT INTO dbo.DOCGIA (
                HODG, TENDG, EMAILDG, SOCMND, GIOITINH, 
                NGAYSINH, DIACHI, DIENTHOAI, NGAYLAMTHE, NGAYHETHAN, HOATDONG
            )
            OUTPUT INSERTED.MADG
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query_deactivate, (old_madg,))
            cursor.execute(query_insert, (
                new_data["HODG"],
                new_data["TENDG"],
                new_data.get("EMAILDG"),
                new_data.get("SOCMND"),
                new_data.get("GIOITINH", 1),
                new_data.get("NGAYSINH"),
                new_data.get("DIACHI"),
                new_data.get("DIENTHOAI"),
                new_data.get("NGAYLAMTHE", datetime.now()),
                new_data.get("NGAYHETHAN")
            ))
            new_id = cursor.fetchone()[0]
            conn.commit()
            return new_id

    @staticmethod
    def kiem_tra_the_hop_le_muon_sach(madg: int) -> tuple[bool, str, int]:
        """
        Kiểm tra tính hợp lệ của thẻ độc giả trước khi cho mượn sách:
        1. Thẻ tồn tại.
        2. Thẻ đang hoạt động (HOATDONG = 1).
        3. Thẻ còn hạn (NGAYHETHAN >= GETDATE()).
        4. Số sách chưa trả < 3.
        """
        query_card = """
            SELECT HOATDONG, 
                   CASE WHEN NGAYHETHAN IS NOT NULL AND NGAYHETHAN < GETDATE() THEN 1 ELSE 0 END AS DaHetHan,
                   CONVERT(VARCHAR(10), NGAYHETHAN, 103) AS NgayHetHanStr
            FROM dbo.DOCGIA
            WHERE MADG = ?;
        """
        query_borrowed_count = """
            SELECT COUNT(*)
            FROM dbo.CT_PHIEUMUON ct
            INNER JOIN dbo.PHIEUMUON pm ON ct.MAPHIEU = pm.MAPHIEU
            WHERE pm.MADG = ? AND ct.TRA = 0;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query_card, (madg,))
            row_card = cursor.fetchone()
            if not row_card:
                return False, f"Không tìm thấy thẻ độc giả mã {madg}!", 0

            hoat_dong, da_het_han, ngay_het_han_str = row_card[0], row_card[1], row_card[2]

            if not hoat_dong:
                return False, "Thẻ độc giả đang bị KHÓA! Không thể mượn sách.", 0

            if da_het_han:
                return False, f"Thẻ độc giả đã HẾT HẠN sử dụng từ ngày {ngay_het_han_str}! Vui lòng gia hạn thẻ.", 0

            cursor.execute(query_borrowed_count, (madg,))
            so_sach_dang_giu = cursor.fetchone()[0]

            if so_sach_dang_giu >= 3:
                return False, f"Độc giả đang mượn {so_sach_dang_giu} cuốn sách chưa trả. Đã đạt mức tối đa (3 cuốn)!", so_sach_dang_giu

            return True, "Thẻ hợp lệ", so_sach_dang_giu


# Bí danh tương thích
DocGiaDAO = ReaderActions
