import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from typing import Dict, Any
from dao.thongke_dao import ThongKeDAO

class TabThongKe(ctk.CTkFrame):
    """
    Giao diện Báo Cáo Thống Kê:
    - 4 Thẻ chỉ số tổng quan (KPI Cards) đo lường tình trạng thư viện.
    - Chuyển đổi linh hoạt giữa 2 Báo cáo chuyên sâu:
      1. Danh sách độc giả mượn sách quá hạn và tiền phạt ước tính.
      2. Tần suất mượn sách theo từng đầu sách (xếp hạng nhiều nhất / ít nhất).
    - Hỗ trợ làm mới dữ liệu tức thì.
    """

    def __init__(self, master, current_user: Dict[str, Any]):
        super().__init__(master, fg_color="transparent")
        self.current_user = current_user

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Hàng trên: 4 Thẻ chỉ số KPI
        self.create_kpi_cards()

        # 2. Hàng dưới: Bảng báo cáo chuyên sâu
        self.create_report_section()

    def create_kpi_cards(self):
        cards_container = ctk.CTkFrame(self, fg_color="transparent")
        cards_container.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        for i in range(4):
            cards_container.grid_columnconfigure(i, weight=1)

        # Card 1: Tổng Đầu Sách
        self.card1 = self.create_card(cards_container, 0, "Tổng Đầu Sách (ISBN)", "0", "#3B82F6")

        # Card 2: Cuốn Sách / Đang Mượn
        self.card2 = self.create_card(cards_container, 1, "Cuốn Sách (Kho / Mượn)", "0 / 0", "#10B981")

        # Card 3: Độc Giả Hoạt Động
        self.card3 = self.create_card(cards_container, 2, "Độc Giả Đang Hoạt Động", "0 thẻ", "#8B5CF6")

        # Card 4: Sách Quá Hạn & Tiền Phạt
        self.card4 = self.create_card(cards_container, 3, "Sách Quá Hạn (Phạt dự kiến)", "0 cuốn (0 đ)", "#EF4444")

    def create_card(self, parent, col, title, initial_value, border_color):
        card = ctk.CTkFrame(
            parent, 
            corner_radius=10, 
            border_width=2, 
            border_color=border_color,
            fg_color=("#F3F4F6", "#1F2937")
        )
        card.grid(row=0, column=col, padx=6, pady=5, sticky="ew")

        lbl_t = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12), text_color="#9CA3AF")
        lbl_t.pack(pady=(12, 4), padx=12, anchor="w")

        lbl_v = ctk.CTkLabel(card, text=initial_value, font=ctk.CTkFont(size=18, weight="bold"))
        lbl_v.pack(pady=(0, 12), padx=12, anchor="w")

        return lbl_v

    def create_report_section(self):
        container = ctk.CTkFrame(self, corner_radius=12)
        container.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        container.grid_rowconfigure(2, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Header điều khiển
        header_frame = ctk.CTkFrame(container, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")

        lbl_title = ctk.CTkLabel(
            header_frame, 
            text="CHI TIẾT BÁO CÁO THỐNG KÊ", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_title.pack(side="left")

        btn_refresh = ctk.CTkButton(
            header_frame, 
            text="Làm mới báo cáo", 
            width=120, 
            height=36,
            fg_color="#4B5563",
            hover_color="#374151",
            command=self.load_data
        )
        btn_refresh.pack(side="right")

        # Nút chuyển đổi 2 báo cáo
        control_frame = ctk.CTkFrame(container, fg_color="transparent")
        control_frame.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="ew")

        self.seg_report = ctk.CTkSegmentedButton(
            control_frame,
            values=["Độc Giả Mượn Quá Hạn", "Tần Suất Sử Dụng Đầu Sách"],
            command=self.switch_report,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=36
        )
        self.seg_report.set("Độc Giả Mượn Quá Hạn")
        self.seg_report.pack(side="left")

        self.lbl_report_summary = ctk.CTkLabel(
            control_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#9CA3AF"
        )
        self.lbl_report_summary.pack(side="right")

        # Container cho bảng Treeview
        tree_container = ctk.CTkFrame(container, fg_color="#1E2229", corner_radius=8)
        tree_container.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="nsew")
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.tree = ttk.Treeview(tree_container, show="headings", selectmode="browse")

        self.tree.tag_configure("oddrow", background="#1E2229", foreground="#F3F4F6")
        self.tree.tag_configure("evenrow", background="#242830", foreground="#F3F4F6")
        self.tree.tag_configure("overdue_alert", background="#382226", foreground="#F87171") # Đỏ cảnh báo

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

    def load_data(self):
        # 1. Cập nhật các thẻ KPI
        try:
            overview = ThongKeDAO.get_tong_quan()
            self.card1.configure(text=f"{overview['TongDauSach']} đầu sách")
            self.card2.configure(text=f"{overview['TongCuonSach']} cuốn ({overview['DangMuon']} đang mượn)")
            self.card3.configure(text=f"{overview['DocGiaHoatDong']} thẻ")
            self.card4.configure(text=f"{overview['SoQuaHan']} cuốn ({overview['TienPhatUocTinh']:,} đ)")
        except Exception as ex:
            print("Lỗi tải KPI:", ex)

        # 2. Hiển thị báo cáo đang chọn
        self.switch_report(self.seg_report.get())

    def switch_report(self, report_name):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if report_name == "Độc Giả Mượn Quá Hạn":
            self.display_report_qua_han()
        else:
            self.display_report_tan_suat()

    def display_report_qua_han(self):
        columns = (
            "MADG", "HoTenDG", "DIENTHOAI", "MASACH", "TENSACH",
            "HinhThuc", "NgayMuonStr", "SoNgayTre", "TienPhatUocTinh"
        )
        self.tree.configure(columns=columns)

        col_configs = {
            "MADG": ("Mã ĐG", 60, "center"),
            "HoTenDG": ("Họ Tên Độc Giả", 150, "w"),
            "DIENTHOAI": ("Điện Thoại", 100, "center"),
            "MASACH": ("Mã Sách", 80, "center"),
            "TENSACH": ("Tên Đầu Sách", 200, "w"),
            "HinhThuc": ("Hình Thức", 90, "center"),
            "NgayMuonStr": ("Ngày Mượn", 90, "center"),
            "SoNgayTre": ("Trễ Hạn (ngày)", 100, "center"),
            "TienPhatUocTinh": ("Tiền Phạt Dự Kiến (VNĐ)", 140, "e")
        }

        for col, (heading, width, align) in col_configs.items():
            self.tree.heading(col, text=heading, anchor=align)
            self.tree.column(col, width=width, minwidth=50, anchor=align)

        try:
            records = ThongKeDAO.get_doc_gia_qua_han()
            for idx, r in enumerate(records):
                phat_str = f"{r.get('TienPhatUocTinh', 0):,}"
                tag = "overdue_alert" if r.get("SoNgayTre", 0) > 0 else ("oddrow" if idx % 2 != 0 else "evenrow")

                self.tree.insert("", "end", values=(
                    r.get("MADG"),
                    r.get("HoTenDG"),
                    r.get("DIENTHOAI") or "",
                    r.get("MASACH"),
                    r.get("TENSACH"),
                    r.get("HinhThuc"),
                    r.get("NgayMuonStr"),
                    f"{r.get('SoNgayTre', 0)} ngày",
                    phat_str
                ), tags=(tag,))

            self.lbl_report_summary.configure(text=f"Có {len(records)} lượt mượn sách bị trễ hạn")
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", f"Không thể tải báo cáo quá hạn:\n{ex}")

    def display_report_tan_suat(self):
        columns = (
            "ISBN", "TENSACH", "TheLoai", "GiaBia",
            "TongSoCuon", "SoCuonSanCo", "SoLuotMuon"
        )
        self.tree.configure(columns=columns)

        col_configs = {
            "ISBN": ("Mã ISBN", 95, "center"),
            "TENSACH": ("Tên Đầu Sách", 230, "w"),
            "TheLoai": ("Thể Loại", 130, "w"),
            "GiaBia": ("Giá Bìa (VNĐ)", 100, "e"),
            "TongSoCuon": ("Tổng Số Cuốn", 100, "center"),
            "SoCuonSanCo": ("Sẵn Có Trong Kho", 110, "center"),
            "SoLuotMuon": ("Số Lượt Mượn", 110, "center")
        }

        for col, (heading, width, align) in col_configs.items():
            self.tree.heading(col, text=heading, anchor=align)
            self.tree.column(col, width=width, minwidth=50, anchor=align)

        try:
            records = ThongKeDAO.get_tan_suat_muon_sach()
            for idx, r in enumerate(records):
                gia_str = f"{r.get('GiaBia', 0):,}"
                tag = "oddrow" if idx % 2 != 0 else "evenrow"

                self.tree.insert("", "end", values=(
                    r.get("ISBN"),
                    r.get("TENSACH"),
                    r.get("TheLoai"),
                    gia_str,
                    r.get("TongSoCuon"),
                    r.get("SoCuonSanCo"),
                    r.get("SoLuotMuon")
                ), tags=(tag,))

            self.lbl_report_summary.configure(text=f"Thống kê trên {len(records)} đầu sách trong thư viện")
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", f"Không thể tải báo cáo tần suất:\n{ex}")
