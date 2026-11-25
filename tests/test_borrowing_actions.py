"""Unit tests for borrowing_and_returns.borrowing_actions (Task 4: transactions).

Lending and returning are stored procedures in sql/09_borrowing_transactions.sql.
These tests replace the SQL Server connection with a fake whose writes stay
pending until commit() and are discarded by rollback(), so they check that:
- each operation is sent as EXEC of the right procedure with the right values;
- success commits once;
- a THROW from the procedure rolls everything back and reaches the UI as a
  ValueError carrying the server's Vietnamese message.
"""

import unittest
from typing import Any, Dict, List, Optional, Sequence, Tuple
from unittest.mock import patch

import pyodbc

from borrowing_and_returns.borrowing_actions import MuonTraDAO


def sql_error(code: int, message: str) -> pyodbc.Error:
    """A pyodbc error shaped like the driver's text for a THROW / native error."""
    return pyodbc.ProgrammingError(
        "42000",
        f"[42000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]{message} ({code}) (SQLExecDirectW)",
    )


Result = Tuple[Sequence[str], List[tuple]]


class FakeCursor:
    """Scripted result set (or error) per procedure name; records every EXEC."""

    def __init__(self, connection: "FakeConnection", results: Dict[str, Any]) -> None:
        self.connection = connection
        self.results = results
        self.description: Optional[List[tuple]] = None
        self._rows: List[tuple] = []

    def execute(self, query: str, params: tuple = ()) -> "FakeCursor":
        call = (" ".join(query.split()), tuple(params))
        self.connection.executed.append(call)
        for name, outcome in self.results.items():
            if name not in query:
                continue
            if callable(outcome):          # a script: may return a result or raise
                outcome = outcome(params)
            if isinstance(outcome, Exception):
                raise outcome
            columns, rows = outcome
            self.connection.pending.append(call)
            self.description = [(column,) for column in columns]
            self._rows = list(rows)
            return self
        raise AssertionError(f"unexpected SQL: {query}")

    def fetchall(self) -> List[tuple]:
        return self._rows


class FakeConnection:
    """Writes are pending until commit(); rollback() discards them."""

    def __init__(self, results: Dict[str, Any]) -> None:
        self.results = results
        self.executed: List[tuple] = []
        self.pending: List[tuple] = []
        self.committed: List[tuple] = []
        self.commit_count = 0
        self.rollback_count = 0

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *exc: Any) -> bool:
        return False

    def cursor(self) -> FakeCursor:
        return FakeCursor(self, self.results)

    def commit(self) -> None:
        self.commit_count += 1
        self.committed.extend(self.pending)
        self.pending.clear()

    def rollback(self) -> None:
        self.rollback_count += 1
        self.pending.clear()


FINE_COLUMNS = ("MAPHIEU", "MASACH", "TENSACH", "GiaBia", "SoNgayDaMuon", "SoNgayTre",
                "TienPhatTre", "TienMatSach", "TienPhatHong", "TongPhat")
BATCH_COLUMNS = ("MAPHIEU", "ISBN", "SoCuonTra", "TienPhatTre", "TienMatSach",
                 "TienPhatHong", "TongPhat")


class BorrowingTestCase(unittest.TestCase):
    def run_with(self, results: Dict[str, Any], func, *args, **kwargs):
        connection = FakeConnection(results)
        with patch("database.get_connection", return_value=connection):
            try:
                return func(*args, **kwargs), connection
            except Exception as error:
                error.connection = connection  # type: ignore[attr-defined]
                raise

    def assert_rolled_back(self, connection: FakeConnection) -> None:
        self.assertEqual(connection.commit_count, 0, "a failed transaction must not commit")
        self.assertGreaterEqual(connection.rollback_count, 1, "a failed transaction must roll back")
        self.assertEqual(connection.committed, [], "no write may survive a rollback")
        self.assertEqual(connection.pending, [])


