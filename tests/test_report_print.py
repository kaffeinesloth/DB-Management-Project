import re
import unittest
from datetime import date

from reports.report_actions import ReportResult
from reports.report_print import render_html, vietnamese_date_line


OVERDUE_KEYS = ["MADG", "HOTENDG", "DIENTHOAI", "EMAILDG", "MAPHIEU", "MASACH", "TENSACH",
                "NGAYMUON", "NGAYHENTRA", "SONGAYQUAHAN", "TIENPHAT"]


def overdue_result():
    rows = [
        (8, "Lê Văn Tám", "0901", "tam@x.vn", 5, 11, "Sách A", date(2026, 8, 1), date(2026, 8, 31), 40, 20000),
        (8, "Lê Văn Tám", "0901", "tam@x.vn", 5, 12, "Sách B", date(2026, 8, 1), date(2026, 8, 31), 40, 20000),
        (9, "Phạm Thị Chín", "0902", None, 7, 20, "Sách <C>", date(2026, 9, 1), date(2026, 10, 1), 10, 5000),
    ]
    return ReportResult(
        title="Độc giả mượn sách quá hạn tính đến 10/10/2026",
        columns=["Mã ĐG", "Độc giả", "Điện thoại", "Email", "Mã phiếu", "Mã sách", "Tên sách",
                 "Ngày mượn", "Hạn trả", "Số ngày trễ", "Tiền phạt (đ)"],
        keys=OVERDUE_KEYS, rows=rows, summary="2 độc giả, 3 cuốn quá hạn",
    )


class ReportPrintTests(unittest.TestCase):
    def test_date_line(self):
        self.assertEqual(vietnamese_date_line(date(2026, 11, 16)),
                         "TP. Hồ Chí Minh, ngày 16 tháng 11 năm 2026")

    def test_footer_has_city_date_and_creator(self):
        page = render_html(overdue_result(), "Nguyễn Thị Hương", date(2026, 11, 16), creator_id=2)
        self.assertIn("TP. Hồ Chí Minh, ngày 16 tháng 11 năm 2026", page)
        self.assertIn("NGƯỜI LẬP BÁO CÁO", page)
        self.assertIn("Nguyễn Thị Hương", page)
        self.assertIn("Mã NV: 2", page)

    def test_title_and_subtitle(self):
        page = render_html(overdue_result(), "X", date(2026, 11, 16))
        self.assertIn("BÁO CÁO Độc giả mượn sách quá hạn</h1>", page)
        self.assertIn("tính đến 10/10/2026", page)

    def test_overdue_groups_reset_row_numbers(self):
        page = render_html(overdue_result(), "X", date(2026, 11, 16))
        self.assertIn("1. Độc giả: <b>Lê Văn Tám</b>", page)
        self.assertIn("2. Độc giả: <b>Phạm Thị Chín</b>", page)
        stt = re.findall(r'<td class="stt">(\d+)</td>', page)
        self.assertEqual(stt, ["1", "2", "1"])
        self.assertIn("45.000", page)  # grand total
        self.assertIn("&lt;C&gt;", page)  # escaped

    def test_flat_report_numbers_rows_continuously(self):
        result = ReportResult(
            title="Tần suất sử dụng sách - Quý 4/2026",
            columns=["Hạng", "ISBN", "Tên sách", "Thể loại", "Số bản", "Lượt mượn", "Số độc giả"],
            keys=["XEPHANG", "ISBN", "TENSACH", "THELOAI", "SOBANSAO", "SOLUOTMUON", "SODOCGIA"],
            rows=[(1, "111", "A", "Tin", 2, 5, 4), (1, "222", "B", "Tin", 1, 5, 3), (3, "333", "C", "Văn", 1, 0, 0)],
            period=(date(2026, 10, 1), date(2026, 12, 31)),
        )
        page = render_html(result, "X", date(2026, 11, 16))
        self.assertEqual(re.findall(r'<td class="stt">(\d+)</td>', page), ["1", "2", "3"])
        self.assertIn("Từ ngày 01/10/2026 đến ngày 31/12/2026", page)
        self.assertIn("Quý 4/2026", page)

    def test_empty_report(self):
        result = ReportResult(title="Sách cần xem xét thanh lý - Năm 2026",
                              columns=["Mã sách"], keys=["MASACH"], rows=[])
        self.assertIn("Không có dữ liệu", render_html(result, "X", date(2026, 11, 16)))


if __name__ == "__main__":
    unittest.main()
