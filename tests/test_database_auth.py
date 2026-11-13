"""Unit tests for fast, deterministic SQL Server authentication."""

import unittest
from unittest.mock import Mock, patch

import pyodbc

import database


class DatabaseAuthenticationTests(unittest.TestCase):
    def tearDown(self):
        database.clear_session()

    @patch("database.pyodbc.connect")
    @patch("database.pyodbc.drivers")
    def test_connection_uses_one_preferred_installed_driver(
        self, mock_drivers, mock_connect
    ):
        mock_drivers.return_value = [
            "SQL Server",
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 17 for SQL Server",
        ]
        expected_connection = Mock()
        mock_connect.return_value = expected_connection

        result = database.get_connection(
            "employee", "secret", server="localhost,1433", database="LibraryManagement"
        )

        self.assertIs(result, expected_connection)
        mock_connect.assert_called_once()
        connection_string = mock_connect.call_args.args[0]
        self.assertIn("DRIVER={ODBC Driver 18 for SQL Server}", connection_string)

    @patch("database.pyodbc.connect")
    @patch("database.pyodbc.drivers")
    def test_driver_compatibility_error_uses_next_installed_driver(
        self, mock_drivers, mock_connect
    ):
        mock_drivers.return_value = [
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 17 for SQL Server",
        ]
        expected_connection = Mock()
        mock_connect.side_effect = [
            pyodbc.Error("08001", "Encryption not supported on the client"),
            expected_connection,
        ]

        result = database.get_connection("employee", "secret")

        self.assertIs(result, expected_connection)
        self.assertEqual(mock_connect.call_count, 2)

    @patch("database.pyodbc.connect")
    @patch("database.pyodbc.drivers")
    def test_login_failure_does_not_retry_another_driver(
        self, mock_drivers, mock_connect
    ):
        mock_drivers.return_value = [
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 17 for SQL Server",
        ]
        mock_connect.side_effect = pyodbc.Error("28000", "Login failed (18456)")

        with self.assertRaises(pyodbc.Error):
            database.get_connection("wrong-user", "wrong-password")

        mock_connect.assert_called_once()

    @patch("database.get_connection")
    def test_invalid_credentials_stop_after_first_attempt(self, mock_get_connection):
        mock_get_connection.side_effect = pyodbc.Error(
            "28000", "[Microsoft][ODBC Driver 18 for SQL Server]Login failed (18456)"
        )

        with self.assertRaisesRegex(ValueError, "không chính xác"):
            database.dang_nhap_he_thong("wrong-user", "wrong-password")

        mock_get_connection.assert_called_once_with(
            "wrong-user",
            "wrong-password",
            server=database.SERVER_NAME,
            database=database.DATABASE_NAME,
        )

    @patch("database.get_connection")
    def test_valid_employee_account_returns_verified_identity(self, mock_get_connection):
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.fetchone.return_value = (
            "nv_huong", "1", "THUTHU", 1, "Nguyễn Hương",
            "huong@example.com", "Thủ thư",
        )
        mock_get_connection.return_value = connection

        result = database.dang_nhap_he_thong("nv_huong", "123456")

        self.assertEqual(result["MANV"], 1)
        self.assertEqual(result["RoleName"], "THUTHU")
        connection.close.assert_called_once()

    @patch("database.get_connection")
    def test_unlinked_account_is_rejected(self, mock_get_connection):
        connection = Mock()
        connection.cursor.return_value.fetchone.return_value = None
        mock_get_connection.return_value = connection

        with self.assertRaisesRegex(ValueError, "liên kết"):
            database.dang_nhap_he_thong("orphan_login", "123456")

        connection.close.assert_called_once()

    @patch("database.get_connection")
    def test_mismatched_employee_mapping_is_rejected(self, mock_get_connection):
        connection = Mock()
        connection.cursor.return_value.fetchone.return_value = (
            "orphan_login", "orphan_login", "THUTHU", 1,
            "Nguyễn Hương", "huong@example.com", "Thủ thư",
        )
        mock_get_connection.return_value = connection

        with self.assertRaisesRegex(ValueError, "liên kết"):
            database.dang_nhap_he_thong("orphan_login", "123456")

    @patch("database.get_connection")
    def test_unknown_role_is_rejected(self, mock_get_connection):
        connection = Mock()
        connection.cursor.return_value.fetchone.return_value = (
            "employee", "1", "db_owner", 1, "Nguyễn Hương",
            "huong@example.com", "Thủ thư",
        )
        mock_get_connection.return_value = connection

        with self.assertRaisesRegex(ValueError, "nhóm quyền"):
            database.dang_nhap_he_thong("employee", "123456")

    @patch("database.get_connection")
    def test_service_account_is_rejected(self, mock_get_connection):
        connection = Mock()
        mock_get_connection.return_value = connection

        with self.assertRaisesRegex(ValueError, "không được phép"):
            database.dang_nhap_he_thong("library_app", "secret")

        connection.cursor.assert_not_called()
        connection.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
