import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from reader_management.reader_actions import ReaderActions


class ReaderValidationTests(unittest.TestCase):
    def valid_reader(self):
        issue_date = datetime(2026, 1, 31, 9, 0)
        return {
            "HODG": "  Nguyễn Văn  ",
            "TENDG": "  An ",
            "EMAILDG": "an@example.com",
            "SOCMND": "123456789012",
            "GIOITINH": 1,
            "NGAYSINH": datetime(2001, 5, 15),
            "DIACHI": "Quận 1",
            "DIENTHOAI": "0912345678",
            "NGAYLAMTHE": issue_date,
            "NGAYHETHAN": ReaderActions.add_months(issue_date, 12),
            "HOATDONG": 1,
        }

    def test_add_months_uses_calendar_months(self):
        self.assertEqual(
            ReaderActions.add_months(datetime(2024, 1, 31), 1),
            datetime(2024, 2, 29),
        )
        self.assertEqual(
            ReaderActions.add_months(datetime(2025, 1, 31), 1),
            datetime(2025, 2, 28),
        )

    def test_valid_data_is_normalized(self):
        result = ReaderActions.validate_reader_data(self.valid_reader())
        self.assertEqual(result["HODG"], "Nguyễn Văn")
        self.assertEqual(result["TENDG"], "An")
        self.assertEqual(result["SOCMND"], "123456789012")
        self.assertEqual(result["HOATDONG"], 1)

    def test_legacy_nine_digit_identity_is_accepted(self):
        data = self.valid_reader()
        data["SOCMND"] = "123456789"
        self.assertEqual(
            ReaderActions.validate_reader_data(data)["SOCMND"],
            "123456789",
        )

    def test_invalid_identity_email_and_phone_are_rejected(self):
        invalid_values = (
            ("SOCMND", "123ABC", "CMND/CCCD"),
            ("EMAILDG", "not-an-email", "Email"),
            ("DIENTHOAI", "090-123", "Số điện thoại"),
        )
        for field, value, message in invalid_values:
            with self.subTest(field=field):
                data = self.valid_reader()
                data[field] = value
                with self.assertRaisesRegex(ValueError, message):
                    ReaderActions.validate_reader_data(data)

    def test_future_birth_date_is_rejected(self):
        data = self.valid_reader()
        data["NGAYSINH"] = datetime.now() + timedelta(days=1)
        with self.assertRaisesRegex(ValueError, "tương lai"):
            ReaderActions.validate_reader_data(data)

    def test_expiry_cannot_precede_issue_date(self):
        data = self.valid_reader()
        data["NGAYHETHAN"] = data["NGAYLAMTHE"] - timedelta(days=1)
        with self.assertRaisesRegex(ValueError, "trước ngày làm thẻ"):
            ReaderActions.validate_reader_data(data)


class FakeCursor:
    """Records EXEC calls; returns a scripted result set per procedure name."""

    def __init__(self, results=None, error=None):
        self.calls = []
        self.results = results or {}
        self.error = error
        self.description = None
        self._rows = []

    def execute(self, query, params=()):
        self.calls.append((" ".join(query.split()), tuple(params)))
        if self.error is not None:
            raise self.error
        for name, (columns, rows) in self.results.items():
            if name in query:
                self.description = [(column,) for column in columns]
                self._rows = list(rows)
                return self
        self.description = None
        self._rows = []
        return self

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


DETAIL_COLUMNS = ("MADG", "HODG", "TENDG", "EMAILDG", "SOCMND", "GIOITINH", "NGAYSINH",
                  "DIACHI", "DIENTHOAI", "NGAYLAMTHE", "NGAYHETHAN", "HOATDONG")


def detail_row(active=1):
    return (7, "Nguyễn Văn", "An", "an@example.com", "123456789012", 1,
            datetime(2001, 5, 15), "Quận 1", "0912345678",
            datetime(2026, 1, 1), datetime(2027, 1, 1), active)


