"""Main navigation dashboard inheriting 100% of feature/qltv:ui/main_dashboard.py layout and RBAC."""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from typing import Dict, Any, Optional

from book_management.book_screen import BookScreen
from reader_management.reader_screen import ReaderScreen
from borrowing_and_returns.borrowing_screen import BorrowingScreen
from reports.report_screen import ReportScreen
from backup_and_restore.backup_screen import BackupScreen
from account_management.account_screen import AccountScreen
from catalog_search.catalog_screen import CatalogSearchScreen
from database import CURRENT_SESSION, clear_session


VALID_DASHBOARD_ROLES = {"DOCGIA", "THUTHU", "QUANLY"}


def require_dashboard_role(current_user: Dict[str, Any]) -> str:
    """Return an exact authorized role or reject the session."""
    role_name = str(current_user.get("RoleName") or "").strip().upper()
    if role_name not in VALID_DASHBOARD_ROLES:
        raise ValueError("Tài khoản không có nhóm quyền hợp lệ.")
    return role_name


class MainDashboard(ctk.CTk):
    """
    Cửa sổ chính Hệ Thống Quản Lý Thư Viện:
    - Kế thừa trọn vẹn 100% giao diện, phân quyền và trải nghiệm từ feature/qltv.
    - Thanh điều hướng (Sidebar) tích hợp định danh nhân viên và nhóm quyền (RBAC).
    - Phân quyền động:
        + Thủ thư (THUTHU): Tab Sách, Độc giả, Mượn/Trả, Báo cáo thống kê.
        + Quản lý (QUANLY): Toàn quyền thêm mới/thanh lý sách và Sao lưu & Phục hồi CSDL.
        + Độc giả (DOCGIA): Chỉ được tra cứu danh mục sách.
    """

    def __init__(self, current_user: Optional[Dict[str, Any]] = None, on_logout=None):
        resolved_user = current_user or CURRENT_SESSION.get("user_info") or {}
        require_dashboard_role(resolved_user)  # reject unknown roles before any window opens
        super().__init__()
        self.current_user = resolved_user  # self.role_name (property) reads the validated role
        self.on_logout = on_logout

        # Thiết lập cửa sổ
        hoten = self.current_user.get("HoTen", "Nhân viên")
        vaitro = self.current_user.get("VaiTro", "Thủ thư")
        self.title(f"Hệ Thống Quản Lý Thư Viện (QLTV) - {hoten} [{vaitro}]")
        # Căn giữa màn hình
        self.center_window()

        # Layout chính: Cột 0 (Sidebar điều hướng), Cột 1 (Khu vực nội dung Tab),
        # Hàng 1: thanh trạng thái (StatusStrip) trải hết chiều ngang.
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.create_sidebar()
        self.create_content_area()
        self.create_status_bar()

        # Độc giả vào thẳng trang tra cứu; nhân viên vào quản lý sách.
        self.select_tab("tracuu" if self.role_name == "DOCGIA" else "sach")

        # Không cho đóng cửa sổ khi đang BACKUP / RESTORE
        self.protocol("WM_DELETE_WINDOW", self.handle_close)

    def _maintenance_running(self) -> bool:
        """True nếu một màn hình đang chạy BACKUP / VERIFY / RESTORE."""
        busy = any(getattr(view, "is_busy", False) for view in self.views.values())
        if busy:
            messagebox.showwarning(
                "Đang sao lưu / phục hồi",
                "Hệ thống đang sao lưu hoặc phục hồi CSDL.\n\n"
                "Vui lòng chờ thao tác hoàn tất rồi mới đóng ứng dụng hoặc đăng xuất, "
                "nếu không CSDL có thể bị kẹt ở trạng thái RESTORING.",
            )
        return busy

    def handle_close(self):
        if self._maintenance_running():
            return
        self.destroy()

    def center_window(self):
        """Fit the window inside the usable screen so the bottom StatusStrip is never hidden.

        On a 1366x768 laptop, 740px + title bar + taskbar exceeds the screen and the
        taskbar would cover the status bar.
        """
        self.update_idletasks()
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        reserved = 40 + 32 + 8          # taskbar + title bar + margin
        width = min(1260, screen_w - 20)
        height = min(740, screen_h - reserved)
        self.minsize(min(1100, width), min(620, height))
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - reserved - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(9, weight=1)

        # Logo / Tên hệ thống
        lbl_brand = ctk.CTkLabel(
            self.sidebar, 
            text="THƯ VIỆN QLTV", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        lbl_brand.grid(row=0, column=0, padx=20, pady=(25, 5))

        lbl_sub = ctk.CTkLabel(
            self.sidebar, 
            text="Hệ Thống Quản Trị CSDL", 
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        lbl_sub.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Khung thông tin nhân viên & Định danh hệ thống
        profile_frame = ctk.CTkFrame(self.sidebar, fg_color=("#E2E8F0", "#1F2937"), corner_radius=10)
        profile_frame.grid(row=2, column=0, padx=15, pady=(0, 18), sticky="ew")

        lbl_name = ctk.CTkLabel(
            profile_frame, 
            text=f"{self.current_user.get('HoTen', 'N/A')}", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl_name.pack(anchor="w", padx=12, pady=(10, 2))

        if self.role_name == "DOCGIA":
            identity_text = "Tài khoản tra cứu dùng chung"
        else:
            identity_text = f"Mã NV: {self.current_user.get('MANV', 'N/A')}"
        ctk.CTkLabel(
            profile_frame, text=identity_text, font=ctk.CTkFont(size=12),
            text_color="#9CA3AF",
        ).pack(anchor="w", padx=12, pady=(0, 2))

        lbl_login = ctk.CTkLabel(
            profile_frame, 
            text=f"Login: {self.current_user.get('LoginName', 'N/A')}", 
            font=ctk.CTkFont(size=11),
            text_color="#9CA3AF"
        )
        lbl_login.pack(anchor="w", padx=12, pady=(0, 2))

        role_name = self.role_name
        role_color = {"QUANLY": "#10B981", "THUTHU": "#60A5FA", "DOCGIA": "#F59E0B"}[role_name]
        lbl_role = ctk.CTkLabel(
            profile_frame,
            text=f"Quyền: {role_name}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=role_color
        )
        lbl_role.pack(anchor="w", padx=12, pady=(0, 10))

        # Các nút chuyển Tab điều hướng theo phân quyền
        self.nav_buttons = {}

        if role_name == "DOCGIA":
            tabs = [("tracuu", "Tra Cứu Sách")]
        elif role_name == "THUTHU":
            tabs = [
                ("sach", "Quản Lý Sách"),
                ("docgia", "Quản Lý Độc Giả"),
                ("muontra", "Mượn / Trả Sách"),
                ("thongke", "Báo Cáo Thống Kê")
            ]
        else:  # QUANLY
            tabs = [
                ("sach", "Quản Lý Sách"),
                ("docgia", "Quản Lý Độc Giả"),
                ("muontra", "Mượn / Trả Sách"),
                ("thongke", "Báo Cáo Thống Kê"),
                ("taikhoan", "Quản Lý Tài Khoản"),
                ("backup", "Sao Lưu & Phục Hồi")
            ]

        for idx, (tab_id, tab_title) in enumerate(tabs, start=3):
            btn = ctk.CTkButton(
                self.sidebar,
                text=tab_title,
                height=42,
                anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("#CBD5E1", "#374151"),
                command=lambda tid=tab_id: self.select_tab(tid)
            )
            btn.grid(row=idx, column=0, padx=15, pady=4, sticky="ew")
            self.nav_buttons[tab_id] = btn

        # The shared DOCGIA password is administered centrally, not by students.
        if role_name != "DOCGIA":
            btn_password = ctk.CTkButton(
                self.sidebar,
                text="Đổi Mật Khẩu",
                height=36,
                fg_color="#0E7490",
                hover_color="#155E75",
                font=ctk.CTkFont(size=13, weight="bold"),
                command=self.open_change_password
            )
            btn_password.grid(row=10, column=0, padx=15, pady=(10, 0), sticky="ew")

        # Nút Đăng Xuất ở góc dưới
        btn_logout = ctk.CTkButton(
            self.sidebar,
            text="Đăng Xuất",
            height=38,
            fg_color="#EF4444",
            hover_color="#DC2626",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.handle_logout
        )
        btn_logout.grid(row=11, column=0, padx=15, pady=(8, 20), sticky="ew")

    @property
    def role_name(self) -> str:
        """The exact role was validated before the dashboard was created."""
        return str(self.current_user.get("RoleName") or "").strip().upper()

    def create_status_bar(self):
        """StatusStrip ở đáy cửa sổ: Mã NV | Họ tên | Nhóm quyền | Login | CSDL."""
        bar = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color=("#CBD5E1", "#111827"))
        bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        role_label = {"QUANLY": "Quản lý", "THUTHU": "Thủ thư", "DOCGIA": "Độc giả"}[self.role_name]
        identity = (
            "Tài khoản dùng chung"
            if self.role_name == "DOCGIA"
            else f"Mã NV: {self.current_user.get('MANV', 'N/A')}"
        )
        items = (
            identity,
            f"Họ tên: {self.current_user.get('HoTen', 'N/A')}",
            f"Nhóm quyền: {self.role_name} ({role_label})",
            f"Đăng nhập: {self.current_user.get('LoginName', 'N/A')}",
            f"CSDL: {CURRENT_SESSION.get('active_db')} @ {CURRENT_SESSION.get('active_server')}",
        )
        self.status_labels = []
        for idx, text in enumerate(items):
            if idx:
                ctk.CTkLabel(bar, text="|", text_color="gray").pack(side="left", padx=2)
            label = ctk.CTkLabel(bar, text=text, font=ctk.CTkFont(size=12),
                                 text_color=("gray10", "gray85"))
            label.pack(side="left", padx=(12 if idx == 0 else 6, 6), pady=2)
            self.status_labels.append(label)

    def open_change_password(self):
        from account_management.account_screen import ChangePasswordDialog
        ChangePasswordDialog(self, self.current_user.get("LoginName", ""))

    def create_content_area(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        if self.role_name == "DOCGIA":
            self.views = {
                "tracuu": CatalogSearchScreen(self.main_container, self.current_user),
            }
        elif self.role_name == "THUTHU":
            self.views = {
                "sach": BookScreen(self.main_container, self.current_user),
                "docgia": ReaderScreen(self.main_container, self.current_user),
                "muontra": BorrowingScreen(self.main_container, self.current_user),
                "thongke": ReportScreen(self.main_container, self.current_user),
            }
        else:
            self.views = {
                "sach": BookScreen(self.main_container, self.current_user),
                "docgia": ReaderScreen(self.main_container, self.current_user),
                "muontra": BorrowingScreen(self.main_container, self.current_user),
                "thongke": ReportScreen(self.main_container, self.current_user),
                "taikhoan": AccountScreen(self.main_container, self.current_user),
                "backup": BackupScreen(self.main_container, self.current_user),
            }

    def select_tab(self, tab_id: str):
        for view in self.views.values():
            view.grid_forget()

        for tid, btn in self.nav_buttons.items():
            if tid == tab_id:
                btn.configure(fg_color=("#3B82F6", "#2563EB"), text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=("gray10", "gray90"))

        if tab_id in self.views:
            self.views[tab_id].grid(row=0, column=0, sticky="nsew")

    def handle_logout(self):
        if self._maintenance_running():
            return
        confirm = messagebox.askyesno("Đăng xuất", "Bạn có chắc chắn muốn đăng xuất khỏi hệ thống?")
        if confirm:
            clear_session()
            if self.on_logout:
                self.on_logout()
            self.withdraw()
            self.quit()


# Bí danh tương thích
Dashboard = MainDashboard
