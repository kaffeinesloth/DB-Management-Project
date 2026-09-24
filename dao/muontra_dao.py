from typing import List, Dict, Any, Optional
from datetime import datetime
from db import get_connection
from dao.docgia_dao import DocGiaDAO
from dao.sach_dao import SachDAO

class MuonTraDAO:
    """
    Data Access Object (DAO) quản lý toàn bộ quy trình nghiệp vụ Mượn / Trả sách và Tính Phạt.
    Tuân thủ tuyệt đối các ràng buộc đề tài:
    - Thẻ độc giả: Còn hạn & Hoạt động.
    - Giới hạn tối đa 3 cuốn sách chưa trả.
    - Sách mượn phải sẵn sàng (CHOMUON = 0, TINHTRANG = 1).
    - Phạt trễ hạn 500đ/ngày nếu mượn mang về quá 30 ngày.
    - Phạt mất sách theo đúng giá bìa (ISBN.GIA).
    - Phạt hư hỏng sách so với tình trạng lúc mượn.
    """

    @staticmethod
    def get_danh_sach_phieu_dang_muon() -> List[Dict[str, Any]]:
        """Lấy danh sách các lượt mượn sách chưa trả (CT_PHIEUMUON.TRA = 0)."""
        query = """
            SELECT pm.MAPHIEU, pm.MADG, 
                   RTRIM(dg.HODG) + ' ' + RTRIM(dg.TENDG) AS HoTenDG,
                   dg.DIENTHOAI, ct.MASACH, i.TENSACH, ISNULL(i.GIA, 0) AS GiaBia,
                   pm.HINHTHUC,
                   CASE WHEN pm.HINHTHUC = 1 THEN N'Mang về' ELSE N'Tại chỗ' END AS HinhThucStr,
                   CONVERT(VARCHAR(10), pm.NGAYMUON, 103) AS NgayMuonStr,
                   pm.NGAYMUON,
                   DATEDIFF(DAY, pm.NGAYMUON, GETDATE()) AS SoNgayDaMuon,
                   CASE 
                       WHEN pm.HINHTHUC = 1 AND DATEDIFF(DAY, pm.NGAYMUON, GETDATE()) > 30 
                            THEN DATEDIFF(DAY, pm.NGAYMUON, GETDATE()) - 30
                       WHEN pm.HINHTHUC = 0 AND DATEDIFF(DAY, pm.NGAYMUON, GETDATE()) > 0 
                            THEN DATEDIFF(DAY, pm.NGAYMUON, GETDATE())
                       ELSE 0 
                   END AS SoNgayTre,
                   nv.HONV + ' ' + nv.TENNV AS NhanVienChoMuon
            FROM dbo.CT_PHIEUMUON ct
            INNER JOIN dbo.PHIEUMUON pm ON ct.MAPHIEU = pm.MAPHIEU
            INNER JOIN dbo.DOCGIA dg ON pm.MADG = dg.MADG
            INNER JOIN dbo.SACH s ON ct.MASACH = s.MASACH
            INNER JOIN dbo.ISBN i ON s.ISBN = i.ISBN
            INNER JOIN dbo.NHANVIEN nv ON pm.MANV = nv.MANV
            WHERE ct.TRA = 0
            ORDER BY pm.NGAYMUON ASC;
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
            SELECT pm.MAPHIEU, pm.MADG, 
                   RTRIM(dg.HODG) + ' ' + RTRIM(dg.TENDG) AS HoTenDG,
                   dg.DIENTHOAI, ct.MASACH, i.TENSACH, ISNULL(i.GIA, 0) AS GiaBia,
                   pm.HINHTHUC,
                   CASE WHEN pm.HINHTHUC = 1 THEN N'Mang về' ELSE N'Tại chỗ' END AS HinhThucStr,
                   CONVERT(VARCHAR(10), pm.NGAYMUON, 103) AS NgayMuonStr,
                   pm.NGAYMUON,
                   DATEDIFF(DAY, pm.NGAYMUON, GETDATE()) AS SoNgayDaMuon,
                   CASE 
                       WHEN pm.HINHTHUC = 1 AND DATEDIFF(DAY, pm.NGAYMUON, GETDATE()) > 30 
                            THEN DATEDIFF(DAY, pm.NGAYMUON, GETDATE()) - 30
                       WHEN pm.HINHTHUC = 0 AND DATEDIFF(DAY, pm.NGAYMUON, GETDATE()) > 0 
                            THEN DATEDIFF(DAY, pm.NGAYMUON, GETDATE())
                       ELSE 0 
                   END AS SoNgayTre,
                   nv.HONV + ' ' + nv.TENNV AS NhanVienChoMuon
            FROM dbo.CT_PHIEUMUON ct
            INNER JOIN dbo.PHIEUMUON pm ON ct.MAPHIEU = pm.MAPHIEU
            INNER JOIN dbo.DOCGIA dg ON pm.MADG = dg.MADG
            INNER JOIN dbo.SACH s ON ct.MASACH = s.MASACH
            INNER JOIN dbo.ISBN i ON s.ISBN = i.ISBN
            INNER JOIN dbo.NHANVIEN nv ON pm.MANV = nv.MANV
            WHERE ct.TRA = 0
              AND (
                  dg.TENDG LIKE ? 
                  OR dg.HODG LIKE ? 
                  OR CAST(pm.MADG AS VARCHAR) LIKE ? 
                  OR dg.DIENTHOAI LIKE ? 
                  OR ct.MASACH LIKE ? 
                  OR i.TENSACH LIKE ?
              )
            ORDER BY pm.NGAYMUON ASC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (pattern, pattern, pattern, pattern, pattern, pattern))
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def tao_phieu_muon(madg: int, manv: int, hinh_thuc: int, danh_sach_masach: List[str]) -> int:
        """
        Tạo phiếu mượn sách mới với kiểm tra toàn bộ ràng buộc nghiệp vụ:
        1. Thẻ độc giả hợp lệ (còn hạn, hoạt động, chưa giữ quá 3 cuốn).
        2. Tổng sách mượn + đang giữ không vượt quá 3.
        3. Từng cuốn sách phải sẵn sàng (CHOMUON = 0, TINHTRANG = 1).
        4. Ghi nhận PHIEUMUON, CT_PHIEUMUON và UPDATE SACH.CHOMUON = 1 trong 1 Transaction.
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

        # 3. Thực thi Transaction
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

                # 3.2. Insert CT_PHIEUMUON & Update SACH
                query_ct = """
                    INSERT INTO dbo.CT_PHIEUMUON (MAPHIEU, MASACH, TINHTRANGMUON, TRA)
                    VALUES (?, ?, 1, 0);
                """
                query_update_sach = "UPDATE dbo.SACH SET CHOMUON = 1 WHERE MASACH = ?;"

                for info in sach_info_list:
                    cursor.execute(query_ct, (maphieu, info["MASACH"]))
                    cursor.execute(query_update_sach, (info["MASACH"],))

                conn.commit()
                return maphieu
            except Exception as e:
                conn.rollback()
                raise RuntimeError(f"Lỗi khi lập phiếu mượn: {e}")

    @staticmethod
    def tinh_toan_phi_phat(maphieu: int, masach: str, tinh_trang_tra: int, bi_mat: bool = False) -> Dict[str, Any]:
        """
        Tính toán chi tiết tiền phạt và đền bù trước khi xác nhận trả sách:
        - Số ngày trễ hạn (>30 ngày nếu mang về, >0 ngày nếu tại chỗ).
        - Phạt trễ hạn: 500 VNĐ / ngày trễ.
        - Phạt mất sách: Đền bù 100% giá bìa (ISBN.GIA).
        - Phạt hư hỏng: Đền bù 50% giá bìa nếu sách trả bị hỏng (TINHTRANG=0).
        """
        maphieu_val = int(maphieu)
        masach_val = str(masach)
        tinh_trang_tra_val = int(tinh_trang_tra)

        query = """
            SELECT pm.HINHTHUC, pm.NGAYMUON, 
                   DATEDIFF(DAY, pm.NGAYMUON, GETDATE()) AS SoNgayDaMuon,
                   ct.TINHTRANGMUON, ct.TRA,
                   ISNULL(i.GIA, 0) AS GiaBia, i.TENSACH
            FROM dbo.CT_PHIEUMUON ct
            INNER JOIN dbo.PHIEUMUON pm ON ct.MAPHIEU = pm.MAPHIEU
            INNER JOIN dbo.SACH s ON ct.MASACH = s.MASACH
            INNER JOIN dbo.ISBN i ON s.ISBN = i.ISBN
            WHERE ct.MAPHIEU = ? AND ct.MASACH = ?;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (maphieu_val, masach_val))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Không tìm thấy thông tin mượn sách này!")

            hinh_thuc, ngay_muon, so_ngay_da_muon, tinh_trang_muon, da_tra, gia_bia, tensach = row

            if da_tra:
                raise ValueError("Cuốn sách này đã được xác nhận trả trước đó!")

            # 1. Tính trễ hạn
            han_muon = 30 if hinh_thuc == 1 else 0
            so_ngay_tre = max(0, so_ngay_da_muon - han_muon)
            tien_phat_tre = so_ngay_tre * 500

            # 2. Tính mất sách
            tien_mat_sach = gia_bia if bi_mat else 0

            # 3. Tính hư hỏng
            tien_phat_hong = 0
            if not bi_mat and tinh_trang_tra_val == 0 and tinh_trang_muon == 1:
                # Phạt 50% giá sách khi làm hư hại
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
        3. Cập nhật SACH: CHOMUON = 0. Nếu mất sách hoặc hỏng thì TINHTRANG = 0.
        Thực hiện trong 1 Transaction an toàn.
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
                # 1. Cập nhật CT_PHIEUMUON
                query_ct = """
                    UPDATE dbo.CT_PHIEUMUON
                    SET TRA = 1,
                        NGAYTRA = GETDATE(),
                        MANVNS = ?
                    WHERE MAPHIEU = ? AND MASACH = ?;
                """
                cursor.execute(query_ct, (manvns_val, maphieu_val, masach_val))

                # 2. Cập nhật SACH
                # Nếu mất sách: TINHTRANG = 0 (hỏng/mất), CHOMUON = 0
                # Nếu trả sách bình thường: TINHTRANG = tinh_trang_tra_val, CHOMUON = 0
                sach_tinh_trang = 0 if bi_mat else tinh_trang_tra_val
                query_sach = """
                    UPDATE dbo.SACH
                    SET CHOMUON = 0,
                        TINHTRANG = ?
                    WHERE MASACH = ?;
                """
                cursor.execute(query_sach, (sach_tinh_trang, masach_val))

                conn.commit()
                return phi_phat
            except Exception as e:
                conn.rollback()
                raise RuntimeError(f"Lỗi khi ghi nhận trả sách: {e}")

