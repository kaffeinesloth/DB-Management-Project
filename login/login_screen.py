"""Login screen inheriting 100% logic and design from feature/qltv."""

import customtkinter as ctk
import ctk_patch
import threading
from tkinter import messagebox
from typing import Optional, Callable
from database import dang_nhap_he_thong


class LoginForm(ctk.CTk):
    """Cửa sổ Đăng Nhập Hệ Thống chuẩn giao diện feature/qltv."""

    def __init__(self, on_login_success: Optional[Callable[[dict], None]] = None):
        super().__init__()
        self.on_login_success = on_login_success

        self.title("Quản Lý Thư Viện - Đăng Nhập")
        self.geometry("420x400")
        self.resizable(False, False)
        self.logged_in_user = None
        self.password_visible = False
        self._auth_result = None
        self._auth_in_progress = False

        # Căn giữa màn hình
        self.center_window()

        # Container chính
        self.frame = ctk.CTkFrame(self, corner_radius=15)
        self.frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Tiêu đề
        self.lbl_title = ctk.CTkLabel(
            self.frame, 
            text="ĐĂNG NHẬP HỆ THỐNG", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.lbl_title.pack(pady=(25, 6))

        self.lbl_subtitle = ctk.CTkLabel(
            self.frame, 
            text="Vui lòng đăng nhập để tiếp tục",
            font=ctk.CTkFont(size=12), 
            text_color="gray"
        )
        self.lbl_subtitle.pack(pady=(0, 20))

        # Ô nhập tài khoản (Login name)
        self.txt_username = ctk.CTkEntry(
            self.frame, 
            placeholder_text="Tên đăng nhập nhân viên",
            width=300, 
            height=40
        )
        self.txt_username.pack(pady=(5, 12))

        # Ô nhập mật khẩu
        self.txt_password = ctk.CTkEntry(
            self.frame, 
            placeholder_text="Mật khẩu", 
            show="*", 
            width=300, 
            height=40
        )
        self.txt_password.pack(pady=(0, 15))

        self.chk_show_password = ctk.CTkCheckBox(
            self.frame,
            text="Hiện mật khẩu",
            width=300,
            font=ctk.CTkFont(size=11),
            command=self._toggle_password,
        )
        self.chk_show_password.pack(pady=(0, 12))

        # Nút đăng nhập
        self.btn_login = ctk.CTkButton(
            self.frame, 
            text="Đăng Nhập", 
            width=300, 
            height=40, 
            font=ctk.CTkFont(weight="bold"),
            command=self.handle_login
        )
        self.btn_login.pack(pady=(5, 15))

        # Phím tắt Enter để đăng nhập
        self.bind("<Return>", lambda event: self.handle_login())

        # Sẵn sàng nhập tên tài khoản khi cửa sổ mở.
        self.txt_username.focus_set()

    def _toggle_password(self):
        self.password_visible = not self.password_visible
        self.txt_password.configure(show="" if self.password_visible else "*")

    def center_window(self):
        self.update_idletasks()
        width = 420
        height = 400
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def handle_login(self):
        if self._auth_in_progress:
            return

        username = self.txt_username.get().strip()
        password = self.txt_password.get()

        if not username or not password:
            messagebox.showwarning("Thông báo", "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!")
            return

        self.btn_login.configure(state="disabled", text="Đang xác thực...")
        self._auth_in_progress = True
        self._auth_result = None
        threading.Thread(
            target=self._authenticate,
            args=(username, password),
            daemon=True,
        ).start()
        self.after(50, self._poll_authentication)

    def _authenticate(self, username: str, password: str) -> None:
        """Run the blocking database connection away from Tk's UI thread."""
        try:
            user = dang_nhap_he_thong(username, password)
            self._auth_result = ("success", user)
        except ValueError as val_err:
            self._auth_result = ("invalid", str(val_err))
        except Exception as err:
            self._auth_result = ("error", str(err))

    def _poll_authentication(self) -> None:
        """Handle a completed authentication attempt on Tk's UI thread."""
        if self._auth_result is None:
            self.after(50, self._poll_authentication)
            return

        status, result = self._auth_result
        self._auth_result = None
        self._auth_in_progress = False

        if status == "success" and result:
            self.logged_in_user = result
            if self.on_login_success:
                self.on_login_success(result)
            # Ẩn cửa sổ đăng nhập ngay lập tức và thoát mainloop sạch sẽ
            self.withdraw()
            self.quit()
            return

        if status == "invalid":
            messagebox.showerror("Thất bại", result)
            self.txt_password.delete(0, "end")
            self.txt_password.focus_set()
        else:
            messagebox.showerror("Lỗi CSDL", result)

        self.btn_login.configure(state="normal", text="Đăng Nhập")


# Bí danh tương thích
LoginScreen = LoginForm
