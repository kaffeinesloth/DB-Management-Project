from typing import List, Dict, Any, Optional
from datetime import datetime
from database import get_connection
from reader_management.reader_actions import ReaderActions, DocGiaDAO
from book_management.book_actions import BookActions, SachDAO

class MuonTraDAO:
    """
    Data Access Object (DAO) quản lý toàn bộ quy trình nghiệp vụ Mượn / Trả sách và Tính Phạt.
    Khai thác trực tiếp VIEW v_ChiTietPhieuMuon_Phat và TRIGGER trg_DongBoTrangThaiSach:
    - Thẻ độc giả: Còn hạn & Hoạt động (Filtered Index UQ_DOCGIA_SOCMND_ACTIVE).
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
        Tạo phiếu mượn sách mới với kiểm tra toàn bộ ràng buộc nghiệp vụ:
        1. Thẻ độc giả hợp lệ (còn hạn, hoạt động, chưa giữ quá 3 cuốn).
        2. Tổng sách mượn + đang giữ không vượt quá 3.
        3. Từng cuốn sách phải sẵn sàng (CHOMUON = 0, TINHTRANG = 1).
        4. Atomic Check & Lock: Ngăn ngừa triệt để Race Condition khi nhiều thủ thư cùng mượn 1 sách.
        5. Ghi nhận PHIEUMUON, CT_PHIEUMUON trong 1 Transaction an toàn.
        """
        if not danh_sach_masach:
            raise ValueError("Danh sách sách mượn không được để trống!")

        if len(danh_sach_masach) > 3:
            raise ValueError("Mỗi lần mượn không được vượt quá 3 cuốn sách!")

        # 1. Kiểm tra thẻ độc giả
        hop_le, ly_do, dang_giu = DocGiaDAO.kiem_tra_the_hop_le_muon_sach(madg)
        if not hop_le:
            raise ValueError(ly_do)

        if dang_giu + len(danh_sach_masach) > 3:
            raise ValueError(
                f"Độc giả đang giữ {dang_giu} cuốn. Muốn mượn thêm {len(danh_sach_masach)} cuốn "
                f"sẽ vượt quá giới hạn tối đa 3 cuốn/độc giả!"
            )

        # 2. Kiểm tra tính sẵn sàng của từng cuốn sách
        sach_info_list = []
        for ms in danh_sach_masach:
            ok, msg, info = SachDAO.kiem_tra_sach_cho_muon(ms)
            if not ok:
                raise ValueError(msg)
            sach_info_list.append(info)

        # 3. Thực thi Transaction nguyên tử
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                # 3.1. Insert PHIEUMUON
                query_pm = """
                    INSERT INTO dbo.PHIEUMUON (MADG, HINHTHUC, NGAYMUON, MANV)
                    OUTPUT INSERTED.MAPHIEU
                    VALUES (?, ?, GETDATE(), ?);
                """
                cursor.execute(query_pm, (madg, hinh_thuc, manv))
                maphieu = cursor.fetchone()[0]

                # 3.2. Atomic Update & Lock cuốn sách chống Race Condition
                query_lock_sach = """
                    UPDATE dbo.SACH 
                    SET CHOMUON = 1 
                    WHERE MASACH = ? AND CHOMUON = 0 AND TINHTRANG = 1;
                """
                query_ct = """
                    INSERT INTO dbo.CT_PHIEUMUON (MAPHIEU, MASACH, TINHTRANGMUON, TRA)
                    VALUES (?, ?, 1, 0);
                """

                for info in sach_info_list:
                    cursor.execute(query_lock_sach, (info["MASACH"],))
                    if cursor.rowcount == 0:
                        raise ValueError(f"Sách '{info['MASACH']}' ({info['TENSACH']}) vừa có người khác mượn hoặc không khả dụng!")
                    cursor.execute(query_ct, (maphieu, info["MASACH"]))

                conn.commit()
                return maphieu
            except Exception as e:
                conn.rollback()
                raise RuntimeError(f"Lỗi khi lập phiếu mượn: {e}")

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
        Xác nhận trả sách:
        1. Tính toán tiền phạt.
        2. Cập nhật CT_PHIEUMUON: TRA = 1, NGAYTRA = GETDATE(), MANVNS = manvns.
           (Trigger trg_DongBoTrangThaiSach sẽ tự động đặt SACH.CHOMUON = 0).
        3. Cập nhật SACH.TINHTRANG nếu sách bị hỏng hoặc mất.
        """
        maphieu_val = int(maphieu)
        masach_val = str(masach)
        manvns_val = int(manvns)
        tinh_trang_tra_val = int(tinh_trang_tra)

        phi_phat = MuonTraDAO.tinh_toan_phi_phat(
            maphieu=maphieu_val, 
            masach=masach_val, 
            tinh_trang_tra=tinh_trang_tra_val, 
            bi_mat=bi_mat
        )

        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                # 1. Cập nhật CT_PHIEUMUON (Trigger trg_DongBoTrangThaiSach tự động cập nhật SACH.CHOMUON = 0)
                query_ct = """
                    UPDATE dbo.CT_PHIEUMUON
                    SET TRA = 1,
                        NGAYTRA = GETDATE(),
                        MANVNS = ?
                    WHERE MAPHIEU = ? AND MASACH = ?;
                """
                cursor.execute(query_ct, (manvns_val, maphieu_val, masach_val))

                # 2. Cập nhật tình trạng sách nếu bị hư hỏng hoặc mất
                sach_tinh_trang = 0 if bi_mat else tinh_trang_tra_val
                query_sach = """
                    UPDATE dbo.SACH
                    SET TINHTRANG = ?
                    WHERE MASACH = ?;
                """
                cursor.execute(query_sach, (sach_tinh_trang, masach_val))

                conn.commit()
                return phi_phat
            except Exception as e:
                conn.rollback()
                raise RuntimeError(f"Lỗi khi ghi nhận trả sách: {e}")

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
        Xác nhận trả sách gom nhóm theo số lượng và tình trạng cho từng ISBN.
        danh_sach_tra: List các dict gồm {
            "ISBN": str,
            "SoLuong": int,
            "TinhTrangTra": int (1: Bình thường, 0: Hỏng),
            "BiMat": bool
        }
        Tự động chọn TOP N mã sách chưa trả (TRA = 0) tương ứng để cập nhật.
        Thực hiện toàn bộ trong 1 Transaction an toàn.
        """
        maphieu_val = int(maphieu)
        manvns_val = int(manvns)

        if not danh_sach_tra:
            raise ValueError("Chưa chọn mục sách nào để trả!")

        tong_so_cuon_tra = 0
        tong_tien_phat_tre = 0
        tong_tien_mat_sach = 0
        tong_tien_phat_hong = 0

        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                for item in danh_sach_tra:
                    isbn = str(item["ISBN"])
                    so_luong = int(item["SoLuong"])
                    tinh_trang_tra = int(item.get("TinhTrangTra", 1))
                    bi_mat = bool(item.get("BiMat", False))

                    if so_luong <= 0:
                        continue

                    # 1. Tìm TOP N mã sách chưa trả thuộc ISBN này trong phiếu
                    query_find = """
                        SELECT TOP (?) ct.MASACH
                        FROM dbo.CT_PHIEUMUON ct
                        JOIN dbo.SACH s ON ct.MASACH = s.MASACH
                        WHERE ct.MAPHIEU = ? AND s.ISBN = ? AND ct.TRA = 0;
                    """
                    cursor.execute(query_find, (so_luong, maphieu_val, isbn))
                    masach_rows = cursor.fetchall()

                    if len(masach_rows) < so_luong:
                        raise ValueError(f"Số lượng sách chưa trả còn lại của ISBN {isbn} chỉ còn {len(masach_rows)} cuốn, không đủ để trả {so_luong} cuốn!")

                    masach_list = [r[0] for r in masach_rows]

                    # 2. Xử lý từng mã sách
                    for masach in masach_list:
                        # Tính phí phạt cho từng cuốn
                        phi = MuonTraDAO.tinh_toan_phi_phat(maphieu_val, masach, tinh_trang_tra, bi_mat)
                        tong_tien_phat_tre += phi["TienPhatTre"]
                        tong_tien_mat_sach += phi["TienMatSach"]
                        tong_tien_phat_hong += phi["TienPhatHong"]
                        tong_so_cuon_tra += 1

                        # Cập nhật CT_PHIEUMUON
                        query_ct = """
                            UPDATE dbo.CT_PHIEUMUON
                            SET TRA = 1,
                                NGAYTRA = GETDATE(),
                                MANVNS = ?
                            WHERE MAPHIEU = ? AND MASACH = ?;
                        """
                        cursor.execute(query_ct, (manvns_val, maphieu_val, masach))

                        # Cập nhật tình trạng SACH
                        sach_tinh_trang = 0 if bi_mat else tinh_trang_tra
                        query_sach = """
                            UPDATE dbo.SACH
                            SET TINHTRANG = ?
                            WHERE MASACH = ?;
                        """
                        cursor.execute(query_sach, (sach_tinh_trang, masach))

                if tong_so_cuon_tra == 0:
                    raise ValueError("Chưa có cuốn sách nào được chọn để trả!")

                conn.commit()

                tong_phat = tong_tien_phat_tre + tong_tien_mat_sach + tong_tien_phat_hong
                return {
                    "TongSoCuonTra": tong_so_cuon_tra,
                    "TienPhatTre": tong_tien_phat_tre,
                    "TienMatSach": tong_tien_mat_sach,
                    "TienPhatHong": tong_tien_phat_hong,
                    "TongPhat": tong_phat
                }
            except Exception as e:
                conn.rollback()
                raise RuntimeError(f"Lỗi khi ghi nhận trả sách gom nhóm: {e}")



# Bí danh tương thích
BorrowingActions = MuonTraDAO
