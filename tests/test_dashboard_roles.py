"""Tests for fail-closed dashboard role authorization."""

import unittest

from dashboard import require_dashboard_role


class DashboardRoleTests(unittest.TestCase):
    def test_known_roles_are_accepted(self):
        self.assertEqual(require_dashboard_role({"RoleName": "THUTHU"}), "THUTHU")
        self.assertEqual(require_dashboard_role({"RoleName": "quanly"}), "QUANLY")

    def test_missing_and_unknown_roles_are_rejected(self):
        for role in (None, "", "db_owner", "library_app_role", "ADMIN"):
            with self.subTest(role=role), self.assertRaisesRegex(
                ValueError, "nhóm quyền"
            ):
                require_dashboard_role({"RoleName": role})


if __name__ == "__main__":
    unittest.main()
