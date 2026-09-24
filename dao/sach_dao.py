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
            SELECT s.MASACH, s.ISBN, i.TENSACH, 
                   ISNULL(tl.THELOAI, N'Chưa phân loại') AS THELOAI, 
                   ISNULL(tg.HOTENTG, N'Chưa rõ') AS HOTENTG,
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
    def search_sach(keyword: str) -> List[Dict[str, Any]]:
        """Tìm kiếm cuốn sách theo Mã sách, Tên sách, ISBN, Thể loại hoặc Tác giả."""
        pattern = f"%{keyword.strip()}%"
        query = """
            SELECT s.MASACH, s.ISBN, i.TENSACH, 
                   ISNULL(tl.THELOAI, N'Chưa phân loại') AS THELOAI, 
                   ISNULL(tg.HOTENTG, N'Chưa rõ') AS HOTENTG,
                   s.TINHTRANG, s.CHOMUON,
                   ISNULL(nt.KE + ' - ' + nt.MOTA, N'Chưa xếp') AS ViTri,
                   ISNULL(i.GIA, 0) AS GiaBia
            FROM dbo.SACH s
            INNER JOIN dbo.ISBN i ON s.ISBN = i.ISBN
            LEFT JOIN dbo.THELOAI tl ON i.MATL = tl.MATL
            LEFT JOIN dbo.TACGIA_SACH tgs ON i.ISBN = tgs.ISBN
            LEFT JOIN dbo.TACGIA tg ON tgs.MATACGIA = tg.MATACGIA
            LEFT JOIN dbo.NGANTU nt ON s.MANGANTU = nt.MANGANTU
            WHERE s.MASACH LIKE ? 
               OR i.TENSACH LIKE ? 
               OR s.ISBN LIKE ? 
               OR tl.THELOAI LIKE ? 
               OR tg.HOTENTG LIKE ?
            ORDER BY s.MASACH ASC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (pattern, pattern, pattern, pattern, pattern))
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_all_isbn() -> List[Dict[str, Any]]:
        """Lấy danh sách các đầu sách (ISBN) kèm số lượng cuốn."""
        query = """
            SELECT i.ISBN, i.TENSACH, i.KHOSACH, i.NOIDUNG, i.SOTRANG, i.GIA,
                   i.LANXUATBAN, i.NHAXB,
                   ISNULL(tl.THELOAI, N'Chưa phân loại') AS THELOAI, 
                   ISNULL(nn.NGONNGU, N'Chưa rõ') AS NGONNGU,
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
    def get_danh_muc_the_loai() -> List[Dict[str, Any]]:
        """Lấy danh mục các thể loại sách."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MATL, THELOAI FROM dbo.THELOAI ORDER BY THELOAI;")
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_danh_muc_ngan_tu() -> List[Dict[str, Any]]:
        """Lấy danh mục các ngăn tủ / kệ sách."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MANGANTU, KE, MOTA FROM dbo.NGANTU ORDER BY KE;")
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_danh_muc_tac_gia() -> List[Dict[str, Any]]:
        """Lấy danh mục tác giả."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MATACGIA, HOTENTG FROM dbo.TACGIA ORDER BY HOTENTG;")
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_danh_muc_ngon_ngu() -> List[Dict[str, Any]]:
        """Lấy danh mục ngôn ngữ."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MANGONNGU, NGONNGU FROM dbo.NGONNGU ORDER BY NGONNGU;")
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def kiem_tra_sach_cho_muon(masach: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Kiểm tra cuốn sách có đủ điều kiện cho mượn không:
        1. Tồn tại trong CSDL.
        2. TINHTRANG = 1 (Sách tốt, không hỏng).
        3. CHOMUON = 0 (Sách đang có sẵn trong kho, chưa ai mượn).
        """
        masach_str = str(masach).strip()
        query = """
            SELECT s.MASACH, s.ISBN, i.TENSACH, s.TINHTRANG, s.CHOMUON, ISNULL(i.GIA, 0) AS GiaBia
            FROM dbo.SACH s
            INNER JOIN dbo.ISBN i ON s.ISBN = i.ISBN
            WHERE s.MASACH = ?;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (masach_str,))
            row = cursor.fetchone()
            if not row:
                return False, f"Không tìm thấy mã sách '{masach_str}' trong hệ thống!", None

            info = {
                "MASACH": row[0],
                "ISBN": row[1],
                "TENSACH": row[2],
                "TINHTRANG": row[3],
                "CHOMUON": row[4],
                "GiaBia": row[5]
            }

            if info["TINHTRANG"] != 1:
                return False, f"Sách '{masach_str}' ({info['TENSACH']}) đang bị hư hỏng (TINHTRANG=0), không thể cho mượn!", info

            if info["CHOMUON"] == 1:
                return False, f"Sách '{masach_str}' ({info['TENSACH']}) hiện ĐANG ĐƯỢC MƯỢN bởi độc giả khác!", info

            return True, "Sách sẵn sàng cho mượn", info

    @staticmethod
    def them_dau_sach(data: Dict[str, Any], matacgia: Optional[int] = None) -> bool:
        """Thêm một đầu sách mới (ISBN) và gán tác giả."""
        query_isbn = """
            INSERT INTO dbo.ISBN (
                ISBN, TENSACH, KHOSACH, NOIDUNG, SOTRANG, GIA,
                HINHANHPATH, NGAYXUATBAN, LANXUATBAN, NHAXB, MANGONNGU, MATL
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query_isbn, (
                str(data["ISBN"]).strip(),
                str(data["TENSACH"]).strip(),
                data.get("KHOSACH"),
                data.get("NOIDUNG"),
                data.get("SOTRANG"),
                data.get("GIA"),
                data.get("HINHANHPATH"),
                data.get("NGAYXUATBAN"),
                data.get("LANXUATBAN", 1),
                data.get("NHAXB"),
                data.get("MANGONNGU"),
                data.get("MATL")
            ))
            if matacgia:
                cursor.execute(
                    "INSERT INTO dbo.TACGIA_SACH (MATACGIA, ISBN) VALUES (?, ?);",
                    (matacgia, str(data["ISBN"]).strip())
                )
            conn.commit()
            return True

    @staticmethod
    def them_cuon_sach(masach: str, isbn: str, mangantu: Optional[int] = None) -> bool:
        """Nhập thêm một cuốn sách vật lý mới vào kho."""
        query = """
            INSERT INTO dbo.SACH (MASACH, ISBN, TINHTRANG, CHOMUON, MANGANTU)
            VALUES (?, ?, 1, 0, ?);
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(masach).strip(), str(isbn).strip(), mangantu))
            conn.commit()
            return True

    @staticmethod
    def cap_nhat_tinh_trang(masach: str, tinh_trang: int) -> bool:
        """Cập nhật tình trạng sách: 1 = Tốt/Bình thường, 0 = Hư hỏng/Hủy."""
        masach_str = str(masach).strip()
        tinh_trang_val = int(tinh_trang)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE dbo.SACH SET TINHTRANG = ? WHERE MASACH = ?;",
                (tinh_trang_val, masach_str)
            )
            conn.commit()
            return cursor.rowcount > 0