class ReaderDatabaseWorkflowTests(unittest.TestCase):
    """Python only sends EXEC; the rules live in sql/08_server_side_crud.sql."""

    def run_with(self, cursor, func, *args, **kwargs):
        connection = FakeConnection(cursor)
        with patch("database.get_connection", return_value=connection):
            return func(*args, **kwargs), connection

    def test_reader_update_calls_stored_procedure_with_merged_fields(self):
        cursor = FakeCursor({"sp_DocGia_ChiTiet": (DETAIL_COLUMNS, [detail_row()])})
        changes = {"TENDG": "Bình", "SOCMND": "999999999999", "DIACHI": "Quận 3"}
        updated, connection = self.run_with(cursor, ReaderActions.update, 7, changes)

        self.assertTrue(updated)
        self.assertTrue(connection.committed)
        query, params = cursor.calls[-1]
        self.assertTrue(query.startswith("EXEC dbo.sp_DocGia_CapNhat"))
        self.assertEqual(params[0], 7)
        self.assertEqual(params[2], "Bình")            # changed
        self.assertEqual(params[1], "Nguyễn Văn")      # kept from the current card
        self.assertEqual(params[4], "999999999999")
        self.assertNotIn("NGAYLAMTHE", query)
        self.assertNotIn("HOATDONG", query)

    def test_locked_reader_cannot_be_edited(self):
        cursor = FakeCursor({"sp_DocGia_ChiTiet": (DETAIL_COLUMNS, [detail_row(active=0)])})
        with self.assertRaisesRegex(ValueError, "dữ liệu lịch sử"):
            self.run_with(cursor, ReaderActions.update, 7, {"TENDG": "Bình"})
        self.assertFalse(any("sp_DocGia_CapNhat" in call[0] for call in cursor.calls))

    def test_lost_card_replacement_is_one_procedure_call(self):
        cursor = FakeCursor({"sp_DocGia_CapLaiThe": (("MADG",), [(88,)])})
        new_id, connection = self.run_with(cursor, ReaderActions.cap_lai_the_mat, 7, so_thang=12)

        self.assertEqual(new_id, 88)
        self.assertTrue(connection.committed)
        self.assertEqual(cursor.calls, [("EXEC dbo.sp_DocGia_CapLaiThe @OldMADG=?, @SoThang=?", (7, 12))])

    def test_borrow_eligibility_comes_from_server(self):
        cursor = FakeCursor({"sp_DocGia_KiemTraMuonSach": (
            ("HopLe", "LyDo", "DangGiu"), [(1, "Thẻ hợp lệ", 2)])})
        (valid, message, active_books), _ = self.run_with(
            cursor, ReaderActions.kiem_tra_the_hop_le_muon_sach, 88)

        self.assertTrue(valid)
        self.assertEqual(message, "Thẻ hợp lệ")
        self.assertEqual(active_books, 2)
        self.assertEqual(cursor.calls[0][1], (88,))

    def test_active_readers_are_filtered_on_server(self):
        cursor = FakeCursor({"sp_DocGia_DanhSachHoatDong": (
            ("MADG", "HODG", "TENDG", "SOCMND"), [(3, "Lê", "Hoa", "123456789")])})
        rows, _ = self.run_with(cursor, ReaderActions.get_active_readers)

        self.assertEqual(rows, [{"MADG": 3, "HODG": "Lê", "TENDG": "Hoa", "SOCMND": "123456789"}])
        self.assertEqual(cursor.calls[0][0], "EXEC dbo.sp_DocGia_DanhSachHoatDong")

    def test_stored_procedure_throw_becomes_value_error_with_server_text(self):
        import pyodbc
        error = pyodbc.ProgrammingError(
            "42000",
            "[42000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]"
            "Không tìm thấy thẻ độc giả; vui lòng làm mới danh sách! (52106) (SQLExecDirectW)",
        )
        cursor = FakeCursor(error=error)
        connection = FakeConnection(cursor)
        with patch("database.get_connection", return_value=connection):
            with self.assertRaisesRegex(ValueError, "^Không tìm thấy thẻ độc giả"):
                ReaderActions.delete(999)
        self.assertTrue(connection.rolled_back)

    def test_fk_violation_still_maps_to_teacher_message(self):
        import pyodbc
        from database import FK_DELETE_MESSAGE
        error = pyodbc.IntegrityError(
            "23000", "[23000] [SQL Server]The DELETE statement conflicted with the "
                     "REFERENCE constraint \"FK_PHIEUMUON_DOCGIA\". (547) (SQLExecDirectW)")
        cursor = FakeCursor(error=error)
        with patch("database.get_connection", return_value=FakeConnection(cursor)):
            with self.assertRaises(ValueError) as caught:
                ReaderActions.delete(1)
        self.assertEqual(str(caught.exception), FK_DELETE_MESSAGE)


class FormStateAndScreenWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        import customtkinter as ctk
        try:
            cls.root = ctk.CTk()
        except tk.TclError as error:
            raise unittest.SkipTest(f"Tk unavailable: {error}")
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        import customtkinter as ctk
        from ui_state import FormStateController, build_command_bar
        self.frame = ctk.CTkFrame(self.root)
        self.inputs = {
            "ID": ctk.CTkEntry(self.frame),
            "NAME": ctk.CTkEntry(self.frame),
            "TYPE": ctk.CTkComboBox(self.frame, values=["A", "B"]),
        }
        noop = lambda: None  # noqa: E731
        self.buttons = build_command_bar(
            self.frame, {k: noop for k in ("add", "edit", "delete", "save", "cancel", "exit")}
        )
        self.extra = ctk.CTkButton(self.frame, text="Gia hạn")
        self.form = FormStateController(
            self.inputs, self.buttons, key_fields=("ID",),
            view_only_widgets=[self.extra], defaults={"TYPE": "A"},
        )
        self.form.to_view()

    def tearDown(self):
        self.frame.destroy()

    def state(self, widget):
        return widget.cget("state")

    def assert_buttons(self, on, off):
        for name in on:
            self.assertEqual(self.state(self.buttons[name]), "normal", name)
        for name in off:
            self.assertEqual(self.state(self.buttons[name]), "disabled", name)

    def test_view_locks_inputs_and_disables_save_cancel(self):
        from ui_state import FormMode
        self.assertIs(self.form.mode, FormMode.VIEW)
        for widget in self.inputs.values():
            self.assertEqual(self.state(widget), "disabled")
        self.assert_buttons(on=("add", "edit", "delete", "exit"), off=("save", "cancel"))
        self.assertEqual(self.state(self.extra), "normal")

    def test_add_unlocks_clears_and_swaps_buttons(self):
        self.form.fill({"ID": "S01", "NAME": "Old", "TYPE": "B"})
        self.form.to_add()
        self.assertEqual(self.form.values(), {"ID": "", "NAME": "", "TYPE": "A"})
        self.assertEqual(self.state(self.inputs["ID"]), "normal")
        self.assertEqual(self.state(self.inputs["TYPE"]), "readonly")
        self.assert_buttons(on=("save", "cancel"), off=("add", "edit", "delete", "exit"))
        self.assertEqual(self.state(self.extra), "disabled")

    def test_edit_keeps_primary_key_locked(self):
        self.form.fill({"ID": "S01", "NAME": "Old", "TYPE": "B"})
        self.form.to_edit()
        self.assertEqual(self.state(self.inputs["ID"]), "disabled")
        self.assertEqual(self.state(self.inputs["NAME"]), "normal")
        self.assert_buttons(on=("save", "cancel"), off=("add", "edit", "delete", "exit"))

    def test_cancel_restores_original_values_and_locks(self):
        from ui_state import FormMode
        self.form.fill({"ID": "S01", "NAME": "Old", "TYPE": "B"})
        self.form.to_edit()
        self.inputs["NAME"].delete(0, "end")
        self.inputs["NAME"].insert(0, "Changed")
        self.form.cancel()
        self.assertEqual(self.form.values()["NAME"], "Old")
        self.assertIs(self.form.mode, FormMode.VIEW)
        self.assertEqual(self.state(self.inputs["NAME"]), "disabled")

    def test_values_are_stripped(self):
        self.form.to_add()
        self.inputs["NAME"].insert(0, "   Nguyễn An   ")
        self.assertEqual(self.form.values()["NAME"], "Nguyễn An")

    @patch("book_management.book_screen.SachDAO")
    def test_book_screen_switches_tree_to_isbn_and_shows_zero_copy_titles(self, mock_dao):
        from book_management.book_screen import BookScreen, ENTITY_COPY, ENTITY_TITLE
        mock_dao.get_all_sach.return_value = [
            {"MASACH": "S0001", "ISBN": "9786041001", "TENSACH": "Mắt biếc",
             "THELOAI": "Văn học", "HOTENTG": "Nguyễn Nhật Ánh", "ViTri": "Kệ A1",
             "GiaBia": 95000, "TINHTRANG": 1, "CHOMUON": 0, "MANGANTU": 1}
        ]
        mock_dao.get_all_isbn.return_value = [
            {"ISBN": "9786041001", "TENSACH": "Mắt biếc", "THELOAI": "Văn học",
             "HOTENTG": "Nguyễn Nhật Ánh", "NGONNGU": "Tiếng Việt", "NHAXB": "NXB Trẻ",
             "GIA": 95000, "GiaBia": 95000, "TongBanSao": 1, "BanSaoKhaDung": 1},
            {"ISBN": "ISBN000099", "TENSACH": "Sách Mới Chưa Nhập Bản Sao", "THELOAI": "Khoa học",
             "HOTENTG": "Tác giả B", "NGONNGU": "Tiếng Việt", "NHAXB": "NXB Giáo Dục",
             "GIA": 120000, "GiaBia": 120000, "TongBanSao": 0, "BanSaoKhaDung": 0},
        ]
        mock_dao.get_danh_muc_ngan_tu.return_value = [{"MANGANTU": 1, "KE": "Kệ A1", "MOTA": "Tầng 1"}]
        mock_dao.get_danh_muc_the_loai.return_value = [{"MATL": "TL001", "THELOAI": "Văn học"}]
        mock_dao.get_danh_muc_tac_gia.return_value = [{"MATACGIA": 1, "HOTENTG": "Nguyễn Nhật Ánh"}]
        mock_dao.get_danh_muc_ngon_ngu.return_value = [{"MANGONNGU": 1, "NGONNGU": "Tiếng Việt"}]
        mock_dao.get_dau_sach.return_value = {
            "ISBN": "ISBN000099", "TENSACH": "Sách Mới Chưa Nhập Bản Sao", "GIA": 120000,
            "MATL": "TL001", "MATACGIA": 1, "MANGONNGU": 1, "NHAXB": "NXB Giáo Dục",
            "SOTRANG": 200, "KHOSACH": "A5", "LANXUATBAN": 1, "NOIDUNG": "",
        }

        screen = BookScreen(self.root, current_user={"RoleName": "QUANLY"})
        try:
            self.assertEqual(screen.entity, ENTITY_COPY)
            self.assertEqual(list(screen.tree.get_children()), ["S0001"])
            self.assertEqual(screen.btn_toggle_status.cget("state"), "normal")

            screen.selector.set(ENTITY_TITLE)
            screen._switch_entity(ENTITY_TITLE)
            self.assertIn("ISBN000099", screen.tree.get_children())
            self.assertEqual(screen.btn_toggle_status.cget("state"), "disabled")

            screen.tree.selection_set("ISBN000099")
            screen._on_select()
            self.assertEqual(screen.form.values()["ISBN"], "ISBN000099")
        finally:
            screen.destroy()


