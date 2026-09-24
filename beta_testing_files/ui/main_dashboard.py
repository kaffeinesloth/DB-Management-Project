import customtkinter as ctk
from typing import Dict, Any
from ui.tabs.tab_docgia import TabDocGia

class MainDashboard(ctk.CTk):
    """
    Cửa sổ Dashboard chính của Hệ thống Quản Lý Thư Viện.
    - Cung cấp thanh điều hướng Sidebar 4 Tab chức năng chính.
    - Hiển thị Profile nhân viên đang đăng nhập và quyền hạn.
    - Chuyển đổi linh hoạt giữa các module quản lý.
    """

    def __init__(self, current_user: Dict[str, Any], on_logout=None):
        super().__init__()
        self.current_user = current_user
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

        # Mặc định mở Tab Độc giả (hoặc Tab đầu tiên)
        self.select_tab("docgia")

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
        self.sidebar.grid_rowconfigure(7, weight=1)

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

        lbl_manv = ctk.CTkLabel(
            profile_frame, 
            text=f"Mã NV: {self.current_user.get('MANV', 'N/A')}", 
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

        lbl_role = ctk.CTkLabel(
            profile_frame, 
            text=f"Quyền: {self.current_user.get('RoleName', 'THUTHU')}", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#10B981" if self.current_user.get('RoleName') == "QUANLY" else "#60A5FA"
        )
        lbl_role.pack(anchor="w", padx=12, pady=(0, 10))

        # Các nút chuyển Tab điều hướng
        self.nav_buttons = {}

        tabs = [
            ("sach", "Quản Lý Sách"),
            ("docgia", "Quản Lý Độc Giả"),
            ("muontra", "Mượn / Trả Sách"),
            ("thongke", "Báo Cáo Thống Kê")
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
        btn_logout.grid(row=8, column=0, padx=15, pady=(10, 20), sticky="ew")

    def create_content_area(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # Khởi tạo các Views
        self.views = {}

        # Tab 1: Quản lý Độc giả (Hoàn chỉnh)
        self.views["docgia"] = TabDocGia(self.main_container, self.current_user)

        # Tab 2: Quản lý Sách (Placeholder)
        self.views["sach"] = self.create_placeholder_tab(
            "QUẢN LÝ ĐẦU SÁCH & CUỐN SÁCH", 
            "Module quản lý danh mục Đầu sách (ISBN), Cuốn sách vật lý (SACH),\nNgăn tủ, Thể loại, Tác giả và Tác giả_Sách.\n(Sẽ hoàn thiện ở Bước 2)"
        )

        # Tab 3: Mượn / Trả Sách (Placeholder)
        self.views["muontra"] = self.create_placeholder_tab(
            "QUẢN LÝ MƯỢN / TRẢ SÁCH", 
            "Module lập phiếu mượn sách, kiểm tra giới hạn 3 cuốn,\ntrả sách, tự động tính phạt quá hạn 500đ/ngày hoặc bồi thường mất sách.\n(Sẽ hoàn thiện ở Bước 3)"
        )

        # Tab 4: Báo Cáo Thống Kê (Placeholder)
        self.views["thongke"] = self.create_placeholder_tab(
            "BÁO CÁO & THỐNG KÊ", 
            "Module thống kê danh sách độc giả mượn quá hạn và tần suất sử dụng sách.\n(Sẽ hoàn thiện ở Bước 4)"
        )

    def create_placeholder_tab(self, title: str, desc: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.main_container, corner_radius=12)
        frame.grid_rowconfigure((0, 1, 2), weight=1)
        frame.grid_columnconfigure(0, weight=1)

        center_box = ctk.CTkFrame(frame, fg_color="transparent")
        center_box.grid(row=1, column=0)

        lbl_title = ctk.CTkLabel(center_box, text=title, font=ctk.CTkFont(size=20, weight="bold"))
        lbl_title.pack(pady=10)

        lbl_desc = ctk.CTkLabel(center_box, text=desc, font=ctk.CTkFont(size=14), text_color="gray", justify="center")
        lbl_desc.pack(pady=10)

        return frame

    def select_tab(self, tab_id: str):
        # Ẩn tất cả các view
        for view in self.views.values():
            view.grid_forget()

        # Đặt lại màu tất cả các nút nav
        for tid, btn in self.nav_buttons.items():
            if tid == tab_id:
                btn.configure(fg_color=("#3B82F6", "#2563EB"), text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=("gray10", "gray90"))

        # Hiển thị view được chọn
        if tab_id in self.views:
            self.views[tab_id].grid(row=0, column=0, sticky="nsew")

    def handle_logout(self):
        """Xác nhận và đăng xuất trở về màn hình đăng nhập."""
        from tkinter import messagebox
        confirm = messagebox.askyesno("Đăng xuất", "Bạn có chắc chắn muốn đăng xuất khỏi hệ thống?")
        if confirm:
            self.destroy()
            if self.on_logout:
                self.on_logout()

if __name__ == "__main__":
    # Chạy thử trực tiếp với user mẫu
    mock_user = {
        "MANV": 1,
        "HoTen": "Nguyễn Trọng Hoàng",
        "VaiTro": "Quản lý",
        "Email": "admin@qltv.com"
    }
    dashboard = MainDashboard(mock_user)
    dashboard.mainloop()
