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


if __name__ == "__main__":
    unittest.main()
