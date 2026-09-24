from typing import List, Dict, Any
from db import get_connection

class ThongKeDAO:
    """
    Data Access Object (DAO) xử lý các truy vấn Báo Cáo Thống Kê theo yêu cầu đề tài:
    1. Thống kê độc giả mượn sách quá hạn (TRA = 0 và trễ hạn).
    2. Thống kê tần suất mượn sách (Top đầu sách mượn nhiều nhất / ít nhất).
    """

    @staticmethod
    def get_doc_gia_qua_han() -> List[Dict[str, Any]]:
        """
        Lấy danh sách các độc giả đang mượn sách quá hạn:
        - Mượn mang về (HINHTHUC=1): Quá 30 ngày.
        - Mượn tại chỗ (HINHTHUC=0): Quá 0 ngày (chưa trả trong ngày).
        """
        query = """
            SELECT 
                dg.MADG,
                RTRIM(dg.HODG) + ' ' + RTRIM(dg.TENDG) AS HoTenDG,
                dg.DIENTHOAI,
                dg.EMAILDG,
                pm.MAPHIEU,
                ct.MASACH,
                i.TENSACH,
                CASE WHEN pm.HINHTHUC = 1 THEN N'Mang về' ELSE N'Tại chỗ' END AS HinhThuc,
                CONVERT(VARCHAR(10), pm.NGAYMUON, 103) AS NgayMuonStr,
                DATEDIFF(DAY, pm.NGAYMUON, GETDATE()) AS SoNgayDaMuon,
                CASE 
                    WHEN pm.HINHTHUC = 1 THEN DATEDIFF(DAY, pm.NGAYMUON, GETDATE()) - 30
                    ELSE DATEDIFF(DAY, pm.NGAYMUON, GETDATE())
                END AS SoNgayTre,
                (CASE 
                    WHEN pm.HINHTHUC = 1 THEN (DATEDIFF(DAY, pm.NGAYMUON, GETDATE()) - 30) * 500
                    ELSE DATEDIFF(DAY, pm.NGAYMUON, GETDATE()) * 500
                END) AS TienPhatUocTinh
            FROM dbo.CT_PHIEUMUON ct
            INNER JOIN dbo.PHIEUMUON pm ON ct.MAPHIEU = pm.MAPHIEU
            INNER JOIN dbo.DOCGIA dg ON pm.MADG = dg.MADG
            INNER JOIN dbo.SACH s ON ct.MASACH = s.MASACH
            INNER JOIN dbo.ISBN i ON s.ISBN = i.ISBN
            WHERE ct.TRA = 0
              AND (
                  (pm.HINHTHUC = 1 AND DATEDIFF(DAY, pm.NGAYMUON, GETDATE()) > 30)
                  OR
                  (pm.HINHTHUC = 0 AND DATEDIFF(DAY, pm.NGAYMUON, GETDATE()) > 0)
              )
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
