"""Application entry point inheriting 100% lifecycle from feature/qltv:login.py."""

import customtkinter as ctk
import ctk_patch
from login.login_screen import LoginForm
from dashboard import MainDashboard

# Cấu hình giao diện Dark Mode chuẩn đồ án
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def start_application() -> None:
    """
    Vòng đời ứng dụng Quản Lý Thư Viện:
    1. Khởi chạy cửa sổ đăng nhập riêng biệt LoginForm (420x560).
    2. Xác thực thành công -> Mở cửa sổ Dashboard chính (1260x740) với phân quyền người dùng.
    3. Khi đăng xuất -> Quay trở lại cửa sổ đăng nhập.
    4. Khi tắt cửa sổ -> Thoát hoàn toàn ứng dụng.
    """
    while True:
        # Bước 1: Mở màn hình đăng nhập
        login_app = LoginForm()
        login_app.mainloop()

        # Nếu người dùng tắt cửa sổ đăng nhập mà không đăng nhập -> Thoát hẳn
        if not getattr(login_app, "logged_in_user", None):
            break

        # Bước 2: Đăng nhập thành công -> Mở màn hình Dashboard
        current_user = login_app.logged_in_user
        logout_holder = {"logged_out": False}

        def on_logout():
            logout_holder["logged_out"] = True

        dashboard = MainDashboard(current_user, on_logout=on_logout)
        dashboard.mainloop()

        # Nếu người dùng đóng Dashboard bằng nút X (không phải bấm Đăng xuất) -> Thoát hẳn
        if not logout_holder["logged_out"]:
            break


# Bí danh tương thích
LibraryApplication = MainDashboard

if __name__ == "__main__":
    start_application()
