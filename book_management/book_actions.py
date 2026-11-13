"""Book validation and database operations."""

from typing import List, Dict, Any, Optional
from database import get_connection, friendly_message


class BookActions:
    """Các thao tác nghiệp vụ và truy vấn CSDL liên quan đến Sách & Kho."""

    @staticmethod
    def get_all_sach() -> List[Dict[str, Any]]:
        """Lấy toàn bộ danh sách sách vật lý trong kho."""
        return BookActions.get_danh_sach_sach()

    @staticmethod
    def search_sach(keyword: str) -> List[Dict[str, Any]]:
        """Tìm kiếm sách theo từ khóa (Mã sách, Tên sách, ISBN)."""
        return BookActions.get_danh_sach_sach(keyword)

    @staticmethod
    def get_all_isbn() -> List[Dict[str, Any]]:
        """Lấy toàn bộ danh mục đầu sách (ISBN)."""
        return BookActions.get_danh_sach_isbn()

    @staticmethod
    def search_isbn(keyword: str) -> List[Dict[str, Any]]:
        """Tìm kiếm đầu sách (ISBN) theo từ khóa."""
        return BookActions.get_danh_sach_isbn(keyword)

    @staticmethod
    def get_danh_sach_sach(keyword: str = "") -> List[Dict[str, Any]]:
        """Lấy danh sách các cuốn sách vật lý (SACH) kèm thông tin chi tiết đầu sách (ISBN), tác giả và thể loại."""
        pattern = f"%{keyword.strip()}%"
        query = """
            SELECT 
                s.MASACH,
                s.ISBN,
                i.TENSACH,
                ISNULL(tl.THELOAI, N'Chưa phân loại') AS THELOAI,
                ISNULL((
                    SELECT STRING_AGG(tg.HOTENTG, ', ') 
                    FROM dbo.TACGIA_SACH tgs 
                    JOIN dbo.TACGIA tg ON tgs.MATACGIA = tg.MATACGIA 
                    WHERE tgs.ISBN = s.ISBN
                ), N'Chưa rõ') AS HOTENTG,
                s.TINHTRANG,
                s.CHOMUON,
                s.MANGANTU,
                ISNULL(nt.KE + ' - ' + nt.MOTA, N'Chưa xếp') AS ViTri,
                ISNULL(i.GIA, 0) AS GiaBia
            FROM dbo.SACH s
            INNER JOIN dbo.ISBN i ON s.ISBN = i.ISBN
            LEFT JOIN dbo.THELOAI tl ON i.MATL = tl.MATL
            LEFT JOIN dbo.NGANTU nt ON s.MANGANTU = nt.MANGANTU
            WHERE s.MASACH LIKE ? 
               OR i.TENSACH LIKE ? 
               OR s.ISBN LIKE ?
               OR tl.THELOAI LIKE ?
               OR EXISTS (
                   SELECT 1 FROM dbo.TACGIA_SACH tgs2 
                   JOIN dbo.TACGIA tg2 ON tgs2.MATACGIA = tg2.MATACGIA 
                   WHERE tgs2.ISBN = s.ISBN AND tg2.HOTENTG LIKE ?
               )
            ORDER BY s.MASACH ASC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (pattern, pattern, pattern, pattern, pattern))
            cols = [col[0] for col in cursor.description]
            records = [dict(zip(cols, row)) for row in cursor.fetchall()]
            for r in records:
                r["TheLoai"] = r["THELOAI"]
                r["HoTenTG"] = r["HOTENTG"]
            return records

    @staticmethod
    def get_danh_sach_isbn(keyword: str = "") -> List[Dict[str, Any]]:
        """Lấy danh mục các đầu sách (ISBN) kèm tác giả và thống kê số bản sao vật lý."""
        pattern = f"%{keyword.strip()}%"
        query = """
            WITH SachStats AS (
                SELECT
                    s.ISBN,
                    COUNT(*) AS TongBanSao,
                    SUM(CASE WHEN s.CHOMUON = 0 AND s.TINHTRANG = 1 THEN 1 ELSE 0 END) AS BanSaoKhaDung
                FROM dbo.SACH s
                GROUP BY s.ISBN
            )
            SELECT 
                RTRIM(i.ISBN) AS ISBN,
                i.TENSACH,
                ISNULL(tl.THELOAI, N'Chưa phân loại') AS THELOAI,
                ISNULL((
                    SELECT STRING_AGG(tg.HOTENTG, ', ')
                    FROM dbo.TACGIA_SACH tgs
                    JOIN dbo.TACGIA tg ON tgs.MATACGIA = tg.MATACGIA
                    WHERE tgs.ISBN = i.ISBN
                ), N'Chưa rõ') AS HOTENTG,
                ISNULL(nn.NGONNGU, N'Chưa rõ') AS NGONNGU,
                i.SOTRANG,
                ISNULL(i.GIA, 0) AS GIA,
                ISNULL(i.GIA, 0) AS GiaBia,
                ISNULL(i.NHAXB, N'') AS NHAXB,
                i.LANXUATBAN,
                ISNULL(st.TongBanSao, 0) AS TongBanSao,
                ISNULL(st.BanSaoKhaDung, 0) AS BanSaoKhaDung
            FROM dbo.ISBN i
            LEFT JOIN dbo.THELOAI tl ON i.MATL = tl.MATL
            LEFT JOIN dbo.NGONNGU nn ON i.MANGONNGU = nn.MANGONNGU
            LEFT JOIN SachStats st ON st.ISBN = i.ISBN
            WHERE i.ISBN LIKE ?
               OR i.TENSACH LIKE ?
               OR i.NHAXB LIKE ?
               OR tl.THELOAI LIKE ?
               OR EXISTS (
                   SELECT 1 FROM dbo.TACGIA_SACH tgs2
                   JOIN dbo.TACGIA tg2 ON tgs2.MATACGIA = tg2.MATACGIA
                   WHERE tgs2.ISBN = i.ISBN AND tg2.HOTENTG LIKE ?
               )
            ORDER BY i.ISBN ASC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (pattern, pattern, pattern, pattern, pattern))
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

    # ------------------------------------------------------------ helpers
    @staticmethod
    def _run_write(statements: List[tuple], entity: str) -> int:
        """Run parameterized write statements in ONE transaction.

        Returns the rowcount of the last statement. SQL Server errors are mapped by
        native error code (547 FK, 2627 PK, 2628 truncation, 229 permission) to a
        ValueError with a Vietnamese message; anything else is re-raised unchanged.
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            rowcount = 0
            for sql, params in statements:
                cursor.execute(sql, params)
                rowcount = cursor.rowcount
            conn.commit()
            return rowcount
        except Exception as error:
            conn.rollback()
            message = friendly_message(error, entity)
            if message:
                raise ValueError(message) from error
            raise
        finally:
            conn.close()

    @staticmethod
    def validate_dau_sach(data: Dict[str, Any]) -> Dict[str, Any]:
        """Strip text fields and check required/length rules before touching SQL Server."""
        clean = {k: (v.strip() if isinstance(v, str) else v) for k, v in data.items()}
        for key in ("NHAXB", "KHOSACH", "NOIDUNG"):
            clean[key] = clean.get(key) or None
        if not clean.get("ISBN") or len(clean["ISBN"]) > 10:
            raise ValueError("Mã ISBN là bắt buộc và tối đa 10 ký tự!")
        if not clean.get("TENSACH"):
            raise ValueError("Tên đầu sách không được để trống!")
        if clean.get("GIA") is not None and int(clean["GIA"]) < 0:
            raise ValueError("Giá bìa không được âm!")
        return clean

    # ------------------------------------------------------------- ISBN
    @staticmethod
    def get_dau_sach(isbn: str) -> Optional[Dict[str, Any]]:
        """Chi tiết một đầu sách kèm tác giả chính (để nạp form Sửa)."""
        query = """
            SELECT i.ISBN, i.TENSACH, i.GIA, i.MATL, i.MANGONNGU, i.NHAXB, i.SOTRANG,
                   i.KHOSACH, i.LANXUATBAN, i.NOIDUNG,
                   (SELECT TOP (1) MATACGIA FROM dbo.TACGIA_SACH t
                    WHERE t.ISBN = i.ISBN ORDER BY MATACGIA) AS MATACGIA
            FROM dbo.ISBN i WHERE i.ISBN = ?;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(isbn).strip(),))
            row = cursor.fetchone()
            return dict(zip([c[0] for c in cursor.description], row)) if row else None

    @staticmethod
    def them_dau_sach(data: Dict[str, Any], matacgia: Optional[int] = None) -> bool:
        """Thêm một đầu sách mới (ISBN) và gán tác giả (một giao dịch)."""
        d = BookActions.validate_dau_sach(data)
        statements = [(
            """INSERT INTO dbo.ISBN (ISBN, TENSACH, KHOSACH, NOIDUNG, SOTRANG, GIA,
                   HINHANHPATH, NGAYXUATBAN, LANXUATBAN, NHAXB, MANGONNGU, MATL)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
            (d["ISBN"], d["TENSACH"], d.get("KHOSACH"), d.get("NOIDUNG"), d.get("SOTRANG"),
             d.get("GIA"), d.get("HINHANHPATH"), d.get("NGAYXUATBAN"), d.get("LANXUATBAN", 1),
             d.get("NHAXB"), d.get("MANGONNGU"), d.get("MATL")),
        )]
        if matacgia:
            statements.append(("INSERT INTO dbo.TACGIA_SACH (MATACGIA, ISBN) VALUES (?, ?);",
                               (matacgia, d["ISBN"])))
        BookActions._run_write(statements, "ISBN")
        return True

    @staticmethod
    def cap_nhat_dau_sach(data: Dict[str, Any], matacgia: Optional[int] = None) -> bool:
        """Sửa đầu sách (khóa chính ISBN không đổi) và tác giả chính."""
        d = BookActions.validate_dau_sach(data)
        statements = [(
            """UPDATE dbo.ISBN SET TENSACH = ?, GIA = ?, MATL = ?, MANGONNGU = ?, NHAXB = ?,
                   SOTRANG = ?, KHOSACH = ?, LANXUATBAN = ?, NOIDUNG = ?
               WHERE ISBN = ?;""",
            (d["TENSACH"], d.get("GIA"), d.get("MATL"), d.get("MANGONNGU"), d.get("NHAXB"),
             d.get("SOTRANG"), d.get("KHOSACH"), d.get("LANXUATBAN", 1), d.get("NOIDUNG"), d["ISBN"]),
        )]
        if matacgia:
            statements = [
                ("DELETE FROM dbo.TACGIA_SACH WHERE ISBN = ? AND MATACGIA <> ?;", (d["ISBN"], matacgia)),
                ("""IF NOT EXISTS (SELECT 1 FROM dbo.TACGIA_SACH WHERE ISBN = ? AND MATACGIA = ?)
                        INSERT INTO dbo.TACGIA_SACH (MATACGIA, ISBN) VALUES (?, ?);""",
                 (d["ISBN"], matacgia, matacgia, d["ISBN"])),
            ] + statements                       # UPDATE last -> its rowcount is returned
        if BookActions._run_write(statements, "ISBN") != 1:
            raise ValueError(f"Không tìm thấy đầu sách '{d['ISBN']}'; vui lòng làm mới danh sách!")
        return True

    @staticmethod
    def xoa_dau_sach(isbn: str) -> bool:
        """Xóa đầu sách. Còn cuốn sách vật lý thuộc ISBN này -> FK 547 -> báo lỗi thân thiện."""
        key = str(isbn).strip()
        rowcount = BookActions._run_write([
            ("DELETE FROM dbo.TACGIA_SACH WHERE ISBN = ?;", (key,)),
            ("DELETE FROM dbo.ISBN WHERE ISBN = ?;", (key,)),
        ], "ISBN")
        if rowcount != 1:
            raise ValueError(f"Không tìm thấy đầu sách '{key}'; vui lòng làm mới danh sách!")
        return True

    # ------------------------------------------------------------- SACH
    @staticmethod
    def them_cuon_sach(masach: str, isbn: str, mangantu: Optional[int] = None,
                       tinh_trang: int = 1) -> bool:
        """Nhập thêm một cuốn sách vật lý mới vào kho."""
        key = str(masach).strip()
        if not key or len(key) > 10:
            raise ValueError("Mã cuốn sách là bắt buộc và tối đa 10 ký tự!")
        BookActions._run_write([(
            "INSERT INTO dbo.SACH (MASACH, ISBN, TINHTRANG, CHOMUON, MANGANTU) VALUES (?, ?, ?, 0, ?);",
            (key, str(isbn).strip(), int(tinh_trang), mangantu),
        )], "sách")
        return True

    @staticmethod
    def cap_nhat_cuon_sach(masach: str, isbn: str, mangantu: Optional[int], tinh_trang: int) -> bool:
        """Sửa cuốn sách (khóa chính MASACH không đổi)."""
        rowcount = BookActions._run_write([(
            "UPDATE dbo.SACH SET ISBN = ?, MANGANTU = ?, TINHTRANG = ? WHERE MASACH = ?;",
            (str(isbn).strip(), mangantu, int(tinh_trang), str(masach).strip()),
        )], "sách")
        if rowcount != 1:
            raise ValueError(f"Không tìm thấy cuốn sách '{masach}'; vui lòng làm mới danh sách!")
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
        """Xóa hẳn cuốn sách (thanh lý). Có lịch sử mượn -> FK 547 -> báo lỗi thân thiện."""
        masach_str = str(masach).strip()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT CHOMUON FROM dbo.SACH WHERE MASACH = ?;", (masach_str,))
            row = cursor.fetchone()
        if not row:
            raise ValueError("Không tìm thấy cuốn sách này trong hệ thống!")
        if row[0] == 1:
            raise ValueError("Sách đang được mượn, không thể tiến hành hủy!")
        return BookActions._run_write(
            [("DELETE FROM dbo.SACH WHERE MASACH = ?;", (masach_str,))], "sách") > 0

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
