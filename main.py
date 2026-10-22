"""Application entry point with integrated login session and dashboard navigation."""

import customtkinter as ctk
import ctk_patch  # Kích hoạt bản vá placeholder cho CustomTkinter
from login.login_screen import LoginScreen
from dashboard import Dashboard
from database import CURRENT_SESSION


class LibraryApplication(ctk.CTk):
    """Cửa sổ ứng dụng chính Quản Lý Thư Viện."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Hệ Thống Quản Lý Thư Viện (Library Management System)")
        self.geometry("1200x740")
        self.minsize(980, 620)

        self._active_frame = None
        self._show_login_screen()

    def _show_login_screen(self) -> None:
        """Hiển thị màn hình Đăng nhập."""
        if self._active_frame:
            self._active_frame.destroy()

        self._active_frame = LoginScreen(self, on_login=self._on_login_success)
        self._active_frame.pack(fill="both", expand=True)

    def _on_login_success(self, username: str, password: str) -> None:
        """Xử lý sau khi người dùng xác thực tài khoản thành công."""
        if self._active_frame:
            self._active_frame.destroy()

        self._active_frame = Dashboard(self, on_logout=self._on_logout)
        self._active_frame.pack(fill="both", expand=True)

    def _on_logout(self) -> None:
        """Đăng xuất phiên làm việc hiện tại và quay về màn hình đăng nhập."""
        CURRENT_SESSION["login_name"] = ""
        CURRENT_SESSION["password"] = ""
        CURRENT_SESSION["user_info"] = None
        self._show_login_screen()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = LibraryApplication()
    app.mainloop()
