"""Tests for the shared reader's read-only catalogue query."""

import unittest
from unittest.mock import MagicMock, patch

from catalog_search.catalog_actions import search_catalog


class CatalogSearchTests(unittest.TestCase):
    @patch("catalog_search.catalog_actions.get_connection")
    def test_search_uses_parameters_and_maps_rows(self, mock_get_connection):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor = connection.cursor.return_value
        cursor.fetchall.return_value = [
            ("S001", "9780000001", "Cơ sở dữ liệu", "Nguyễn An", "Giáo trình",
             "Tiếng Việt", "NXB Trẻ", True, "Kệ A", "Tầng 1"),
        ]
        mock_get_connection.return_value = connection

        rows = search_catalog("dữ liệu", available_only=True)

        self.assertEqual(rows[0]["MASACH"], "S001")
        self.assertTrue(rows[0]["COSAN"])
        sql, *parameters = cursor.execute.call_args.args
        self.assertIn("v_TraCuuSachDocGia", sql)
        self.assertEqual(parameters[0], "dữ liệu")
        self.assertEqual(parameters[-1], 1)
        self.assertNotIn("dữ liệu", sql)


if __name__ == "__main__":
    unittest.main()
