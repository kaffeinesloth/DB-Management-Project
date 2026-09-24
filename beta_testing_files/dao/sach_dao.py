from typing import List, Dict, Any, Optional
from db import get_connection

class SachDAO:
    """
    Data Access Object (DAO) cho quản lý Đầu sách (ISBN) và Cuốn sách vật lý (SACH).
    """

    @staticmethod
    def get_all_sach() -> List[Dict[str, Any]]:
        """Lấy danh sách tất cả các cuốn sách vật lý kèm thông tin đầu sách, vị trí ngăn tủ."""
        query = """
            SELECT s.MASACH, s.ISBN, i.TENSACH, tl.THELOAI, tg.HOTENTG,
                   s.TINHTRANG, s.CHOMUON,
                   ISNULL(nt.KE + ' - ' + nt.MOTA, N'Chưa xếp') AS ViTri,
                   ISNULL(i.GIA, 0) AS GiaBia
            FROM dbo.SACH s
            INNER JOIN dbo.ISBN i ON s.ISBN = i.ISBN
            LEFT JOIN dbo.THELOAI tl ON i.MATL = tl.MATL
            LEFT JOIN dbo.TACGIA_SACH tgs ON i.ISBN = tgs.ISBN
            LEFT JOIN dbo.TACGIA tg ON tgs.MATACGIA = tg.MATACGIA
            LEFT JOIN dbo.NGANTU nt ON s.MANGANTU = nt.MANGANTU
            ORDER BY s.MASACH ASC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_all_isbn() -> List[Dict[str, Any]]:
        """Lấy danh sách các đầu sách (ISBN)."""
        query = """
            SELECT i.ISBN, i.TENSACH, i.KHOSACH, i.NOIDUNG, i.SOTRANG, i.GIA,
                   i.LANXUATBAN, i.NHAXB,
                   tl.THELOAI, nn.NGONNGU,
                   (SELECT COUNT(*) FROM dbo.SACH s WHERE s.ISBN = i.ISBN) AS TongSoCuon,
                   (SELECT COUNT(*) FROM dbo.SACH s WHERE s.ISBN = i.ISBN AND s.CHOMUON = 0 AND s.TINHTRANG = 1) AS SanCo
            FROM dbo.ISBN i
            LEFT JOIN dbo.THELOAI tl ON i.MATL = tl.MATL
            LEFT JOIN dbo.NGONNGU nn ON i.MANGONNGU = nn.MANGONNGU
            ORDER BY i.ISBN ASC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def kiem_tra_sach_cho_muon(masach: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Kiểm tra cuốn sách có đủ điều kiện cho mượn không:
        1. Tồn tại trong CSDL.
        2. TINHTRANG = 1 (Sách tốt, không hỏng).
        3. CHOMUON = 0 (Sách đang có sẵn trong kho, chưa ai mượn).
        Trả về: (du_dieu_kien, thong_bao, thong_tin_sach)
        """
        query = """
            SELECT s.MASACH, s.ISBN, i.TENSACH, s.TINHTRANG, s.CHOMUON, ISNULL(i.GIA, 0) AS GiaBia
            FROM dbo.SACH s
            INNER JOIN dbo.ISBN i ON s.ISBN = i.ISBN
            WHERE s.MASACH = ?;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (masach.strip(),))
            row = cursor.fetchone()
            if not row:
                return False, f"Không tìm thấy mã sách '{masach}' trong hệ thống!", None

            info = {
                "MASACH": row[0],
                "ISBN": row[1],
                "TENSACH": row[2],
                "TINHTRANG": row[3],
                "CHOMUON": row[4],
                "GiaBia": row[5]
            }

            if info["TINHTRANG"] != 1:
                return False, f"Sách '{masach}' ({info['TENSACH']}) đang bị hư hỏng (TINHTRANG=0), không thể cho mượn!", info

            if info["CHOMUON"] == 1:
                return False, f"Sách '{masach}' ({info['TENSACH']}) hiện ĐANG ĐƯỢC MƯỢN bởi độc giả khác!", info

            return True, "Sách sẵn sàng cho mượn", info
