"""Main navigation dashboard with role-based access control (RBAC)."""

import customtkinter as ctk
from typing import Dict, Any, Optional, Callable

from backup_and_restore.backup_screen import BackupScreen
from book_management.book_screen import BookScreen
from borrowing_and_returns.borrowing_screen import BorrowingScreen
from reader_management.reader_screen import ReaderScreen
from reports.report_screen import ReportScreen
from database import CURRENT_SESSION


class Dashboard(ctk.CTkFrame):
    """Bảng điều khiển trung tâm (Dashboard) điều hướng các module nghiệp vụ."""

    def __init__(self, master, on_logout: Optional[Callable[[], None]] = None) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_logout = on_logout
        self.user_info: Dict[str, Any] = CURRENT_SESSION.get("user_info") or {}

        # 1. Sidebar điều hướng bên trái
        navigation = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=("#F3F4F6", "#1E2229"))
        navigation.pack(side="left", fill="y", padx=0, pady=0)
        navigation.pack_propagate(False)

        # 2. Vùng hiển thị màn hình chức năng bên phải
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(side="right", fill="both", expand=True, padx=(10, 15), pady=10)

        # 3. Logo & Tiêu đề ứng dụng
        header_box = ctk.CTkFrame(navigation, fg_color="transparent")
        header_box.pack(fill="x", padx=15, pady=(25, 15))

        ctk.CTkLabel(
            header_box,
            text="QL THƯ VIỆN",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=("#1F2937", "#60A5FA")
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_box,
            text="Hệ Thống Quản Trị CSDL",
            font=ctk.CTkFont(size=11),
            text_color="gray60"
        ).pack(anchor="w")

        # 4. Huy hiệu người dùng (User Profile Badge)
        user_card = ctk.CTkFrame(navigation, corner_radius=10, fg_color=("#E5E7EB", "#2A2F3D"))
        user_card.pack(fill="x", padx=12, pady=(0, 20))

        hoten = self.user_info.get("HoTen") or self.user_info.get("LoginName") or "Người dùng"
        vaitro = self.user_info.get("VaiTro") or "Quản trị"
        role_key = (self.user_info.get("RoleName") or "QUANLY").upper()

        ctk.CTkLabel(
            user_card,
            text=hoten,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

        role_badge = ctk.CTkLabel(
            user_card,
            text=f"• {vaitro}",
            font=ctk.CTkFont(size=11),
            text_color="#10B981" if "QUANLY" in role_key else "#3B82F6",
            anchor="w"
        )
        role_badge.pack(fill="x", padx=10, pady=(0, 8))

        # 5. Danh sách các module theo phân quyền (RBAC)
        self.nav_buttons: Dict[str, ctk.CTkButton] = {}

        all_modules = [
            ("📚 Quản Lý Sách", BookScreen, ["QUANLY", "THUTHU", "DOCGIA"]),
            ("👥 Quản Lý Độc Giả", ReaderScreen, ["QUANLY", "THUTHU"]),
            ("🔄 Mượn & Trả Sách", BorrowingScreen, ["QUANLY", "THUTHU"]),
            ("📊 Báo Cáo Thống Kê", ReportScreen, ["QUANLY", "THUTHU"]),
            ("💾 Sao Lưu & Phục Hồi", BackupScreen, ["QUANLY"])
        ]

        allowed_modules = []
        for label, screen_class, roles in all_modules:
            if any(r in role_key for r in roles) or "SA" in role_key or "ADMIN" in role_key:
                allowed_modules.append((label, screen_class))

        for label, screen_class in allowed_modules:
            btn = ctk.CTkButton(
                navigation,
                text=label,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
                height=42,
                fg_color="transparent",
                text_color=("#1F2937", "#E5E7EB"),
                hover_color=("#E5E7EB", "#374151"),
                command=lambda sc=screen_class, lbl=label: self._on_module_click(sc, lbl)
            )
            btn.pack(fill="x", padx=12, pady=4)
            self.nav_buttons[label] = btn

        # Spacer
        ctk.CTkFrame(navigation, fg_color="transparent").pack(fill="both", expand=True)

        # 6. Nút Đăng xuất ở cuối sidebar
        if self._on_logout:
            btn_logout = ctk.CTkButton(
                navigation,
                text="🚪 Đăng Xuất",
                font=ctk.CTkFont(size=12, weight="bold"),
                height=36,
                fg_color=("#FEE2E2", "#450A0A"),
                text_color=("#DC2626", "#FCA5A5"),
                hover_color=("#FECACA", "#7F1D1D"),
                command=self._on_logout
            )
            btn_logout.pack(fill="x", padx=12, pady=(10, 16))

        # Khởi tạo màn hình mặc định ban đầu
        default_screen = allowed_modules[0][1] if allowed_modules else BookScreen
        default_label = allowed_modules[0][0] if allowed_modules else "📚 Quản Lý Sách"
        self._on_module_click(default_screen, default_label)

    def _on_module_click(self, screen_class, label: str) -> None:
        # Cập nhật style nút đang chọn
        for l, b in self.nav_buttons.items():
            if l == label:
                b.configure(fg_color=("#2563EB", "#1D4ED8"), text_color="#FFFFFF")
            else:
                b.configure(fg_color="transparent", text_color=("#1F2937", "#E5E7EB"))

        self.show_screen(screen_class)

    def show_screen(self, screen_class) -> None:
        """Chuyển đổi giao diện vùng nội dung chính."""
        for widget in self._content.winfo_children():
            widget.destroy()

        try:
            screen = screen_class(self._content, current_user=self.user_info)
        except TypeError:
            screen = screen_class(self._content)

        screen.pack(fill="both", expand=True)
