"""Báo cáo thống kê: truy vấn và tiện ích. SQL nằm trong sql/06_reports.sql."""

import calendar
import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import database


@dataclass
class ReportResult:
    title: str
    columns: list[str]
    rows: list[tuple]
    summary: str = ""
    period: tuple[date, date] | None = None
    keys: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Period:
    year: int
    month: int | None = None
    quarter: int | None = None

    def __post_init__(self) -> None:
        if not 1900 <= self.year <= 2078:
            raise ValueError("Năm phải từ 1900 đến 2078.")
        if self.month is not None and self.quarter is not None:
            raise ValueError("Chỉ chọn tháng hoặc quý, không chọn cả hai.")
        if self.month is not None and not 1 <= self.month <= 12:
            raise ValueError("Tháng phải từ 1 đến 12.")
        if self.quarter is not None and not 1 <= self.quarter <= 4:
            raise ValueError("Quý phải từ 1 đến 4.")

    @property
    def bounds(self) -> tuple[date, date]:
        """Ngày đầu và ngày cuối của kỳ (tính cả hai đầu)."""
        if self.month is not None:
            first_month = last_month = self.month
        elif self.quarter is not None:
            first_month, last_month = (self.quarter - 1) * 3 + 1, self.quarter * 3
        else:
            first_month, last_month = 1, 12
        last_day = calendar.monthrange(self.year, last_month)[1]
        return date(self.year, first_month, 1), date(self.year, last_month, last_day)

    @property
    def label(self) -> str:
        if self.month is not None:
            return f"Tháng {self.month}/{self.year}"
        if self.quarter is not None:
            return f"Quý {self.quarter}/{self.year}"
        return f"Năm {self.year}"

    def as_of(self, today: date | None = None) -> date:
        """Ngày cuối kỳ, hoặc hôm nay nếu kỳ chưa kết thúc."""
        today = today or date.today()
        return min(self.bounds[1], today)


def _fetch(sql: str, params: tuple = ()) -> tuple[list[str], list[tuple]]:
    """Run one query on the logged-in user's connection and close it afterwards."""
    conn = database.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        keys = [column[0] for column in cursor.description]
        rows = [tuple(row) for row in cursor.fetchall()]
        cursor.close()
    finally:
        conn.close()
    return keys, rows


def _vnd(amount: int | None) -> str:
    return f"{int(amount or 0):,} đ".replace(",", ".")


def overview() -> dict[str, Any]:
    """Chỉ số tổng quan hiện tại cho các thẻ KPI."""
    _, rows = _fetch(
        "SELECT "
        "(SELECT COUNT(*) FROM dbo.ISBN), "
        "(SELECT COUNT(*) FROM dbo.SACH), "
        "(SELECT COUNT(*) FROM dbo.SACH WHERE CHOMUON = 1), "
        "(SELECT COUNT(*) FROM dbo.DOCGIA WHERE HOATDONG = 1), "
        "(SELECT COUNT(*) FROM dbo.fn_BaoCao_QuaHan(CONVERT(DATE, GETDATE()))), "
        "(SELECT COALESCE(SUM(TIENPHAT), 0) FROM dbo.fn_BaoCao_QuaHan(CONVERT(DATE, GETDATE())))"
    )
    titles, copies, on_loan, readers, overdue, fines = rows[0]
    return {
        "TongDauSach": titles,
        "TongCuonSach": copies,
        "DangMuon": on_loan,
        "DocGiaHoatDong": readers,
        "SoQuaHan": overdue,
        "TienPhatUocTinh": fines,
    }


def overdue_readers(as_of: date) -> ReportResult:
    keys, rows = _fetch(
        "SELECT MADG, HOTENDG, DIENTHOAI, EMAILDG, MAPHIEU, MASACH, TENSACH, "
        "NGAYMUON, NGAYHENTRA, SONGAYQUAHAN, TIENPHAT "
        "FROM dbo.fn_BaoCao_QuaHan(?) "
        "ORDER BY SONGAYQUAHAN DESC, MADG, MASACH",
        (as_of,),
    )
    readers = len({row[0] for row in rows})
    total_fine = sum(row[-1] for row in rows)
    return ReportResult(
        title=f"Độc giả mượn sách quá hạn tính đến {as_of:%d/%m/%Y}",
        columns=[
            "Mã ĐG", "Độc giả", "Điện thoại", "Email", "Mã phiếu", "Mã sách", "Tên sách",
            "Ngày mượn", "Hạn trả", "Số ngày trễ", "Tiền phạt (đ)",
        ],
        keys=keys,
        rows=rows,
        summary=(
            f"{readers} độc giả, {len(rows)} cuốn quá hạn, "
            f"tiền phạt tạm tính {_vnd(total_fine)}"
        ),
    )


