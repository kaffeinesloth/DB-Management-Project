"""Login validation and database operations."""

from typing import Dict, Any
from database import dang_nhap_he_thong, kiem_tra_dang_nhap, CURRENT_SESSION


def authenticate(username: str, password: str) -> Dict[str, Any]:
    """Xác thực đăng nhập trực tiếp qua SQL Server Authentication."""
    return dang_nhap_he_thong(username, password)


# Bí danh tương thích
LoginActions = authenticate
