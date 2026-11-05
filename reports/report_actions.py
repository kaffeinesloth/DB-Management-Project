"""Report queries and helpers. SQL lives in sql/06_reports.sql."""

import calendar
import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

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
            raise ValueError("Year must be between 1900 and 2078.")
        if self.month is not None and self.quarter is not None:
            raise ValueError("Choose a month or a quarter, not both.")
        if self.month is not None and not 1 <= self.month <= 12:
            raise ValueError("Month must be between 1 and 12.")
        if self.quarter is not None and not 1 <= self.quarter <= 4:
            raise ValueError("Quarter must be between 1 and 4.")

    @property
    def bounds(self) -> tuple[date, date]:
        """First and last calendar day of the period (both inclusive)."""
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
            return f"Month {self.month}/{self.year}"
        if self.quarter is not None:
            return f"Q{self.quarter}/{self.year}"
        return f"Year {self.year}"

    def as_of(self, today: date | None = None) -> date:
        """End of the period, or today if the period has not ended yet."""
        today = today or date.today()
        return min(self.bounds[1], today)


def _fetch(sql: str, params: tuple) -> tuple[list[str], list[tuple]]:
    cursor = database.get_connection().cursor()
    try:
        cursor.execute(sql, params)
        keys = [column[0] for column in cursor.description]
        rows = [tuple(row) for row in cursor.fetchall()]
    finally:
        cursor.close()
    return keys, rows


def _vnd(amount: int | None) -> str:
    return f"{int(amount or 0):,} VND".replace(",", ".")


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
        title=f"Overdue readers as of {as_of:%d/%m/%Y}",
        columns=[
            "Reader ID", "Reader", "Phone", "Email", "Loan", "Copy", "Title",
            "Borrowed", "Due", "Days late", "Fine (VND)",
        ],
        keys=keys,
        rows=rows,
        summary=(
            f"{readers} reader(s), {len(rows)} book(s) overdue, "
            f"fines to date {_vnd(total_fine)}"
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
        title=f"Book usage frequency - {period.label}",
        columns=["Rank", "ISBN", "Title", "Category", "Copies", "Loans", "Readers"],
        keys=keys,
        rows=rows,
        period=(start, end),
        summary=f"{loans} loan(s) across {len(rows) - unused} title(s); {unused} title(s) not borrowed",
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
        title=f"Stock review - {period.label}",
        columns=["Copy", "ISBN", "Title", "Shelf", "Location", "Last borrowed", "Reason"],
        keys=keys,
        rows=rows,
        period=(start, end),
        summary=f"{len(rows)} copy(ies) to review: {damaged} damaged, {len(rows) - damaged} not borrowed",
    )


SUMMARY_LABELS = {
    "KY": "Period",
    "TUNGAY": "From",
    "DENNGAY": "To",
    "NGAYCHOT": "Overdue figures as of",
    "SOPHIEUMUON": "Loan slips",
    "SOLUOTMUON": "Books lent",
    "SODOCGIAMUON": "Readers who borrowed",
    "SOLUOTTRA": "Books returned",
    "SOLUOTTRATRE": "Books returned late",
    "TIENPHATTRATRE": "Late-return fines (VND)",
    "SOSACHQUAHAN_CUOIKY": "Books overdue at period end",
    "SODOCGIAQUAHAN_CUOIKY": "Readers overdue at period end",
    "TIENPHATQUAHAN_CUOIKY": "Outstanding overdue fines (VND)",
}


def period_summary(period: Period) -> ReportResult:
    keys, rows = _fetch(
        "EXEC dbo.sp_ThongKe_TheoKy @Nam = ?, @Thang = ?, @Quy = ?",
        (period.year, period.month, period.quarter),
    )
    values = rows[0] if rows else ()
    pivot = [(SUMMARY_LABELS.get(key, key), value) for key, value in zip(keys, values)]
    return ReportResult(
        title=f"Period summary - {period.label}",
        columns=["Metric", "Value"],
        keys=["METRIC", "VALUE"],
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
        return "Yes" if value else "No"
    return str(value)


def export_csv(result: ReportResult, path: str | Path) -> Path:
    """Write the report as UTF-8 CSV with BOM so Excel shows Vietnamese text."""
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
