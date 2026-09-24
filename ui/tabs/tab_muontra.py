import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import ui.ctk_patch
from typing import Dict, Any, List
from dao.muontra_dao import MuonTraDAO
from dao.docgia_dao import DocGiaDAO
from dao.sach_dao import SachDAO

class TabMuonTra(ctk.CTkFrame):
    """
    Giao diện Quản Lý Mượn / Trả Sách và Xử Phạt:
    - Hiển thị danh sách các lượt mượn đang diễn ra (chưa trả).
    - Cảnh báo trực quan các phiếu mượn trễ hạn (>30 ngày nếu mang về, >0 ngày nếu tại chỗ).
    - Thực hiện trả sách: Tính tiền phạt trễ hạn (500đ/ngày), bồi thường mất sách (100% giá bìa), phạt sách hỏng (50% giá bìa).
    - Lập phiếu mượn mới: Kiểm tra thẻ độc giả, kiểm tra giới hạn mượn tối đa 3 cuốn, kiểm tra tình trạng sách sẵn sàng.
    """

    def __init__(self, master, current_user: Dict[str, Any]):
        super().__init__(master, fg_color="transparent")
        self.current_user = current_user

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        self.create_left_panel()
        self.create_right_panel()

    def create_left_panel(self):
        left_frame = ctk.CTkFrame(self, corner_radius=12)
        left_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        left_frame.grid_rowconfigure(2, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        # 1. Header & Bộ đếm
        header_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")

        lbl_title = ctk.CTkLabel(
            header_frame, 
            text="SÁCH ĐANG ĐƯỢC MƯỢN (CHƯA TRẢ)", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_title.pack(side="left")

        self.lbl_count = ctk.CTkLabel(
            header_frame, 
            text="Tổng: 0 cuốn đang mượn", 
            font=ctk.CTkFont(size=13),
            text_color="#9CA3AF"
        )
        self.lbl_count.pack(side="right")

        # 2. Thanh tìm kiếm
        search_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        search_frame.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)

        self.txt_search = ctk.CTkEntry(
            search_frame, 
            placeholder_text="Tìm theo Tên độc giả, Mã ĐG, SĐT, Mã sách hoặc Tên sách...",
            height=36
        )
        self.txt_search.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.txt_search.bind("<Return>", lambda e: self.handle_search())

        btn_search = ctk.CTkButton(
            search_frame, 
            text="Tìm kiếm", 
            width=90, 
            height=36,
            command=self.handle_search
        )
        btn_search.grid(row=0, column=1, padx=(0, 6))

        btn_refresh = ctk.CTkButton(
            search_frame, 
            text="Làm mới", 
            width=80, 
            height=36,
            fg_color="#4B5563",
            hover_color="#374151",
            command=self.load_data
        )
        btn_refresh.grid(row=0, column=2)

        # 3. Bảng Treeview
        tree_container = ctk.CTkFrame(left_frame, fg_color="#1E2229", corner_radius=8)
        tree_container.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="nsew")
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        self.style = ttk.Style()
        self.style.theme_use("clam")

        columns = (
            "MAPHIEU", "MADG", "HoTenDG", "DIENTHOAI", "MASACH", "TENSACH",
            "HinhThucStr", "NgayMuonStr", "SoNgayDaMuon", "SoNgayTre"
        )

        self.tree = ttk.Treeview(
            tree_container, 
            columns=columns, 
            show="headings", 
            selectmode="browse"
        )

        col_configs = {
            "MAPHIEU": ("Mã Phiếu", 65, "center"),
            "MADG": ("Mã ĐG", 55, "center"),
            "HoTenDG": ("Độc Giả", 130, "w"),
            "DIENTHOAI": ("Điện Thoại", 90, "center"),
            "MASACH": ("Mã Sách", 75, "center"),
            "TENSACH": ("Tên Sách", 180, "w"),
            "HinhThucStr": ("Hình Thức", 80, "center"),
            "NgayMuonStr": ("Ngày Mượn", 85, "center"),
            "SoNgayDaMuon": ("Đã Mượn (ngày)", 95, "center"),
            "SoNgayTre": ("Trễ Hạn (ngày)", 90, "center")
        }

        for col, (heading, width, align) in col_configs.items():
            self.tree.heading(col, text=heading, anchor=align)
            self.tree.column(col, width=width, minwidth=40, anchor=align)

        self.tree.tag_configure("oddrow", background="#1E2229", foreground="#F3F4F6")
        self.tree.tag_configure("evenrow", background="#242830", foreground="#F3F4F6")
        self.tree.tag_configure("overdue", background="#383020", foreground="#FBBF24") # Cảnh báo quá hạn (vàng)

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # 4. Thanh thao tác Trả sách dưới bảng
        action_bar = ctk.CTkFrame(left_frame, fg_color="transparent")
        action_bar.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="ew")

        btn_return_good = ctk.CTkButton(
            action_bar,
            text="Trả Sách (Nguyên vẹn)",
            fg_color="#059669",
            hover_color="#047857",
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.handle_return_book(tinh_trang_tra=1, bi_mat=False)
        )
        btn_return_good.pack(side="left", padx=(0, 10))

        btn_return_damaged = ctk.CTkButton(
            action_bar,
            text="Trả Sách (Bị hư hỏng)",
            fg_color="#D97706",
            hover_color="#B45309",
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.handle_return_book(tinh_trang_tra=0, bi_mat=False)
        )
        btn_return_damaged.pack(side="left", padx=(0, 10))

        btn_return_lost = ctk.CTkButton(
            action_bar,
            text="Báo Mất Sách (Đền 100%)",
            fg_color="#DC2626",
            hover_color="#B91C1C",
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.handle_return_book(tinh_trang_tra=0, bi_mat=True)
        )
        btn_return_lost.pack(side="left")

    def create_right_panel(self):
        right_frame = ctk.CTkScrollableFrame(self, width=340, corner_radius=12)
        right_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")

        lbl_panel_title = ctk.CTkLabel(
            right_frame, 
            text="LẬP PHIẾU MƯỢN SÁCH", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        lbl_panel_title.pack(pady=(15, 12), anchor="w")

        # 1. Mã độc giả
        lbl_dg = ctk.CTkLabel(right_frame, text="Mã độc giả (MADG) *", font=ctk.CTkFont(size=12))
        lbl_dg.pack(anchor="w")

        dg_row = ctk.CTkFrame(right_frame, fg_color="transparent")
        dg_row.pack(fill="x", pady=(2, 6))
        dg_row.grid_columnconfigure(0, weight=1)

        self.txt_madg = ctk.CTkEntry(dg_row, placeholder_text="Ví dụ: 1", height=35)
        self.txt_madg.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        btn_check_dg = ctk.CTkButton(
            dg_row, 
            text="Kiểm Tra", 
            width=80, 
            height=35,
            command=self.handle_check_docgia
        )
        btn_check_dg.grid(row=0, column=1)

        self.lbl_dg_info = ctk.CTkLabel(
            right_frame, 
            text="", 
            font=ctk.CTkFont(size=11), 
            text_color="#9CA3AF",
            justify="left",
            wraplength=310
        )
        self.lbl_dg_info.pack(anchor="w", pady=(0, 10))

        # 2. Hình thức mượn
        lbl_ht = ctk.CTkLabel(right_frame, text="Hình thức mượn *", font=ctk.CTkFont(size=12))
        lbl_ht.pack(anchor="w")

        self.cb_hinhthuc = ctk.CTkComboBox(
            right_frame, 
            values=["Mang về (Hạn 30 ngày)", "Tại chỗ (Trả trong ngày)"],
            height=35
        )
        self.cb_hinhthuc.set("Mang về (Hạn 30 ngày)")
        self.cb_hinhthuc.pack(fill="x", pady=(2, 10))

        # 3. Danh sách mã sách mượn (Tối đa 3 cuốn)
        lbl_sach_title = ctk.CTkLabel(
            right_frame, 
            text="Danh sách mã sách mượn (Tối đa 3 cuốn):", 
            font=ctk.CTkFont(size=12, weight="bold")
        )
        lbl_sach_title.pack(anchor="w", pady=(5, 4))

        lbl_s1 = ctk.CTkLabel(right_frame, text="Cuốn sách 1 *", font=ctk.CTkFont(size=11))
        lbl_s1.pack(anchor="w")
        self.txt_sach1 = ctk.CTkEntry(right_frame, placeholder_text="Mã sách (VD: S00102)", height=35)
        self.txt_sach1.pack(fill="x", pady=(1, 6))

        lbl_s2 = ctk.CTkLabel(right_frame, text="Cuốn sách 2 (Tùy chọn)", font=ctk.CTkFont(size=11))
        lbl_s2.pack(anchor="w")
        self.txt_sach2 = ctk.CTkEntry(right_frame, placeholder_text="Mã sách thứ 2 (nếu có)...", height=35)
        self.txt_sach2.pack(fill="x", pady=(1, 6))

        lbl_s3 = ctk.CTkLabel(right_frame, text="Cuốn sách 3 (Tùy chọn)", font=ctk.CTkFont(size=11))
        lbl_s3.pack(anchor="w")
        self.txt_sach3 = ctk.CTkEntry(right_frame, placeholder_text="Mã sách thứ 3 (nếu có)...", height=35)
        self.txt_sach3.pack(fill="x", pady=(1, 12))

        # Ghi chú nghiệp vụ
        lbl_note = ctk.CTkLabel(
            right_frame,
            text="Quy định mượn trả:\n- Mỗi độc giả chỉ được giữ tối đa 3 cuốn chưa trả.\n- Trả quá hạn phạt: 500 VNĐ / ngày trễ.\n- Mất sách: Phạt đúng 100% giá bìa.",
            font=ctk.CTkFont(size=11),
            text_color="#9CA3AF",
            justify="left"
        )
        lbl_note.pack(anchor="w", pady=(0, 15))

        btn_borrow = ctk.CTkButton(
            right_frame,
            text="Xác Nhận Cho Mượn",
            height=40,
            font=ctk.CTkFont(weight="bold"),
            command=self.handle_borrow_books
        )
        btn_borrow.pack(fill="x", pady=(0, 10))

        btn_clear = ctk.CTkButton(
            right_frame,
            text="Làm Mới Form",
            height=35,
            fg_color="#4B5563",
            hover_color="#374151",
            command=self.clear_form
        )
        btn_clear.pack(fill="x", pady=(0, 20))

    def load_data(self):
        try:
            records = MuonTraDAO.get_danh_sach_phieu_dang_muon()
            self.display_records(records)
            self.txt_search.delete(0, "end")
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", f"Không thể tải danh sách mượn sách:\n{ex}")

    def display_records(self, records):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for idx, r in enumerate(records):
            so_ngay_tre = r.get("SoNgayTre", 0)
            tag = "overdue" if so_ngay_tre > 0 else ("oddrow" if idx % 2 != 0 else "evenrow")

            self.tree.insert("", "end", values=(
                r.get("MAPHIEU"),
                r.get("MADG"),
                r.get("HoTenDG"),
                r.get("DIENTHOAI") or "",
                r.get("MASACH"),
                r.get("TENSACH"),
                r.get("HinhThucStr"),
                r.get("NgayMuonStr"),
                r.get("SoNgayDaMuon"),
                f"{so_ngay_tre} ngày" if so_ngay_tre > 0 else "Đúng hạn"
            ), tags=(tag,))

        self.lbl_count.configure(text=f"Tổng: {len(records)} cuốn đang mượn")

    def handle_search(self):
        keyword = self.txt_search.get().strip()
        if not keyword:
            self.load_data()
            return
        try:
            records = MuonTraDAO.search_phieu_dang_muon(keyword)
            self.display_records(records)
        except Exception as ex:
            messagebox.showerror("Lỗi tìm kiếm", str(ex))

    def handle_check_docgia(self):
        madg_str = self.txt_madg.get().strip()
        if not madg_str:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập Mã độc giả để kiểm tra!")
            return

        try:
            madg = int(madg_str)
            valid, msg, dang_giu = DocGiaDAO.kiem_tra_the_hop_le_muon_sach(madg)
            if valid:
                con_lai = 3 - dang_giu
                self.lbl_dg_info.configure(
                    text=f"Thẻ HỢP LỆ! Đang giữ: {dang_giu}/3 cuốn (Có thể mượn thêm {con_lai} cuốn)",
                    text_color="#10B981"
                )
            else:
                self.lbl_dg_info.configure(
                    text=f"KHÔNG ĐỦ ĐIỀU KIỆN: {msg}",
                    text_color="#EF4444"
                )
        except ValueError:
            messagebox.showerror("Sai định dạng", "Mã độc giả phải là số nguyên!")
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", str(ex))

    def handle_borrow_books(self):
        madg_str = self.txt_madg.get().strip()
        if not madg_str:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập Mã độc giả!")
            return

        try:
            madg = int(madg_str)
        except ValueError:
            messagebox.showerror("Sai dữ liệu", "Mã độc giả phải là số nguyên!")
            return

        # Tập hợp danh sách sách muốn mượn
        s1 = self.txt_sach1.get().strip()
        s2 = self.txt_sach2.get().strip()
        s3 = self.txt_sach3.get().strip()

        danh_sach = [s for s in [s1, s2, s3] if s]
        if not danh_sach:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập ít nhất 1 mã cuốn sách!")
            return

        # Kiểm tra trùng lặp trong cùng 1 lần mượn
        if len(danh_sach) != len(set(danh_sach)):
            messagebox.showwarning("Trùng lặp", "Các mã sách trong cùng một phiếu mượn không được trùng nhau!")
            return

        hinh_thuc = 1 if "Mang về" in self.cb_hinhthuc.get() else 0
        manv = self.current_user.get("MANV", 1)

        try:
            maphieu = MuonTraDAO.tao_phieu_muon(madg, manv, hinh_thuc, danh_sach)
            messagebox.showinfo(
                "Mượn sách thành công",
                f"Đã lập Phiếu mượn thành công!\nMã Phiếu: {maphieu}\nSố sách mượn: {len(danh_sach)} cuốn."
            )
            self.clear_form()
            self.load_data()
        except ValueError as val_err:
            messagebox.showwarning("Không thể cho mượn", str(val_err))
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", str(ex))

    def handle_return_book(self, tinh_trang_tra: int, bi_mat: bool = False):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một dòng sách đang mượn trên bảng để xác nhận trả!")
            return

        item = self.tree.item(selected[0])
        values = item.get("values", [])
        if not values or len(values) < 6:
            messagebox.showwarning("Lỗi dữ liệu", "Dòng được chọn không hợp lệ hoặc thiếu dữ liệu!")
            return

        maphieu = int(values[0])
        madg = values[1]
        hoten = values[2]
        masach = str(values[4])
        tensach = values[5]

        # 1. Tính toán trước hóa đơn phạt
        try:
            phi_info = MuonTraDAO.tinh_toan_phi_phat(
                maphieu=maphieu, 
                masach=masach, 
                tinh_trang_tra=int(tinh_trang_tra), 
                bi_mat=bi_mat
            )
        except Exception as ex:
            messagebox.showerror("Lỗi tính phí", str(ex))
            return

        # 2. Soạn bảng thông báo chi tiết
        msg = f"Xác nhận trả sách cho độc giả: {hoten} (Mã ĐG: {madg})\n"
        msg += f"Cuốn sách: {masach} - {tensach}\n\n"
        msg += f"- Số ngày đã mượn: {phi_info['SoNgayDaMuon']} ngày\n"
        msg += f"- Trễ hạn: {phi_info['SoNgayTre']} ngày -> Phạt trễ: {phi_info['TienPhatTre']:,} VNĐ\n"

        if bi_mat:
            msg += f"- Bồi thường mất sách (100% giá bìa): {phi_info['TienMatSach']:,} VNĐ\n"
        elif tinh_trang_tra == 0:
            msg += f"- Phạt sách hư hỏng (50% giá bìa): {phi_info['TienPhatHong']:,} VNĐ\n"

        msg += f"\n>>> TỔNG SỐ TIỀN PHẢI THU: {phi_info['TongPhat']:,} VNĐ <<<\n\n"
        msg += "Bạn có chắc chắn muốn xác nhận trả sách này?"

        confirm = messagebox.askyesno("Hóa Đơn Trả Sách & Xử Phạt", msg)
        if not confirm:
            return

        # 3. Ghi nhận trả sách vào CSDL
        manvns = int(self.current_user.get("MANV", 1))
        try:
            MuonTraDAO.xac_nhan_tra_sach(
                maphieu=maphieu, 
                masach=masach, 
                manvns=manvns, 
                tinh_trang_tra=int(tinh_trang_tra), 
                bi_mat=bi_mat
            )
            messagebox.showinfo("Thành công", f"Đã thu hồi sách '{masach}' và cập nhật kho thành công!")
            self.load_data()
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", str(ex))

    def clear_form(self):
        """Xóa trắng các ô nhập trên form và khôi phục placeholder."""
        self.focus_set()
        self.txt_madg.delete(0, "end")
        self.txt_sach1.delete(0, "end")
        self.txt_sach2.delete(0, "end")
        self.txt_sach3.delete(0, "end")
        self.lbl_dg_info.configure(text="")
        self.cb_hinhthuc.set("Mang về (Hạn 30 ngày)")
