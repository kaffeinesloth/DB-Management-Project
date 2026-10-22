"""Login screen with authentication handling and quick-account testing."""

import customtkinter as ctk
from typing import Callable, Optional
from login.login_actions import authenticate


class LoginScreen(ctk.CTkFrame):
    """Màn hình Đăng nhập ứng dụng quản lý thư viện."""

    def __init__(self, master, on_login: Callable[[str, str], None]) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_login_callback = on_login

        self._build_ui()

    def _build_ui(self) -> None:
        card = ctk.CTkFrame(self, width=440, height=520, corner_radius=16, fg_color=("#F3F4F6", "#1E2229"))
        card.place(relx=0.5, rely=0.5, anchor="center")

        # Header
        ctk.CTkLabel(
            card,
            text="HỆ THỐNG QUẢN LÝ THƯ VIỆN",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=("#1F2937", "#60A5FA")
        ).pack(padx=20, pady=(35, 6))

        ctk.CTkLabel(
            card,
            text="Đăng nhập bằng tài khoản SQL Server",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray70")
        ).pack(padx=20, pady=(0, 20))

        # Username entry
        ctk.CTkLabel(card, text="Tên đăng nhập:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=45, pady=(0, 4))
        self.username_entry = ctk.CTkEntry(
            card,
            placeholder_text="Nhập tài khoản (vd: library_app, sa, admin)...",
            width=350,
            height=40
        )
        self.username_entry.pack(padx=45, pady=(0, 14))

        # Password entry
        ctk.CTkLabel(card, text="Mật khẩu:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=45, pady=(0, 4))
        self.password_entry = ctk.CTkEntry(
            card,
            placeholder_text="Nhập mật khẩu...",
            show="*",
            width=350,
            height=40
        )
        self.password_entry.pack(padx=45, pady=(0, 10))
        self.password_entry.bind("<Return>", lambda e: self._handle_submit())

        # Error / Status message
        self.message_label = ctk.CTkLabel(
            card,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#EF4444"
        )
        self.message_label.pack(pady=4)

        # Login button
        self.btn_login = ctk.CTkButton(
            card,
            text="ĐĂNG NHẬP",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            width=350,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            command=self._handle_submit
        )
        self.btn_login.pack(padx=45, pady=(8, 20))

        # Quick account presets for development testing
        preset_frame = ctk.CTkFrame(card, fg_color="transparent")
        preset_frame.pack(fill="x", padx=40, pady=(0, 20))

        ctk.CTkLabel(preset_frame, text="Tài khoản thử nghiệm nhanh:", font=ctk.CTkFont(size=11), text_color="gray60").pack(pady=(0, 6))
        
        btn_box = ctk.CTkFrame(preset_frame, fg_color="transparent")
        btn_box.pack()

        presets = [
            ("Docker App", "library_app", "LibraryApp_2026!"),
            ("Docker SA", "sa", "LibraryAdmin_2026!"),
            ("Admin (123456)", "admin", "123456"),
            ("Thủ thư", "nv_mai", "123456")
        ]

        for title, u, p in presets:
            ctk.CTkButton(
                btn_box,
                text=title,
                width=76,
                height=26,
                font=ctk.CTkFont(size=10),
                fg_color=("#E5E7EB", "#374151"),
                text_color=("#111827", "#F9FAFB"),
                hover_color=("#D1D5DB", "#4B5563"),
                command=lambda user=u, pwd=p: self._fill_preset(user, pwd)
            ).pack(side="left", padx=3)

        # Default fill to Docker App for convenient testing
        self._fill_preset("library_app", "LibraryApp_2026!")

    def _fill_preset(self, u: str, p: str) -> None:
        self.username_entry.delete(0, "end")
        self.username_entry.insert(0, u)
        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, p)
        self.show_message("")

    def _handle_submit(self) -> None:
        user = self.username_entry.get().strip()
        pwd = self.password_entry.get().strip()

        if not user or not pwd:
            self.show_message("Vui lòng điền đầy đủ tài khoản và mật khẩu!")
            return

        self.btn_login.configure(state="disabled", text="Đang xác thực...")
        self.update_idletasks()

        try:
            user_info = authenticate(user, pwd)
            self.show_message("")
            if self._on_login_callback:
                self._on_login_callback(user, pwd)
        except Exception as err:
            self.show_message(str(err))
        finally:
            self.btn_login.configure(state="normal", text="ĐĂNG NHẬP")

    def show_message(self, message: str) -> None:
        self.message_label.configure(text=message)
