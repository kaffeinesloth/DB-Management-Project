"""Report validation and database operations."""

from typing import List, Dict, Any
from database import get_connection


class ReportActions:
    """
    Data Access Object (DAO) xử lý các truy vấn Báo Cáo Thống Kê:
    1. Thống kê độc giả mượn sách quá hạn (TRA = 0 và trễ hạn) - Sử dụng View v_ChiTietPhieuMuon_Phat / v_DOCGIA_MUON_QUAHAN.
    2. Thống kê tần suất mượn sách (Top đầu sách mượn nhiều nhất / ít nhất) - View v_TANSUAT_SU_DUNG_SACH.
    3. Thống kê tổng quan KPI thư viện thời gian thực.
    """

    @staticmethod
    def get_doc_gia_qua_han() -> List[Dict[str, Any]]:
        """
        Lấy danh sách các độc giả đang mượn sách quá hạn:
        - Mượn mang về (HINHTHUC=1): Quá 30 ngày.
        - Mượn tại chỗ (HINHTHUC=0): Quá 0 ngày.
        """
        query = """
            SELECT 
                MADG,
                HoTenDG,
                DIENTHOAI,
                EMAILDG,
                MAPHIEU,
                MASACH,
                TENSACH,
                HinhThucStr AS HinhThuc,
                CONVERT(VARCHAR(10), NGAYMUON, 103) AS NgayMuonStr,
                SoNgayDaMuon,
                SoNgayTre,
                TienPhatTre AS TienPhatUocTinh
            FROM dbo.v_ChiTietPhieuMuon_Phat
            WHERE TRA = 0 AND SoNgayTre > 0
            ORDER BY SoNgayTre DESC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_tan_suat_muon_sach() -> List[Dict[str, Any]]:
        """
        Thống kê tần suất mượn sách theo từng đầu sách (ISBN),
        sắp xếp theo số lượt mượn giảm dần (Được mượn nhiều nhất lên đầu).
        """
        query = """
            SELECT 
                i.ISBN,
                i.TENSACH,
                ISNULL(tl.THELOAI, N'Chưa phân loại') AS TheLoai,
                ISNULL(i.GIA, 0) AS GiaBia,
                (SELECT COUNT(*) FROM dbo.SACH s WHERE s.ISBN = i.ISBN) AS TongSoCuon,
                (SELECT COUNT(*) FROM dbo.SACH s WHERE s.ISBN = i.ISBN AND s.CHOMUON = 0 AND s.TINHTRANG = 1) AS SoCuonSanCo,
                COUNT(ct.MASACH) AS SoLuotMuon
            FROM dbo.ISBN i
            LEFT JOIN dbo.THELOAI tl ON i.MATL = tl.MATL
            LEFT JOIN dbo.SACH s ON i.ISBN = s.ISBN
            LEFT JOIN dbo.CT_PHIEUMUON ct ON s.MASACH = ct.MASACH
            GROUP BY i.ISBN, i.TENSACH, tl.THELOAI, i.GIA
            ORDER BY SoLuotMuon DESC, i.TENSACH ASC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_tong_quan() -> Dict[str, Any]:
        """Lấy các chỉ số tổng quan phục vụ Dashboard Thống kê."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM dbo.ISBN;")
            tong_isbn = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM dbo.SACH;")
            tong_sach = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM dbo.SACH WHERE CHOMUON = 1;")
            dang_muon = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM dbo.DOCGIA WHERE HOATDONG = 1;")
            tong_docgia = cursor.fetchone()[0]

            # Số sách quá hạn và tổng tiền phạt từ View
            query_qh = """
                SELECT COUNT(*), ISNULL(SUM(TienPhatTre), 0)
                FROM dbo.v_ChiTietPhieuMuon_Phat
                WHERE TRA = 0 AND SoNgayTre > 0;
            """
            cursor.execute(query_qh)
            row_qh = cursor.fetchone()
            so_qua_han = row_qh[0] if row_qh else 0
            tien_phat = row_qh[1] if row_qh else 0

            return {
                "TongDauSach": tong_isbn,
                "TongCuonSach": tong_sach,
                "DangMuon": dang_muon,
                "DocGiaHoatDong": tong_docgia,
                "SoQuaHan": so_qua_han,
                "TienPhatUocTinh": tien_phat
            }


# Bí danh tương thích
ThongKeDAO = ReportActions
