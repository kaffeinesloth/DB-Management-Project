"""Unit tests for account validation, connection/SQL security, error codes, and AccountScreen UI."""

import tkinter as tk
import unittest
from unittest.mock import MagicMock, patch

import customtkinter as ctk
import pyodbc

import ctk_patch  # noqa: F401
import database
from account_management.account_actions import (
    change_own_password,
    validate_account_input,
    validate_login_name,
    validate_new_employee,
)
from account_management.account_screen import AccountScreen
from database import (
    FK_DELETE_MESSAGE,
    build_connection_string,
    friendly_message,
    has_error_code,
    is_fk_violation,
    odbc_quote,
    server_message,
    sql_error_codes,
)


def _attributes(conn_str: str):
    """Parse an ODBC connection string the way the driver manager does ({...} quoting)."""
    attrs, i = {}, 0
    while i < len(conn_str):
        eq = conn_str.index("=", i)
        key = conn_str[i:eq]
        i = eq + 1
        if conn_str[i] == "{":
            i += 1
            value = []
            while True:
                if conn_str[i] == "}":
                    if i + 1 < len(conn_str) and conn_str[i + 1] == "}":
                        value.append("}")
                        i += 2
                        continue
                    i += 1
                    break
                value.append(conn_str[i])
                i += 1
            attrs[key.upper()] = "".join(value)
        else:
            end = conn_str.find(";", i)
            end = len(conn_str) if end == -1 else end
            attrs[key.upper()] = conn_str[i:end]
            i = end
        if i < len(conn_str) and conn_str[i] == ";":
            i += 1
    return attrs


FK_ERROR = Exception(
    "('23000', '[23000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]The DELETE statement "
    "conflicted with the REFERENCE constraint \"FK_PHIEUMUON_DOCGIA\". The conflict occurred in "
    "database \"LibraryManagement\", table \"dbo.PHIEUMUON\", column \"MADG\". (547) (SQLExecDirectW)')"
)
PK_ERROR = Exception("[23000] [SQL Server]Violation of PRIMARY KEY constraint 'PK_SACH'. (2627)")
THROW_ERROR = Exception(
    "('42000', '[42000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]"
    "Mật khẩu cũ không đúng. (51034) (SQLExecDirectW)')"
)


class AccountValidationTests(unittest.TestCase):
    def test_valid_input_is_normalized(self):
        result = validate_account_input(5, "  nv_5  ", "Secret1!", "thuthu")
        self.assertEqual(result, (5, "nv_5", "Secret1!", "THUTHU"))

    def test_invalid_employee_id_is_rejected(self):
        for value in (0, -1, "abc", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_account_input(value, "nv_5", "Secret1!", "THUTHU")

    def test_blank_login_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Tên đăng nhập"):
            validate_account_input(5, "   ", "Secret1!", "THUTHU")

    def test_short_password_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ít nhất 6"):
            validate_account_input(5, "nv_5", "12345", "THUTHU")

    def test_unknown_role_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "THUTHU hoặc QUANLY"):
            validate_account_input(5, "nv_5", "Secret1!", "DOCGIA")

    def test_new_employee_form_is_normalized(self):
        result = validate_new_employee(
            "  Nguyễn ", " An ", True, " Quận 1 ", "0901234567",
            " AN@EXAMPLE.COM ", " nv_an ", "Secret1!", "thuthu",
        )
        self.assertEqual(result["family_name"], "Nguyễn")
        self.assertEqual(result["given_name"], "An")
        self.assertEqual(result["email"], "an@example.com")
        self.assertEqual(result["login_name"], "nv_an")

    def test_new_employee_rejects_bad_phone_and_email(self):
        with self.assertRaisesRegex(ValueError, "Điện thoại"):
            validate_new_employee(
                "Nguyễn", "An", True, "", "abc", "an@example.com",
                "nv_an", "Secret1!", "THUTHU",
            )
        with self.assertRaisesRegex(ValueError, "Email"):
            validate_new_employee(
                "Nguyễn", "An", True, "", "0901234567", "invalid",
                "nv_an", "Secret1!", "THUTHU",
            )


class ConnectionStringInjectionTests(unittest.TestCase):
    PAYLOADS = (
        "x;Trusted_Connection=yes",
        "x};Trusted_Connection=yes;{",
        "' OR '1'='1",
        "a;Database=master;",
        "p}}w;d",
    )

    def test_password_cannot_add_attributes(self):
        for payload in self.PAYLOADS:
            with self.subTest(payload=payload):
                attrs = _attributes(build_connection_string("admin", payload, server="h,1", database="db"))
                self.assertEqual(attrs["PWD"], payload)
                self.assertNotIn("TRUSTED_CONNECTION", attrs)
                self.assertEqual(attrs["DATABASE"], "db")

    def test_username_cannot_add_attributes(self):
        attrs = _attributes(build_connection_string("admin;Trusted_Connection=yes", "p", server="h", database="d"))
        self.assertEqual(attrs["UID"], "admin;Trusted_Connection=yes")
        self.assertNotIn("TRUSTED_CONNECTION", attrs)

    def test_quote_doubles_closing_brace(self):
        self.assertEqual(odbc_quote("a}b"), "{a}}b}")


