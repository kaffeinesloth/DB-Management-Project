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
        Tối ưu truy vấn: Gom nhóm trước trên CT_PHIEUMUON và SACH (mỗi bảng chỉ quét 1 lần,
        không dùng correlated subquery lặp theo từng dòng ISBN).
        """
        query = """
            WITH CopyLoans AS (
                SELECT
                    ct.MASACH,
                    COUNT(*) AS SoLuotMuonCuon
                FROM dbo.CT_PHIEUMUON ct
                GROUP BY ct.MASACH
            ),
            SachStats AS (
                SELECT
                    s.ISBN,
                    COUNT(*) AS TongSoCuon,
                    SUM(CASE WHEN s.CHOMUON = 0 AND s.TINHTRANG = 1 THEN 1 ELSE 0 END) AS SoCuonSanCo,
                    ISNULL(SUM(cl.SoLuotMuonCuon), 0) AS SoLuotMuon
                FROM dbo.SACH s
                LEFT JOIN CopyLoans cl ON cl.MASACH = s.MASACH
                GROUP BY s.ISBN
            )
            SELECT 
                RTRIM(i.ISBN) AS ISBN,
                i.TENSACH,
                ISNULL(tl.THELOAI, N'Chưa phân loại') AS TheLoai,
                ISNULL(i.GIA, 0) AS GiaBia,
                ISNULL(st.TongSoCuon, 0) AS TongSoCuon,
                ISNULL(st.SoCuonSanCo, 0) AS SoCuonSanCo,
                ISNULL(st.SoLuotMuon, 0) AS SoLuotMuon
            FROM dbo.ISBN i
            LEFT JOIN dbo.THELOAI tl ON i.MATL = tl.MATL
            LEFT JOIN SachStats st ON st.ISBN = i.ISBN
            ORDER BY SoLuotMuon DESC, i.TENSACH ASC;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            cols = [col[0] for col in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_tong_quan() -> Dict[str, Any]:
        """Lấy các chỉ số tổng quan phục vụ Dashboard Thống kê trong 1 truy vấn duy nhất."""
        query = """
            SELECT
                (SELECT COUNT(*) FROM dbo.ISBN) AS TongDauSach,
                (SELECT COUNT(*) FROM dbo.SACH) AS TongCuonSach,
                (SELECT COUNT(*) FROM dbo.SACH WHERE CHOMUON = 1) AS DangMuon,
                (SELECT COUNT(*) FROM dbo.DOCGIA WHERE HOATDONG = 1) AS DocGiaHoatDong,
                COUNT(*) AS SoQuaHan,
                ISNULL(SUM(TienPhatTre), 0) AS TienPhatUocTinh
            FROM dbo.v_ChiTietPhieuMuon_Phat
            WHERE TRA = 0 AND SoNgayTre > 0;
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            return {
                "TongDauSach": row[0] if row else 0,
                "TongCuonSach": row[1] if row else 0,
                "DangMuon": row[2] if row else 0,
                "DocGiaHoatDong": row[3] if row else 0,
                "SoQuaHan": row[4] if row else 0,
                "TienPhatUocTinh": row[5] if row else 0,
            }


# Bí danh tương thích
ThongKeDAO = ReportActions