class TaoPhieuMuonTests(BorrowingTestCase):
    def test_lending_is_one_procedure_call_and_returns_new_loan_id(self):
        maphieu, connection = self.run_with(
            {"sp_PhieuMuon_Tao": (("MAPHIEU",), [(501,)])},
            MuonTraDAO.tao_phieu_muon, 7, 2, 1, [" S0001", "S0002 "],
        )

        self.assertEqual(maphieu, 501)
        self.assertEqual(connection.executed, [(
            "EXEC dbo.sp_PhieuMuon_Tao @MADG=?, @MANV=?, @HinhThuc=?, @DanhSachMaSach=?",
            (7, 2, 1, "S0001,S0002"),
        )])
        self.assertEqual(connection.commit_count, 1)
        self.assertEqual(len(connection.committed), 1)

    def test_every_business_rule_throw_rolls_back_and_becomes_value_error(self):
        cases = (
            (54101, "Mỗi phiếu mượn phải có từ 1 đến 3 cuốn sách!"),
            (54102, "Thẻ độc giả đang bị KHÓA! Không thể mượn sách."),
            (54103, "Thẻ độc giả đã HẾT HẠN từ ngày 01/01/2026! Vui lòng gia hạn thẻ."),
            (54104, "Độc giả đang giữ 2 cuốn. Muốn mượn thêm 2 cuốn sẽ vượt quá giới hạn tối đa 3 cuốn/độc giả!"),
            (54105, "Sách S0002 đã có người khác mượn, đang hư hỏng hoặc không tồn tại!"),
            (54106, "Các mã sách trong cùng một phiếu mượn không được trùng nhau!"),
        )
        for code, message in cases:
            with self.subTest(code=code):
                with self.assertRaises(ValueError) as caught:
                    self.run_with({"sp_PhieuMuon_Tao": sql_error(code, message)},
                                  MuonTraDAO.tao_phieu_muon, 7, 2, 1, ["S0001", "S0002"])
                self.assertEqual(str(caught.exception), message)
                self.assert_rolled_back(caught.exception.connection)

    def test_unexpected_server_error_rolls_back_and_becomes_runtime_error(self):
        lost = pyodbc.OperationalError("08S01", "[08S01] Communication link failure (10054)")
        with self.assertRaisesRegex(RuntimeError, "lập phiếu mượn") as caught:
            self.run_with({"sp_PhieuMuon_Tao": lost}, MuonTraDAO.tao_phieu_muon, 7, 2, 1, ["S0001"])
        self.assert_rolled_back(caught.exception.connection)

    def test_permission_denied_is_reported_in_vietnamese(self):
        denied = sql_error(229, "The EXECUTE permission was denied on the object 'sp_PhieuMuon_Tao'.")
        with self.assertRaisesRegex(ValueError, "không có quyền"):
            self.run_with({"sp_PhieuMuon_Tao": denied}, MuonTraDAO.tao_phieu_muon, 7, 2, 1, ["S0001"])

    def test_empty_or_comma_codes_are_rejected_before_calling_the_server(self):
        for books, fragment in (([], "không được để trống"), (["  "], "không được để trống"),
                                (["S0001,S0002"], "dấu phẩy")):
            with self.subTest(books=books):
                with patch("database.get_connection") as get_connection:
                    with self.assertRaisesRegex(ValueError, fragment):
                        MuonTraDAO.tao_phieu_muon(7, 2, 1, books)
                    get_connection.assert_not_called()


class XacNhanTraSachTests(BorrowingTestCase):
    def test_single_return_sends_flags_and_returns_server_fine(self):
        row = (501, "S0001", "Mắt biếc", 80000, 40, 10, 5000, 0, 40000, 45000)
        fine, connection = self.run_with(
            {"sp_PhieuMuon_XacNhanTra": (FINE_COLUMNS, [row])},
            MuonTraDAO.xac_nhan_tra_sach, 501, "S0001 ", 3, 0, False,
        )

        self.assertEqual(connection.executed, [(
            "EXEC dbo.sp_PhieuMuon_XacNhanTra @MAPHIEU=?, @MASACH=?, @MANVNS=?, @TinhTrangTra=?, @BiMat=?",
            (501, "S0001", 3, 0, 0),
        )])
        self.assertEqual(connection.commit_count, 1)
        self.assertEqual(fine["TienPhatTre"], 5000)
        self.assertEqual(fine["TienPhatHong"], 40000)
        self.assertEqual(fine["TongPhat"], 45000)

    def test_lost_flag_is_sent_as_bit(self):
        row = (501, "S0001", "Mắt biếc", 80000, 3, 0, 0, 80000, 0, 80000)
        _, connection = self.run_with(
            {"sp_PhieuMuon_XacNhanTra": (FINE_COLUMNS, [row])},
            MuonTraDAO.xac_nhan_tra_sach, 501, "S0001", 3, 1, True,
        )
        self.assertEqual(connection.executed[0][1][-1], 1)

    def test_double_return_rolls_back(self):
        message = "Không tìm thấy lượt mượn chưa trả của cuốn sách này (có thể đã được trả trước đó)!"
        with self.assertRaises(ValueError) as caught:
            self.run_with({"sp_PhieuMuon_XacNhanTra": sql_error(54111, message)},
                          MuonTraDAO.xac_nhan_tra_sach, 501, "S0001", 3, 1)
        self.assertEqual(str(caught.exception), message)
        self.assert_rolled_back(caught.exception.connection)


