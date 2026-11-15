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


class ReplacementCursor:
    def __init__(self):
        self.calls = []
        self.rowcount = -1
        self._result = None

    def execute(self, query, params=()):
        self.calls.append((query, params))
        if "WITH (UPDLOCK, HOLDLOCK)" in query:
            self._result = (
                "Nguyễn Văn", "An", "an@example.com", "123456789012", 1,
                datetime(2001, 5, 15), "Quận 1", "0912345678", 1,
            )
        elif query.lstrip().startswith("UPDATE"):
            self.rowcount = 1
        elif "OUTPUT INSERTED.MADG" in query:
            self._result = (88,)
        return self

    def fetchone(self):
        return self._result


class EligibilityCursor:
    def __init__(self):
        self.calls = []
        self._results = [
            (1, 0, "31/12/2027", "123456789012"),
            (2,),
        ]

    def execute(self, query, params=()):
        self.calls.append((query, params))
        return self

    def fetchone(self):
        return self._results.pop(0)


class UpdateCursor:
    def __init__(self, active=1):
        self.calls = []
        self.rowcount = -1
        self._result = None
        self.active = active

    def execute(self, query, params=()):
        self.calls.append((query, params))
        compact_query = " ".join(query.split())
        if "SELECT MADG" in query and "WITH (UPDLOCK, HOLDLOCK)" in query:
            self._result = (
                7, "Nguyễn Văn", "An", "an@example.com", "123456789012", 1,
                datetime(2001, 5, 15), "Quận 1", "0912345678",
                datetime(2026, 1, 1), datetime(2027, 1, 1), self.active,
            )
        elif compact_query.startswith("SELECT COUNT(*)"):
            self._result = (0,)
        elif "UPDATE dbo.DOCGIA SET SOCMND" in compact_query:
            self.rowcount = 2
        elif compact_query.startswith("UPDATE dbo.DOCGIA SET HODG"):
            self.rowcount = 1
        return self

    def fetchone(self):
        return self._result


class ReaderDatabaseWorkflowTests(unittest.TestCase):
    def test_reader_update_preserves_card_fields_and_commits(self):
        cursor = UpdateCursor()
        connection = FakeConnection(cursor)
        changes = {
            "HODG": "Nguyễn Văn",
            "TENDG": "Bình",
            "EMAILDG": "binh@example.com",
            "SOCMND": "999999999999",
            "GIOITINH": 1,
            "NGAYSINH": datetime(2001, 5, 15),
            "DIACHI": "Quận 3",
            "DIENTHOAI": "0987654321",
        }
        with patch("reader_management.reader_actions.get_connection", return_value=connection):
            updated = ReaderActions.update(7, changes)

        self.assertTrue(updated)
        self.assertTrue(connection.committed)
        self.assertFalse(connection.rolled_back)
        identity_updates = [call for call in cursor.calls if "SET SOCMND = ?" in call[0]]
        self.assertEqual(identity_updates[0][1], ("999999999999", "123456789012"))
        final_update = cursor.calls[-1]
        self.assertEqual(final_update[1][-1], 7)
        self.assertNotIn("NGAYLAMTHE =", final_update[0])
        self.assertNotIn("NGAYHETHAN =", final_update[0])
        self.assertNotIn("SET HOATDONG =", final_update[0])

    def test_locked_reader_cannot_be_edited(self):
        cursor = UpdateCursor(active=0)
        connection = FakeConnection(cursor)
        with patch("reader_management.reader_actions.get_connection", return_value=connection):
            with self.assertRaisesRegex(ValueError, "dữ liệu lịch sử"):
                ReaderActions.update(7, {"TENDG": "Bình"})

        self.assertTrue(connection.rolled_back)
        self.assertFalse(connection.committed)

    def test_lost_card_replacement_is_atomic_and_returns_new_id(self):
        cursor = ReplacementCursor()
        connection = FakeConnection(cursor)
        with patch("reader_management.reader_actions.get_connection", return_value=connection):
            new_id = ReaderActions.cap_lai_the_mat(7, so_thang=12)

        self.assertEqual(new_id, 88)
        self.assertTrue(connection.committed)
        self.assertFalse(connection.rolled_back)
        self.assertEqual(len(cursor.calls), 3)
        self.assertIn("UPDLOCK, HOLDLOCK", cursor.calls[0][0])
        self.assertIn("HOATDONG = 0", cursor.calls[1][0])
        self.assertIn("INSERT INTO dbo.DOCGIA", cursor.calls[2][0])

    def test_borrow_limit_counts_all_cards_for_same_identity(self):
        cursor = EligibilityCursor()
        connection = FakeConnection(cursor)
        with patch("reader_management.reader_actions.get_connection", return_value=connection):
            valid, message, active_books = ReaderActions.kiem_tra_the_hop_le_muon_sach(88)

        self.assertTrue(valid)
        self.assertEqual(message, "Thẻ hợp lệ")
        self.assertEqual(active_books, 2)
        self.assertEqual(cursor.calls[1][1], ("123456789012",))
        self.assertIn("INNER JOIN dbo.DOCGIA", cursor.calls[1][0])


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
