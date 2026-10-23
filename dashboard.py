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
from database import CURRENT_SESSION


class MainDashboard(ctk.CTk):
    """
    Cửa sổ chính Hệ Thống Quản Lý Thư Viện:
    - Kế thừa trọn vẹn 100% giao diện, phân quyền và trải nghiệm từ feature/qltv.
    - Thanh điều hướng (Sidebar) tích hợp định danh nhân viên và nhóm quyền (RBAC).
    - Phân quyền động:
        + Độc giả (DOCGIA): Chỉ mở Tab Tra cứu sách.
        + Thủ thư (THUTHU): Tab Sách, Độc giả, Mượn/Trả, Báo cáo thống kê.
        + Quản lý (QUANLY): Toàn quyền thêm mới/thanh lý sách và Sao lưu & Phục hồi CSDL.
    """

    def __init__(self, current_user: Optional[Dict[str, Any]] = None, on_logout=None):
        super().__init__()
        self.current_user = current_user or CURRENT_SESSION.get("user_info") or {}
        self.on_logout = on_logout

        # Thiết lập cửa sổ
        hoten = self.current_user.get("HoTen", "Nhân viên")
        vaitro = self.current_user.get("VaiTro", "Thủ thư")
        self.title(f"Hệ Thống Quản Lý Thư Viện (QLTV) - {hoten} [{vaitro}]")
        self.geometry("1260x740")
        self.minsize(1100, 660)

        # Căn giữa màn hình
        self.center_window()

        # Layout chính: Cột 0 (Sidebar điều hướng), Cột 1 (Khu vực nội dung Tab)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.create_sidebar()
        self.create_content_area()

        # Mặc định mở Tab Sách
        self.select_tab("sach")

    def center_window(self):
        self.update_idletasks()
        width = 1260
        height = 740
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
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

        is_docgia = (self.current_user.get("RoleName") == "DOCGIA")

        if not is_docgia:
            lbl_manv = ctk.CTkLabel(
                profile_frame, 
                text=f"Mã NV: {self.current_user.get('MANV', 'N/A')}", 
                font=ctk.CTkFont(size=12),
                text_color="#9CA3AF"
            )
        else:
            lbl_manv = ctk.CTkLabel(
                profile_frame, 
                text="Đối tượng: Bạn đọc", 
                font=ctk.CTkFont(size=12),
                text_color="#9CA3AF"
            )
        lbl_manv.pack(anchor="w", padx=12, pady=(0, 2))

        lbl_login = ctk.CTkLabel(
            profile_frame, 
            text=f"Login: {self.current_user.get('LoginName', 'N/A')}", 
            font=ctk.CTkFont(size=11),
            text_color="#9CA3AF"
        )
        lbl_login.pack(anchor="w", padx=12, pady=(0, 2))

        role_name = (self.current_user.get('RoleName') or 'QUANLY').upper()
        role_color = "#10B981" if "QUANLY" in role_name else ("#A855F7" if is_docgia else "#60A5FA")
        lbl_role = ctk.CTkLabel(
            profile_frame, 
            text=f"Quyền: {self.current_user.get('RoleName', 'QUANLY')}", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=role_color
        )
        lbl_role.pack(anchor="w", padx=12, pady=(0, 10))

        # Các nút chuyển Tab điều hướng theo phân quyền
        self.nav_buttons = {}

        if is_docgia:
            tabs = [
                ("sach", "Tra Cứu Sách")
            ]
        elif "THUTHU" in role_name:
            tabs = [
                ("sach", "Quản Lý Sách"),
                ("docgia", "Quản Lý Độc Giả"),
                ("muontra", "Mượn / Trả Sách"),
                ("thongke", "Báo Cáo Thống Kê")
            ]
        else:  # QUANLY hoặc ADMIN
            tabs = [
                ("sach", "Quản Lý Sách"),
                ("docgia", "Quản Lý Độc Giả"),
                ("muontra", "Mượn / Trả Sách"),
                ("thongke", "Báo Cáo Thống Kê"),
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
        btn_logout.grid(row=10, column=0, padx=15, pady=(10, 20), sticky="ew")

    def create_content_area(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        is_docgia = (self.current_user.get("RoleName") == "DOCGIA")
        role_name = (self.current_user.get("RoleName") or "QUANLY").upper()

        if is_docgia:
            self.views = {
                "sach": BookScreen(self.main_container, self.current_user)
            }
        elif "THUTHU" in role_name:
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
        confirm = messagebox.askyesno("Đăng xuất", "Bạn có chắc chắn muốn đăng xuất khỏi hệ thống?")
        if confirm:
            if self.on_logout:
                self.on_logout()
            self.after(30, self._safe_destroy)

    def _safe_destroy(self):
        try:
            self.destroy()
        except Exception:
            pass


# Bí danh tương thích
Dashboard = MainDashboard