class BorrowingFixesTests(unittest.TestCase):
    def test_parse_madg_input_handles_combo_and_raw_id(self):
        from borrowing_and_returns.borrowing_screen import BorrowingScreen
        dummy = BorrowingScreen.__new__(BorrowingScreen)
        self.assertEqual(dummy._parse_madg_input("12 | Nguyễn An (079201000001)"), "12")
        self.assertEqual(dummy._parse_madg_input("  7  "), "7")
        self.assertEqual(dummy._parse_madg_input("-- Chọn hoặc gõ mã ĐG --"), "")

    @patch("borrowing_and_returns.borrowing_actions.get_connection")
    @patch("borrowing_and_returns.borrowing_actions.SachDAO.kiem_tra_sach_cho_muon")
    @patch("borrowing_and_returns.borrowing_actions.DocGiaDAO.kiem_tra_the_hop_le_muon_sach")
    def test_tao_phieu_muon_reraises_value_error_without_runtime_wrapping(
        self, mock_check_dg, mock_check_sach, mock_get_conn
    ):
        from unittest.mock import MagicMock
        from borrowing_and_returns.borrowing_actions import MuonTraDAO
        mock_check_dg.return_value = (True, "OK", 0)
        mock_check_sach.return_value = (True, "OK", {"MASACH": "S0001", "TENSACH": "Mắt biếc"})

        conn = MagicMock()
        conn.__enter__.return_value = conn
        cursor = conn.cursor.return_value
        cursor.fetchone.return_value = (101,)
        cursor.rowcount = 0
        mock_get_conn.return_value = conn

        with self.assertRaisesRegex(ValueError, "vừa có người khác mượn"):
            MuonTraDAO.tao_phieu_muon(1, 1, 1, ["S0001"])
        conn.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