def usage_frequency(period: Period) -> ReportResult:
    start, end = period.bounds
    keys, rows = _fetch(
        "SELECT XEPHANG, ISBN, TENSACH, THELOAI, SOBANSAO, SOLUOTMUON, SODOCGIA "
        "FROM dbo.fn_BaoCao_TanSuat(?, ?) "
        "ORDER BY XEPHANG, TENSACH",
        (start, end),
    )
    loans = sum(row[5] for row in rows)
    unused = sum(1 for row in rows if row[5] == 0)
    return ReportResult(
        title=f"Tần suất sử dụng sách - {period.label}",
        columns=["Hạng", "ISBN", "Tên sách", "Thể loại", "Số bản", "Lượt mượn", "Số độc giả"],
        keys=keys,
        rows=rows,
        period=(start, end),
        summary=(
            f"{loans} lượt mượn trên {len(rows) - unused} đầu sách; "
            f"{unused} đầu sách không được mượn"
        ),
    )


def stock_review(period: Period) -> ReportResult:
    start, end = period.bounds
    keys, rows = _fetch(
        "SELECT MASACH, ISBN, TENSACH, KE, VITRI, LANMUONCUOI, LYDO "
        "FROM dbo.fn_BaoCao_SachCanXemXet(?, ?) "
        "ORDER BY LYDO, KE, MASACH",
        (start, end),
    )
    damaged = sum(1 for row in rows if row[6] == "Hư hỏng")
    return ReportResult(
        title=f"Sách cần xem xét thanh lý - {period.label}",
        columns=["Mã sách", "ISBN", "Tên sách", "Kệ", "Vị trí", "Lần mượn cuối", "Lý do"],
        keys=keys,
        rows=rows,
        period=(start, end),
        summary=f"{len(rows)} cuốn cần xem xét: {damaged} hư hỏng, {len(rows) - damaged} không có độc giả mượn",
    )


SUMMARY_LABELS = {
    "KY": "Kỳ báo cáo",
    "TUNGAY": "Từ ngày",
    "DENNGAY": "Đến ngày",
    "NGAYCHOT": "Số liệu quá hạn tính đến",
    "SOPHIEUMUON": "Số phiếu mượn",
    "SOLUOTMUON": "Số lượt mượn sách",
    "SODOCGIAMUON": "Số độc giả mượn",
    "SOLUOTTRA": "Số lượt trả sách",
    "SOLUOTTRATRE": "Số lượt trả trễ",
    "TIENPHATTRATRE": "Tiền phạt trả trễ (đ)",
    "SOSACHQUAHAN_CUOIKY": "Sách quá hạn cuối kỳ",
    "SODOCGIAQUAHAN_CUOIKY": "Độc giả quá hạn cuối kỳ",
    "TIENPHATQUAHAN_CUOIKY": "Tiền phạt quá hạn chưa thu (đ)",
}


def period_summary(period: Period) -> ReportResult:
    keys, rows = _fetch(
        "EXEC dbo.sp_ThongKe_TheoKy @Nam = ?, @Thang = ?, @Quy = ?",
        (period.year, period.month, period.quarter),
    )
    values = rows[0] if rows else ()
    pivot = [(SUMMARY_LABELS.get(key, key), value) for key, value in zip(keys, values)]
    return ReportResult(
        title=f"Thống kê tổng hợp - {period.label}",
        columns=["Chỉ tiêu", "Giá trị"],
        keys=["CHITIEU", "GIATRI"],
        rows=pivot,
        period=period.bounds,
    )


def format_value(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        if getattr(value, "hour", 0) or getattr(value, "minute", 0):
            return value.strftime("%d/%m/%Y %H:%M")
        return value.strftime("%d/%m/%Y")
    if isinstance(value, bool):
        return "Có" if value else "Không"
    return str(value)


def export_csv(result: ReportResult, path: str | Path) -> Path:
    """Ghi báo cáo ra CSV UTF-8 có BOM để Excel hiển thị đúng tiếng Việt."""
    path = Path(path)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([result.title])
        if result.summary:
            writer.writerow([result.summary])
        writer.writerow([])
        writer.writerow(result.columns)
        for row in result.rows:
            writer.writerow([format_value(value) for value in row])
    return path
