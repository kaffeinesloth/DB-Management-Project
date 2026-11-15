"""Login screen inheriting 100% logic and design from feature/qltv."""

import customtkinter as ctk
import ctk_patch
from tkinter import messagebox
from typing import Optional, Callable
from database import dang_nhap_he_thong, SERVER_NAME, DATABASE_NAME


class LoginForm(ctk.CTk):
    """Cửa sổ Đăng Nhập Hệ Thống chuẩn giao diện feature/qltv."""

    def __init__(self, on_login_success: Optional[Callable[[dict], None]] = None):
        super().__init__()
        self.on_login_success = on_login_success

        self.title("Quản Lý Thư Viện - Đăng Nhập")
        self.geometry("420x560")
        self.resizable(False, False)
        self.logged_in_user = None
        self.password_visible = False

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
            text="Xác thực qua tài khoản SQL Server", 
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

        # Gợi ý tài khoản thử nghiệm
        self.lbl_hints = ctk.CTkLabel(
            self.frame,
            text="Tài khoản nhân viên (Mật khẩu: 123456):\n• Quản lý: admin\n• Thủ thư: nv_huong / nv_long / nv_nam\n• Độc giả được quản lý bằng thẻ, không đăng nhập",
            font=ctk.CTkFont(size=11),
            text_color="#9CA3AF",
            justify="left"
        )
        self.lbl_hints.pack(pady=(0, 10))

        # Phím tắt chọn nhanh
        btn_box = ctk.CTkFrame(self.frame, fg_color="transparent")
        btn_box.pack(pady=(0, 15))

        for title, u, p in [
            ("Admin", "admin", "123456"),
            ("Hương", "nv_huong", "123456"),
            ("Long", "nv_long", "123456"),
            ("Nam", "nv_nam", "123456"),
        ]:
            ctk.CTkButton(
                btn_box,
                text=title,
                width=65,
                height=26,
                font=ctk.CTkFont(size=11),
                fg_color=("#E5E7EB", "#374151"),
                text_color=("#111827", "#F9FAFB"),
                command=lambda user=u, pwd=p: self._fill_credentials(user, pwd)
            ).pack(side="left", padx=3)

        # Nút đăng nhập
        self.btn_login = ctk.CTkButton(
            self.frame, 
            text="Đăng Nhập", 
            width=300, 
            height=40, 
            font=ctk.CTkFont(weight="bold"),
            command=self.handle_login
        )
        self.btn_login.pack(pady=(0, 15))

        self.lbl_connection = ctk.CTkLabel(
            self.frame,
            text=f"CSDL: {SERVER_NAME} / {DATABASE_NAME}",
            font=ctk.CTkFont(size=10),
            text_color="#6B7280",
        )
        self.lbl_connection.pack(pady=(0, 5))

        # Phím tắt Enter để đăng nhập
        self.bind("<Return>", lambda event: self.handle_login())

        # Điền mặc định admin
        self._fill_credentials("admin", "123456")

    def _fill_credentials(self, u: str, p: str):
        self.txt_username.delete(0, "end")
        self.txt_username.insert(0, u)
        self.txt_password.delete(0, "end")
        self.txt_password.insert(0, p)

    def _toggle_password(self):
        self.password_visible = not self.password_visible
        self.txt_password.configure(show="" if self.password_visible else "*")

    def center_window(self):
        self.update_idletasks()
        width = 420
        height = 560
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def handle_login(self):
        username = self.txt_username.get().strip()
        password = self.txt_password.get()

        if not username or not password:
            messagebox.showwarning("Thông báo", "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!")
            return

        self.btn_login.configure(state="disabled", text="Đang xác thực...")
        self.update_idletasks()

        success = False
        try:
            user = dang_nhap_he_thong(username, password)
            if user:
                self.logged_in_user = user
                if self.on_login_success:
                    self.on_login_success(user)
                success = True
                # Ẩn cửa sổ đăng nhập ngay lập tức và thoát mainloop sạch sẽ
                self.withdraw()
                self.quit()
        except ValueError as val_err:
            messagebox.showerror("Thất bại", str(val_err))
            self.txt_password.delete(0, "end")
        except Exception as err:
            messagebox.showerror("Lỗi CSDL", str(err))
        finally:
            if not success:
                try:
                    self.btn_login.configure(state="normal", text="Đăng Nhập")
                except Exception:
                    pass


# Bí danh tương thích
LoginScreen = LoginForm