class LoginNameAndPasswordRules(unittest.TestCase):
    def test_login_name_must_be_typed_and_well_formed(self):
        self.assertEqual(validate_login_name("  nv_hoa "), "nv_hoa")
        for bad in ("", "1abc", "ab", "nv hoa", "nv'; DROP LOGIN admin;--", "x@gmail.com"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_login_name(bad)

    def test_change_password_rules_before_database(self):
        cases = (
            (("", "abcdef", "abcdef"), "mật khẩu cũ"),
            (("old123", "abc", "abc"), "ít nhất 6"),
            (("old123", "abcdef", "abcdeX"), "không khớp"),
            (("same12", "same12", "same12"), "khác mật khẩu cũ"),
        )
        for args, message in cases:
            with self.subTest(args=args), self.assertRaisesRegex(ValueError, message):
                change_own_password(*args)


class SqlErrorCodeTests(unittest.TestCase):
    def test_extracts_native_codes(self):
        self.assertIn(547, sql_error_codes(FK_ERROR))
        self.assertEqual(sql_error_codes(PK_ERROR), {2627})

    def test_fk_violation_by_code_not_wording(self):
        self.assertTrue(is_fk_violation(FK_ERROR))
        self.assertFalse(is_fk_violation(PK_ERROR))
        self.assertFalse(is_fk_violation(Exception("REFERENCE constraint mentioned in text")))

    def test_friendly_messages(self):
        self.assertEqual(friendly_message(FK_ERROR), FK_DELETE_MESSAGE)
        self.assertIn("đã tồn tại", friendly_message(PK_ERROR, "sách"))
        self.assertIn("không có quyền", friendly_message(Exception("permission denied (229)")))
        self.assertIsNone(friendly_message(Exception("something else")))

    def test_fk_message_matches_teacher_wording(self):
        self.assertEqual(
            FK_DELETE_MESSAGE,
            "Không thể xóa vì dữ liệu này đã phát sinh giao dịch liên quan trong hệ thống!",
        )

    def test_server_message_strips_driver_noise(self):
        self.assertEqual(server_message(THROW_ERROR), "Mật khẩu cũ không đúng.")

    def test_small_numbers_are_not_codes(self):
        self.assertFalse(has_error_code(Exception("value (5) is invalid"), 5))


class ManagedConnectionTests(unittest.TestCase):
    def test_pooling_is_disabled(self):
        self.assertFalse(pyodbc.pooling)

    def test_context_manager_closes_connection_on_normal_exit(self):
        raw = MagicMock()
        with database.ManagedConnection(raw) as conn:
            conn.cursor()
        raw.__enter__.assert_called_once()
        raw.__exit__.assert_called_once()
        raw.close.assert_called_once()
        self.assertNotIn(conn, database._ACTIVE_CONNECTIONS)

    def test_context_manager_closes_connection_on_exception(self):
        raw = MagicMock()
        raw.__exit__.return_value = False
        with self.assertRaises(RuntimeError):
            with database.ManagedConnection(raw):
                raise RuntimeError("boom")
        raw.close.assert_called_once()

    def test_clear_session_closes_all_tracked_connections(self):
        raw1, raw2 = MagicMock(), MagicMock()
        c1 = database.ManagedConnection(raw1)
        c2 = database.ManagedConnection(raw2)
        self.assertIn(c1, database._ACTIVE_CONNECTIONS)
        self.assertIn(c2, database._ACTIVE_CONNECTIONS)
        database.clear_session()
        raw1.close.assert_called_once()
        raw2.close.assert_called_once()
        self.assertEqual(len(database._ACTIVE_CONNECTIONS), 0)


class AccountScreenDynamicButtonsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = ctk.CTk()
        except tk.TclError as error:
            raise unittest.SkipTest(f"Tk unavailable: {error}")
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    @patch("account_management.account_screen.list_employees_without_account")
    @patch("account_management.account_screen.list_employee_accounts")
    def test_account_screen_toggles_buttons_by_selected_employee(
        self, mock_list_all, mock_list_eligible
    ):
        sample_rows = [
            {"MANV": 1, "HoTen": "Nguyễn Hương", "Email": "h@lib.local",
             "DaCoTaiKhoan": True, "LoginName": "nv_huong", "RoleName": "THUTHU"},
            {"MANV": 3, "HoTen": "Lê Mai", "Email": "m@lib.local",
             "DaCoTaiKhoan": True, "LoginName": "admin", "RoleName": "QUANLY"},
            {"MANV": 4, "HoTen": "Phạm Nam", "Email": "n@lib.local",
             "DaCoTaiKhoan": False, "LoginName": "", "RoleName": ""},
            {"MANV": 5, "HoTen": "Võ Oanh", "Email": "o@lib.local",
             "DaCoTaiKhoan": False, "LoginName": "", "RoleName": ""},
        ]
        mock_list_all.return_value = sample_rows
        mock_list_eligible.return_value = [r for r in sample_rows if not r["DaCoTaiKhoan"]]

        screen = AccountScreen(self.root, current_user={"LoginName": "admin", "RoleName": "QUANLY"})
        try:
            btns = screen.state.buttons
            screen.tree.selection_set("1")
            screen._on_select()
            self.assertEqual(btns["add"].cget("state"), "disabled")
            self.assertEqual(btns["edit"].cget("state"), "normal")
            self.assertEqual(btns["delete"].cget("state"), "normal")
            self.assertEqual(screen.btn_reset.cget("state"), "normal")

            screen.tree.selection_set("3")
            screen._on_select()
            self.assertEqual(btns["add"].cget("state"), "disabled")
            self.assertEqual(btns["edit"].cget("state"), "disabled")
            self.assertEqual(btns["delete"].cget("state"), "disabled")
            self.assertEqual(screen.btn_reset.cget("state"), "disabled")

            screen.tree.selection_set("5")
            screen._on_select()
            self.assertEqual(btns["add"].cget("state"), "normal")
            self.assertEqual(btns["edit"].cget("state"), "disabled")
            self.assertEqual(btns["delete"].cget("state"), "disabled")
            self.assertEqual(screen.btn_reset.cget("state"), "disabled")

            screen.on_add()
            self.assertEqual(screen.state.values()["employee"], "5 - Võ Oanh")
        finally:
            screen.destroy()


if __name__ == "__main__":
    unittest.main()
