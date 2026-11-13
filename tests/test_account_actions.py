"""Unit tests for account-management input validation."""

import unittest

from account_management.account_actions import validate_account_input, validate_new_employee


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

    def test_oversized_login_and_password_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "đăng nhập tối đa"):
            validate_account_input(5, "x" * 129, "Secret1!", "THUTHU")
        with self.assertRaisesRegex(ValueError, "Mật khẩu tối đa"):
            validate_account_input(5, "nv_5", "x" * 129, "THUTHU")

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

    def test_new_employee_rejects_invalid_names_and_unicode_phone_digits(self):
        for family_name, given_name in (("123", "An"), ("Nguyễn", "@@@")):
            with self.subTest(family_name=family_name, given_name=given_name):
                with self.assertRaisesRegex(ValueError, "chữ cái"):
                    validate_new_employee(
                        family_name, given_name, True, "", "0901234567",
                        "an@example.com", "nv_an", "Secret1!", "THUTHU",
                    )

        with self.assertRaisesRegex(ValueError, "10 đến 11"):
            validate_new_employee(
                "Nguyễn", "An", True, "", "٠٩٠١٢٣٤٥٦٧",
                "an@example.com", "nv_an", "Secret1!", "THUTHU",
            )


if __name__ == "__main__":
    unittest.main()
