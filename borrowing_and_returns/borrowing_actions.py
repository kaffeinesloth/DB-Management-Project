from typing import Any, Callable, Dict, List, Tuple, TypeVar

from database import call_write, call_write_many, friendly_message, get_connection

T = TypeVar("T")


def _call_procedure(runner: Callable[..., T], *args: Any, action: str) -> T:
    """Run a borrowing procedure and turn SQL Server errors into UI exceptions.

    THROW 5xxxx from the procedures (and FK / permission errors) become
    ValueError with the server's Vietnamese text; anything else RuntimeError.
    The procedure has already rolled its transaction back by then.
    """
    try:
        return runner(*args)
    except (ValueError, PermissionError):
        raise
    except Exception as error:
        message = friendly_message(error, "phiếu mượn")
        if message:
            raise ValueError(message) from error
        raise RuntimeError(f"Lỗi SQL Server khi {action}: {error}") from error


class MuonTraDAO:
    """
    Data Access Object (DAO) quản lý toàn bộ quy trình nghiệp vụ Mượn / Trả sách và Tính Phạt.
    Mượn / trả là giao tác trên SQL Server (sql/09_borrowing_transactions.sql):
    Python chỉ gửi EXEC; mọi kiểm tra, khóa và ghi dữ liệu nằm trong 1 TRANSACTION.
    - Thẻ độc giả: Còn hạn & Hoạt động.
    - Giới hạn tối đa 3 cuốn sách chưa trả.
    - Sách mượn phải sẵn sàng (CHOMUON = 0, TINHTRANG = 1) với kiểm tra nguyên tử chống Race Condition.
    - Phạt trễ hạn 500đ/ngày nếu mượn mang về quá 30 ngày.
    - Phạt mất sách theo đúng giá bìa (ISBN.GIA).
    - Phạt hư hỏng sách so với tình trạng lúc mượn.
    """

    @staticmethod
    def get_danh_sach_phieu_dang_muon() -> List[Dict[str, Any]]:
        """Lấy danh sách các lượt mượn sách chưa trả (TRA = 0) từ View tính toán thời gian thực."""
        query = """
            SELECT MAPHIEU, MADG, HoTenDG, DIENTHOAI, MASACH, TENSACH, GiaBia,
                   HINHTHUC, HinhThucStr,
                   CONVERT(VARCHAR(10), NGAYMUON, 103) AS NgayMuonStr,
                   NGAYMUON, SoNgayDaMuon, SoNgayTre, TienPhatTre
            FROM dbo.v_ChiTietPhieuMuon_Phat
            WHERE TRA = 0
            ORDER BY NGAYMUON ASC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def search_phieu_dang_muon(keyword: str) -> List[Dict[str, Any]]:
        """Tìm kiếm phiếu đang mượn theo Tên độc giả, Mã ĐG, SĐT, Mã sách hoặc Tên sách."""
        pattern = f"%{keyword.strip()}%"
        query = """
            SELECT MAPHIEU, MADG, HoTenDG, DIENTHOAI, MASACH, TENSACH, GiaBia,
                   HINHTHUC, HinhThucStr,
                   CONVERT(VARCHAR(10), NGAYMUON, 103) AS NgayMuonStr,
                   NGAYMUON, SoNgayDaMuon, SoNgayTre, TienPhatTre
            FROM dbo.v_ChiTietPhieuMuon_Phat
            WHERE TRA = 0
              AND (
                  HoTenDG LIKE ? 
                  OR CAST(MADG AS VARCHAR) LIKE ? 
                  OR DIENTHOAI LIKE ? 
                  OR MASACH LIKE ? 
                  OR TENSACH LIKE ?
              )
            ORDER BY NGAYMUON ASC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (pattern, pattern, pattern, pattern, pattern))
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def tao_phieu_muon(madg: int, manv: int, hinh_thuc: int, danh_sach_masach: List[str]) -> int:
        """
        Lập phiếu mượn bằng một lời gọi dbo.sp_PhieuMuon_Tao (sql/09_borrowing_transactions.sql).

        Toàn bộ nghiệp vụ chạy trong 1 TRANSACTION trên SQL Server: kiểm tra thẻ
        (54102/54103), giới hạn 3 cuốn (54101/54104), khóa nguyên tử từng cuốn
        sách (54105), rồi ghi PHIEUMUON + CT_PHIEUMUON. Lỗi bất kỳ -> ROLLBACK.
        Trả về MAPHIEU vừa tạo.
        """
        masach_list = [str(ms).strip() for ms in danh_sach_masach or [] if str(ms).strip()]
        if not masach_list:
            raise ValueError("Danh sách sách mượn không được để trống!")
        if any("," in ms for ms in masach_list):
            raise ValueError("Mã sách không được chứa dấu phẩy!")

        row = _call_procedure(
            call_write,
            "EXEC dbo.sp_PhieuMuon_Tao @MADG=?, @MANV=?, @HinhThuc=?, @DanhSachMaSach=?",
            (int(madg), int(manv), 1 if int(hinh_thuc) else 0, ",".join(masach_list)),
            action="lập phiếu mượn",
        )
        if not row or row.get("MAPHIEU") is None:
            raise RuntimeError("SQL Server không trả về mã phiếu mượn vừa tạo!")
        return int(row["MAPHIEU"])

    @staticmethod
    def tinh_toan_phi_phat(maphieu: int, masach: str, tinh_trang_tra: int, bi_mat: bool = False) -> Dict[str, Any]:
        """
        Tính toán chi tiết tiền phạt và đền bù trước khi xác nhận trả sách:
        Khai thác trực tiếp từ View v_ChiTietPhieuMuon_Phat.
        - Số ngày trễ hạn (>30 ngày nếu mang về, >0 ngày nếu tại chỗ).
        - Phạt trễ hạn: 500 VNĐ / ngày trễ.
        - Phạt mất sách: Đền bù 100% giá bìa (ISBN.GIA).
        - Phạt hư hỏng: Đền bù 50% giá bìa nếu sách trả bị hỏng (TINHTRANG=0).
        """
        maphieu_val = int(maphieu)
        masach_val = str(masach)
        tinh_trang_tra_val = int(tinh_trang_tra)

        query = """
            SELECT TENSACH, GiaBia, SoNgayDaMuon, SoNgayTre, TienPhatTre, TINHTRANGMUON, TRA
            FROM dbo.v_ChiTietPhieuMuon_Phat
            WHERE MAPHIEU = ? AND MASACH = ?;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (maphieu_val, masach_val))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Không tìm thấy thông tin mượn sách này!")

            tensach, gia_bia, so_ngay_da_muon, so_ngay_tre, tien_phat_tre, tinh_trang_muon, da_tra = row

            if da_tra:
                raise ValueError("Cuốn sách này đã được xác nhận trả trước đó!")

            # 1. Tiền mất sách
            tien_mat_sach = gia_bia if bi_mat else 0

            # 2. Tiền hư hỏng (50% giá bìa nếu lúc mượn tốt mà lúc trả bị hỏng)
            tien_phat_hong = 0
            if not bi_mat and tinh_trang_tra_val == 0 and tinh_trang_muon == 1:
                tien_phat_hong = int(gia_bia * 0.5)

            tong_phat = tien_phat_tre + tien_mat_sach + tien_phat_hong

            return {
                "TENSACH": tensach,
                "GiaBia": gia_bia,
                "SoNgayDaMuon": so_ngay_da_muon,
                "SoNgayTre": so_ngay_tre,
                "TienPhatTre": tien_phat_tre,
                "TienMatSach": tien_mat_sach,
                "TienPhatHong": tien_phat_hong,
                "TongPhat": tong_phat
            }

    @staticmethod
    def xac_nhan_tra_sach(maphieu: int, masach: str, manvns: int, tinh_trang_tra: int, bi_mat: bool = False) -> Dict[str, Any]:
        """
        Xác nhận trả 1 cuốn bằng dbo.sp_PhieuMuon_XacNhanTra, trong 1 TRANSACTION:
        tính phạt (trễ hạn / mất 100% / hỏng 50% giá bìa), đóng dòng CT_PHIEUMUON,
        cập nhật SACH (CHOMUON = 0, TINHTRANG = 0 nếu mất hoặc hỏng).
        Trả về chi tiết tiền phạt do SQL Server tính.
        """
        row = _call_procedure(
            call_write,
            "EXEC dbo.sp_PhieuMuon_XacNhanTra @MAPHIEU=?, @MASACH=?, @MANVNS=?, @TinhTrangTra=?, @BiMat=?",
            (int(maphieu), str(masach).strip(), int(manvns),
             1 if int(tinh_trang_tra) else 0, 1 if bi_mat else 0),
            action="ghi nhận trả sách",
        )
        if not row:
            raise RuntimeError("SQL Server không trả về kết quả tiền phạt!")
        return row

    @staticmethod
    def get_chi_tiet_phieu_gom_nhom(maphieu: int) -> List[Dict[str, Any]]:
        """
        Lấy danh sách các đầu sách (ISBN) trong phiếu mượn chưa trả, gom nhóm theo ISBN.
        Bao gồm số lượng mượn, số lượng chưa trả, giá bìa, số ngày trễ và tiền phạt trễ mỗi cuốn.
        """
        query = """
            SELECT 
                s.ISBN,
                i.TENSACH,
                ISNULL(i.GIA, 0) AS GiaBia,
                COUNT(ct.MASACH) AS TongMuon,
                SUM(CASE WHEN ct.TRA = 0 THEN 1 ELSE 0 END) AS ConMuon,
                ISNULL(MAX(v.SoNgayTre), 0) AS SoNgayTre,
                ISNULL(MAX(v.TienPhatTre), 0) AS TienPhatTrePerBook
            FROM dbo.CT_PHIEUMUON ct
            JOIN dbo.SACH s ON ct.MASACH = s.MASACH
            JOIN dbo.ISBN i ON s.ISBN = i.ISBN
            LEFT JOIN dbo.v_ChiTietPhieuMuon_Phat v ON ct.MAPHIEU = v.MAPHIEU AND ct.MASACH = v.MASACH
            WHERE ct.MAPHIEU = ? AND ct.TRA = 0
            GROUP BY s.ISBN, i.TENSACH, i.GIA;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (int(maphieu),))
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def xac_nhan_tra_sach_theo_so_luong(maphieu: int, danh_sach_tra: List[Dict[str, Any]], manvns: int) -> Dict[str, Any]:
        """
        Trả sách gom nhóm theo ISBN. danh_sach_tra là list dict {
            "ISBN": str, "SoLuong": int,
            "TinhTrangTra": int (1: Bình thường, 0: Hỏng), "BiMat": bool
        }.
        Mỗi ISBN là một lời gọi dbo.sp_PhieuMuon_TraTheoISBN (tự chọn TOP N cuốn
        chưa trả). Tất cả lời gọi chạy chung 1 giao tác (call_write_many): một
        ISBN lỗi thì toàn bộ lần trả bị ROLLBACK.
        """
        maphieu_val = int(maphieu)
        manvns_val = int(manvns)

        calls: List[Tuple[str, tuple]] = []
        for item in danh_sach_tra or []:
            so_luong = int(item["SoLuong"])
            if so_luong <= 0:
                continue
            calls.append((
                "EXEC dbo.sp_PhieuMuon_TraTheoISBN @MAPHIEU=?, @ISBN=?, @SoLuong=?, "
                "@MANVNS=?, @TinhTrangTra=?, @BiMat=?",
                (maphieu_val, str(item["ISBN"]).strip(), so_luong, manvns_val,
                 1 if int(item.get("TinhTrangTra", 1)) else 0,
                 1 if item.get("BiMat", False) else 0),
            ))

        if not calls:
            raise ValueError("Chưa có cuốn sách nào được chọn để trả!")

        rows = _call_procedure(call_write_many, calls, action="ghi nhận trả sách gom nhóm")

        tong = {"TongSoCuonTra": 0, "TienPhatTre": 0, "TienMatSach": 0, "TienPhatHong": 0, "TongPhat": 0}
        for row in rows:
            if not row:
                raise RuntimeError("SQL Server không trả về kết quả trả sách theo ISBN!")
            tong["TongSoCuonTra"] += int(row["SoCuonTra"] or 0)
            for key in ("TienPhatTre", "TienMatSach", "TienPhatHong", "TongPhat"):
                tong[key] += int(row[key] or 0)
        return tong


# Bí danh tương thích
BorrowingActions = MuonTraDAO
