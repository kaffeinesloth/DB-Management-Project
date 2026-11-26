"""Book validation and database operations.

Every database operation calls a stored procedure in sql/08_server_side_crud.sql
(server-side processing). Python validates input for friendly UI messages and
sends EXEC; searching, joins, counts, transactions and state checks run on SQL Server.
"""

from typing import List, Dict, Any, Optional
from database import call_one, call_rows, call_write, friendly_message


class BookActions:
    """Các thao tác nghiệp vụ Sách & Kho, gọi Stored Procedure trên SQL Server."""

    # ------------------------------------------------------------- reads
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
        """Cuốn sách vật lý kèm đầu sách, thể loại, tác giả, vị trí (sp_Sach_DanhSach)."""
        return call_rows("EXEC dbo.sp_Sach_DanhSach @Keyword=?", ((keyword or "").strip(),))

    @staticmethod
    def get_danh_sach_isbn(keyword: str = "") -> List[Dict[str, Any]]:
        """Đầu sách kèm tác giả và số bản sao (sp_DauSach_DanhSach)."""
        return call_rows("EXEC dbo.sp_DauSach_DanhSach @Keyword=?", ((keyword or "").strip(),))

    @staticmethod
    def get_danh_muc_the_loai() -> List[Dict[str, Any]]:
        """Lấy danh mục các thể loại sách."""
        return call_rows("EXEC dbo.sp_DanhMuc_TheLoai")

    @staticmethod
    def get_danh_muc_ngan_tu() -> List[Dict[str, Any]]:
        """Lấy danh mục các ngăn tủ / kệ sách."""
        return call_rows("EXEC dbo.sp_DanhMuc_NganTu")

    @staticmethod
    def get_danh_muc_tac_gia() -> List[Dict[str, Any]]:
        """Lấy danh mục tác giả."""
        return call_rows("EXEC dbo.sp_DanhMuc_TacGia")

    @staticmethod
    def get_danh_muc_ngon_ngu() -> List[Dict[str, Any]]:
        """Lấy danh mục ngôn ngữ."""
        return call_rows("EXEC dbo.sp_DanhMuc_NgonNgu")

    @staticmethod
    def kiem_tra_sach_cho_muon(masach: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Kiểm tra cuốn sách có đủ điều kiện cho mượn không:
        1. Tồn tại trong CSDL.
        2. TINHTRANG = 1 (Sách tốt, không hỏng).
        3. CHOMUON = 0 (Sách đang có sẵn trong kho, chưa ai mượn).
        """
        masach_str = str(masach).strip()
        info = call_one("EXEC dbo.sp_Sach_KiemTraChoMuon @MASACH=?", (masach_str,))
        if not info:
            return False, f"Không tìm thấy mã sách '{masach_str}' trong hệ thống!", None
        if info["TINHTRANG"] != 1:
            return False, f"Sách '{masach_str}' ({info['TENSACH']}) đang bị hư hỏng (TINHTRANG=0), không thể cho mượn!", info
        if info["CHOMUON"] == 1:
            return False, f"Sách '{masach_str}' ({info['TENSACH']}) hiện ĐANG ĐƯỢC MƯỢN bởi độc giả khác!", info
        return True, "Sách sẵn sàng cho mượn", info

    @staticmethod
    def get_danh_sach_sach_san_sang() -> List[Dict[str, Any]]:
        """Cuốn sách đang sẵn sàng cho mượn (CHOMUON = 0 AND TINHTRANG = 1), lọc trên server."""
        return call_rows("EXEC dbo.sp_Sach_SanSangChoMuon")

    @staticmethod
    def get_dau_sach(isbn: str) -> Optional[Dict[str, Any]]:
        """Chi tiết một đầu sách kèm tác giả chính (để nạp form Sửa)."""
        return call_one("EXEC dbo.sp_DauSach_ChiTiet @ISBN=?", (str(isbn).strip(),))

    # ------------------------------------------------------------ helpers
    @staticmethod
    def _run_write(sql: str, params: tuple, entity: str) -> None:
        """Run ONE writing stored procedure (it owns its transaction).

        SQL Server errors are mapped by native error code (THROW 5xxxx business
        rule, 547 FK, 2627 PK, 2628 truncation, 229 permission) to a ValueError
        with a Vietnamese message; anything else is re-raised unchanged.
        """
        try:
            call_write(sql, params)
        except Exception as error:
            message = friendly_message(error, entity)
            if message:
                raise ValueError(message) from error
            raise

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
    def them_dau_sach(data: Dict[str, Any], matacgia: Optional[int] = None) -> bool:
        """Thêm một đầu sách mới (ISBN) và gán tác giả (một giao dịch trong SP)."""
        d = BookActions.validate_dau_sach(data)
        BookActions._run_write(
            "EXEC dbo.sp_DauSach_Them @ISBN=?, @TENSACH=?, @KHOSACH=?, @NOIDUNG=?, @SOTRANG=?, "
            "@GIA=?, @HINHANHPATH=?, @NGAYXUATBAN=?, @LANXUATBAN=?, @NHAXB=?, @MANGONNGU=?, "
            "@MATL=?, @MATACGIA=?",
            (d["ISBN"], d["TENSACH"], d.get("KHOSACH"), d.get("NOIDUNG"), d.get("SOTRANG"),
             d.get("GIA"), d.get("HINHANHPATH"), d.get("NGAYXUATBAN"), d.get("LANXUATBAN", 1),
             d.get("NHAXB"), d.get("MANGONNGU"), d.get("MATL"), matacgia or None),
            "ISBN",
        )
        return True

    @staticmethod
    def cap_nhat_dau_sach(data: Dict[str, Any], matacgia: Optional[int] = None) -> bool:
        """Sửa đầu sách (khóa chính ISBN không đổi) và tác giả chính."""
        d = BookActions.validate_dau_sach(data)
        BookActions._run_write(
            "EXEC dbo.sp_DauSach_CapNhat @ISBN=?, @TENSACH=?, @GIA=?, @MATL=?, @MANGONNGU=?, "
            "@NHAXB=?, @SOTRANG=?, @KHOSACH=?, @LANXUATBAN=?, @NOIDUNG=?, @MATACGIA=?",
            (d["ISBN"], d["TENSACH"], d.get("GIA"), d.get("MATL"), d.get("MANGONNGU"),
             d.get("NHAXB"), d.get("SOTRANG"), d.get("KHOSACH"), d.get("LANXUATBAN", 1),
             d.get("NOIDUNG"), matacgia or None),
            "ISBN",
        )
        return True

    @staticmethod
    def xoa_dau_sach(isbn: str) -> bool:
        """Xóa đầu sách. Còn cuốn sách vật lý thuộc ISBN này -> FK 547 -> báo lỗi thân thiện."""
        BookActions._run_write("EXEC dbo.sp_DauSach_Xoa @ISBN=?", (str(isbn).strip(),), "ISBN")
        return True

    # ------------------------------------------------------------- SACH
    @staticmethod
    def them_cuon_sach(masach: str, isbn: str, mangantu: Optional[int] = None,
                       tinh_trang: int = 1) -> bool:
        """Nhập thêm một cuốn sách vật lý mới vào kho."""
        key = str(masach).strip()
        if not key or len(key) > 10:
            raise ValueError("Mã cuốn sách là bắt buộc và tối đa 10 ký tự!")
        BookActions._run_write(
            "EXEC dbo.sp_Sach_Them @MASACH=?, @ISBN=?, @MANGANTU=?, @TINHTRANG=?",
            (key, str(isbn).strip(), mangantu, int(tinh_trang)),
            "sách",
        )
        return True

    @staticmethod
    def cap_nhat_cuon_sach(masach: str, isbn: str, mangantu: Optional[int], tinh_trang: int) -> bool:
        """Sửa cuốn sách (khóa chính MASACH không đổi)."""
        BookActions._run_write(
            "EXEC dbo.sp_Sach_CapNhat @MASACH=?, @ISBN=?, @MANGANTU=?, @TINHTRANG=?",
            (str(masach).strip(), str(isbn).strip(), mangantu, int(tinh_trang)),
            "sách",
        )
        return True

    @staticmethod
    def cap_nhat_tinh_trang(masach: str, tinh_trang: int) -> bool:
        """Cập nhật tình trạng sách: 1 = Tốt/Bình thường, 0 = Hư hỏng/Hủy."""
        BookActions._run_write(
            "EXEC dbo.sp_Sach_CapNhatTinhTrang @MASACH=?, @TINHTRANG=?",
            (str(masach).strip(), int(tinh_trang)),
            "sách",
        )
        return True

    @staticmethod
    def huy_cuon_sach(masach: str) -> bool:
        """Xóa hẳn cuốn sách (thanh lý). Đang mượn -> SP từ chối; có lịch sử mượn -> FK 547."""
        BookActions._run_write("EXEC dbo.sp_Sach_Huy @MASACH=?", (str(masach).strip(),), "sách")
        return True


# Bí danh tương thích ngược
SachDAO = BookActions