class TraTheoSoLuongTests(BorrowingTestCase):
    ITEMS = [
        {"ISBN": "ISBN000001", "SoLuong": 2, "TinhTrangTra": 1, "BiMat": False},
        {"ISBN": "ISBN000002", "SoLuong": 0, "TinhTrangTra": 1, "BiMat": False},  # skipped
        {"ISBN": "ISBN000003", "SoLuong": 1, "TinhTrangTra": 0, "BiMat": True},
    ]

    @staticmethod
    def batch_script(fail_on_isbn: Optional[str] = None):
        def script(params: tuple):
            maphieu, isbn, so_luong = params[0], params[1], params[2]
            if isbn == fail_on_isbn:
                return sql_error(54114, f"Số sách chưa trả của ISBN {isbn} chỉ còn 0 cuốn, không đủ để trả {so_luong} cuốn!")
            lost = params[5] == 1
            tien_mat = 50000 * so_luong if lost else 0
            return BATCH_COLUMNS, [(maphieu, isbn, so_luong, 1000 * so_luong, tien_mat, 0,
                                    1000 * so_luong + tien_mat)]
        return script

    def test_each_isbn_is_one_call_in_a_single_commit_and_totals_are_summed(self):
        totals, connection = self.run_with(
            {"sp_PhieuMuon_TraTheoISBN": self.batch_script()},
            MuonTraDAO.xac_nhan_tra_sach_theo_so_luong, 501, self.ITEMS, 3,
        )

        sql = ("EXEC dbo.sp_PhieuMuon_TraTheoISBN @MAPHIEU=?, @ISBN=?, @SoLuong=?, "
               "@MANVNS=?, @TinhTrangTra=?, @BiMat=?")
        self.assertEqual(connection.executed, [
            (sql, (501, "ISBN000001", 2, 3, 1, 0)),
            (sql, (501, "ISBN000003", 1, 3, 0, 1)),
        ])
        self.assertEqual(connection.commit_count, 1)
        self.assertEqual(totals, {
            "TongSoCuonTra": 3, "TienPhatTre": 3000, "TienMatSach": 50000,
            "TienPhatHong": 0, "TongPhat": 53000,
        })

    def test_failure_on_a_later_isbn_rolls_back_the_earlier_ones(self):
        with self.assertRaisesRegex(ValueError, "không đủ để trả") as caught:
            self.run_with(
                {"sp_PhieuMuon_TraTheoISBN": self.batch_script(fail_on_isbn="ISBN000003")},
                MuonTraDAO.xac_nhan_tra_sach_theo_so_luong, 501, self.ITEMS, 3,
            )
        connection = caught.exception.connection
        self.assertEqual(len(connection.executed), 2, "the first ISBN ran before the failure")
        self.assert_rolled_back(connection)

    def test_nothing_selected_is_rejected_without_a_connection(self):
        for items in ([], [{"ISBN": "ISBN000001", "SoLuong": 0}]):
            with self.subTest(items=items):
                with patch("database.get_connection") as get_connection:
                    with self.assertRaisesRegex(ValueError, "Chưa có cuốn sách nào"):
                        MuonTraDAO.xac_nhan_tra_sach_theo_so_luong(501, items, 3)
                    get_connection.assert_not_called()


class ReturnScreenTests(unittest.TestCase):
    def test_fine_preview_error_stops_the_return_without_crashing(self):
        """A copy that was already returned: show the warning and stop (no UnboundLocalError)."""
        from unittest.mock import MagicMock
        from borrowing_and_returns import borrowing_screen
        from borrowing_and_returns.borrowing_screen import BorrowingScreen

        screen = BorrowingScreen.__new__(BorrowingScreen)
        screen.tree = MagicMock()
        screen.tree.selection.return_value = ("row1",)
        screen.tree.item.return_value = {"values": [501, 7, "Nguyễn An", "0900", "S0001", "Mắt biếc"]}

        with patch.object(borrowing_screen.MuonTraDAO, "tinh_toan_phi_phat",
                          side_effect=ValueError("Cuốn sách này đã được xác nhận trả trước đó!")), \
             patch.object(borrowing_screen.MuonTraDAO, "xac_nhan_tra_sach") as confirm, \
             patch.object(borrowing_screen, "messagebox") as box:
            screen.handle_return_book(1, False)

        box.showwarning.assert_called_once()
        box.askyesno.assert_not_called()
        confirm.assert_not_called()


if __name__ == "__main__":
    unittest.main()
