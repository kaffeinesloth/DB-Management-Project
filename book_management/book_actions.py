"""Book validation and database operations."""

from typing import List, Dict, Any, Optional
from database import get_connection


class BookActions:
    """Các thao tác nghiệp vụ và truy vấn CSDL liên quan đến Sách & Kho."""

    @staticmethod
    def get_danh_sach_sach(keyword: str = "") -> List[Dict[str, Any]]:
        """Lấy danh sách các cuốn sách vật lý (SACH) kèm thông tin chi tiết đầu sách (ISBN)."""
        pattern = f"%{keyword.strip()}%"
        query = """
            SELECT 
                s.MASACH,
                i.ISBN,
                i.TENSACH,
                ISNULL(tl.THELOAI, N'Chưa phân loại') AS TheLoai,
                ISNULL(i.GIA, 0) AS GiaBia,
                s.TINHTRANG,
                s.CHOMUON,
                ISNULL(nt.KE + ' - ' + nt.MOTA, N'Chưa xếp') AS ViTri
            FROM dbo.SACH s
            INNER JOIN dbo.ISBN i ON s.ISBN = i.ISBN
            LEFT JOIN dbo.THELOAI tl ON i.MATL = tl.MATL
            LEFT JOIN dbo.NGANTU nt ON s.MANGANTU = nt.MANGANTU
            WHERE s.MASACH LIKE ? 
               OR i.TENSACH LIKE ? 
               OR i.ISBN LIKE ?
            ORDER BY s.MASACH ASC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (pattern, pattern, pattern))
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_danh_sach_isbn(keyword: str = "") -> List[Dict[str, Any]]:
        """Lấy danh mục các đầu sách (ISBN)."""
        pattern = f"%{keyword.strip()}%"
        query = """
            SELECT 
                i.ISBN,
                i.TENSACH,
                tl.THELOAI,
                nn.NGONNGU,
                i.SOTRANG,
                i.GIA,
                i.NHAXB,
                i.LANXUATBAN,
                (SELECT COUNT(*) FROM dbo.SACH s WHERE s.ISBN = i.ISBN) AS TongBanSao,
                (SELECT COUNT(*) FROM dbo.SACH s WHERE s.ISBN = i.ISBN AND s.CHOMUON = 0 AND s.TINHTRANG = 1) AS BanSaoKhaDung
            FROM dbo.ISBN i
            LEFT JOIN dbo.THELOAI tl ON i.MATL = tl.MATL
            LEFT JOIN dbo.NGONNGU nn ON i.MANGONNGU = nn.MANGONNGU
            WHERE i.ISBN LIKE ? OR i.TENSACH LIKE ? OR i.NHAXB LIKE ?
            ORDER BY i.ISBN ASC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (pattern, pattern, pattern))
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

    @staticmethod
    def huy_cuon_sach(masach: str) -> bool:
        """Xóa hẳn cuốn sách khỏi cơ sở dữ liệu (thanh lý)."""
        masach_str = str(masach).strip()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT CHOMUON FROM dbo.SACH WHERE MASACH = ?;", (masach_str,))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Không tìm thấy cuốn sách này trong hệ thống!")
            if row[0] == 1:
                raise ValueError("Sách đang được mượn, không thể tiến hành hủy!")
            try:
                cursor.execute("DELETE FROM dbo.SACH WHERE MASACH = ?;", (masach_str,))
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                if 'REFERENCE constraint' in str(e) or 'FK_' in str(e):
                    raise ValueError("Không thể hủy sách do đã có lịch sử mượn trả (ràng buộc CSDL). Vui lòng dùng tính năng 'Báo Hỏng' thay thế!")
                raise e

    @staticmethod
    def get_danh_sach_sach_san_sang() -> List[Dict[str, Any]]:
        """Lấy danh sách các cuốn sách vật lý đang sẵn sàng cho mượn (CHOMUON = 0 AND TINHTRANG = 1)."""
        query = """
            SELECT s.MASACH, i.TENSACH, s.ISBN, ISNULL(i.GIA, 0) AS GiaBia,
                   ISNULL(nt.KE + ' - ' + nt.MOTA, N'Chưa xếp') AS ViTri
            FROM dbo.SACH s
            INNER JOIN dbo.ISBN i ON s.ISBN = i.ISBN
            LEFT JOIN dbo.NGANTU nt ON s.MANGANTU = nt.MANGANTU
            WHERE s.CHOMUON = 0 AND s.TINHTRANG = 1
            ORDER BY i.TENSACH ASC, s.MASACH ASC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]


# Bí danh tương thích ngược
SachDAO = BookActions
