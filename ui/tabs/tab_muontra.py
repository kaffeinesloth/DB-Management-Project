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

        # Đăng ký sự kiện Nhấp kép (Double Click) vào dòng bất kỳ trên bảng để mở Pop-up trả sách
        self.tree.bind("<Double-1>", lambda event: self.open_popup_return_grouped())

        # 4. Thanh thao tác Trả sách dưới bảng (Chỉ dùng 1 nút duy nhất)
        action_bar = ctk.CTkFrame(left_frame, fg_color="transparent")
        action_bar.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="ew")

        btn_return_popup = ctk.CTkButton(
            action_bar,
            text="📦 XÁC NHẬN TRẢ SÁCH (Hoặc Nhấp Kép Vào Dòng Trong Bảng)",
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            height=42,
            font=ctk.CTkFont(weight="bold", size=13),
            command=self.open_popup_return_grouped
        )
        btn_return_popup.pack(fill="x", expand=True)

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

        # 3. Danh sách mã sách mượn (Tối đa 3 cuốn - Hỗ trợ gợi ý sách khả dụng)
        lbl_sach_title = ctk.CTkLabel(
            right_frame, 
            text="Danh sách sách mượn (Gợi ý chưa mượn):", 
            font=ctk.CTkFont(size=12, weight="bold")
        )
        lbl_sach_title.pack(anchor="w", pady=(5, 4))

        lbl_s1 = ctk.CTkLabel(right_frame, text="Cuốn sách 1 *", font=ctk.CTkFont(size=11))
        lbl_s1.pack(anchor="w")
        self.cb_sach1 = ctk.CTkComboBox(right_frame, values=["-- Chọn hoặc gõ mã sách --"], height=35)
        self.cb_sach1.set("-- Chọn hoặc gõ mã sách --")
        self.cb_sach1.pack(fill="x", pady=(1, 6))

        lbl_s2 = ctk.CTkLabel(right_frame, text="Cuốn sách 2 (Tùy chọn)", font=ctk.CTkFont(size=11))
        lbl_s2.pack(anchor="w")
        self.cb_sach2 = ctk.CTkComboBox(right_frame, values=["-- Chọn hoặc gõ mã sách --"], height=35)
        self.cb_sach2.set("-- Chọn hoặc gõ mã sách --")
        self.cb_sach2.pack(fill="x", pady=(1, 6))

        lbl_s3 = ctk.CTkLabel(right_frame, text="Cuốn sách 3 (Tùy chọn)", font=ctk.CTkFont(size=11))
        lbl_s3.pack(anchor="w")
        self.cb_sach3 = ctk.CTkComboBox(right_frame, values=["-- Chọn hoặc gõ mã sách --"], height=35)
        self.cb_sach3.set("-- Chọn hoặc gõ mã sách --")
        self.cb_sach3.pack(fill="x", pady=(1, 12))

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
            self.load_available_books_recommendation()
        except ValueError as ve:
            messagebox.showwarning("Cảnh báo", str(ve))
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", f"Không thể tải danh sách mượn sách:\n{ex}")

    def load_available_books_recommendation(self):
        """Tải danh sách các cuốn sách đang sẵn sàng (CHOMUON = 0, TINHTRANG = 1) làm gợi ý cho Combobox."""
        try:
            available_books = SachDAO.get_danh_sach_sach_san_sang()
            options = ["-- Chọn hoặc gõ mã sách --"]
            for b in available_books:
                options.append(f"{b['MASACH']} | {b['TENSACH']}")
            
            self.cb_sach1.configure(values=options)
            self.cb_sach2.configure(values=options)
            self.cb_sach3.configure(values=options)
        except Exception as ex:
            print(f"Lỗi tải danh sách gợi ý sách: {ex}")

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
        except ValueError as ve:
            messagebox.showwarning("Cảnh báo", str(ve))
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

    def _parse_masach_input(self, raw_input: str) -> str:
        text = raw_input.strip()
        if not text or text.startswith("--"):
            return ""
        if " | " in text:
            return text.split(" | ")[0].strip()
        return text

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

        # Tập hợp danh sách sách muốn mượn từ các combobox gợi ý
        s1 = self._parse_masach_input(self.cb_sach1.get())
        s2 = self._parse_masach_input(self.cb_sach2.get())
        s3 = self._parse_masach_input(self.cb_sach3.get())

        danh_sach = [s for s in [s1, s2, s3] if s]
        if not danh_sach:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng chọn hoặc nhập ít nhất 1 cuốn sách muốn mượn!")
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
        except ValueError as ve:
            messagebox.showwarning("Cảnh báo", str(ve))
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
        except ValueError as ve:
            messagebox.showwarning("Cảnh báo", str(ve))
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", str(ex))

    def open_popup_return_grouped(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một dòng phiếu mượn trên bảng để mở Pop-up trả sách!")
            return

        item = self.tree.item(selected[0])
        values = item.get("values", [])
        if not values:
            return

        maphieu = int(values[0])
        madg = values[1]
        hoten = values[2]

        PopupTraSachTheoSoLuong(
            parent=self,
            maphieu=maphieu,
            hoten_dg=hoten,
            madg=madg,
            current_user=self.current_user,
            on_success_callback=self.load_data
        )

    def clear_form(self):
        """Xóa trắng các ô nhập trên form và khôi phục placeholder."""
        self.focus_set()
        self.txt_madg.delete(0, "end")
        self.cb_sach1.set("-- Chọn hoặc gõ mã sách --")
        self.cb_sach2.set("-- Chọn hoặc gõ mã sách --")
        self.cb_sach3.set("-- Chọn hoặc gõ mã sách --")
        self.lbl_dg_info.configure(text="")
        self.cb_hinhthuc.set("Mang về (Hạn 30 ngày)")


class PopupTraSachTheoSoLuong(ctk.CTkToplevel):
    """Pop-up trả sách gom nhóm theo Đầu sách (ISBN) và Số lượng."""

    def __init__(self, parent, maphieu: int, hoten_dg: str, madg: Any, current_user: Dict[str, Any], on_success_callback=None):
        super().__init__(parent)
        self.title(f"Xác Nhận Trả Sách Gom Nhóm - Phiếu #{maphieu}")
        self.geometry("920x620")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.maphieu = maphieu
        self.hoten_dg = hoten_dg
        self.madg = madg
        self.current_user = current_user
        self.on_success_callback = on_success_callback

        self.rows_data = []
        self.books_grouped = []

        self.setup_ui()
        self.load_grouped_data()

    def setup_ui(self):
        header = ctk.CTkFrame(self, fg_color="#1F2937", corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)

        title_lbl = ctk.CTkLabel(
            header,
            text=f"📖 TRẢ SÁCH THEO SỐ LƯỢNG - PHIẾU MƯỢN #{self.maphieu}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#F9FAFB"
        )
        title_lbl.pack(anchor="w", padx=20, pady=(12, 2))

        sub_lbl = ctk.CTkLabel(
            header,
            text=f"👤 Độc giả: {self.hoten_dg} (Mã ĐG: {self.madg})",
            font=ctk.CTkFont(size=12),
            text_color="#9CA3AF"
        )
        sub_lbl.pack(anchor="w", padx=20, pady=(0, 12))

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=20, pady=10)

        btn_select_all = ctk.CTkButton(
            toolbar,
            text="🟢 Trả Tất Cả (Nguyên Vẹn)",
            fg_color="#059669",
            hover_color="#047857",
            font=ctk.CTkFont(weight="bold"),
            command=self.handle_select_all
        )
        btn_select_all.pack(side="left", padx=(0, 10))

        btn_reset = ctk.CTkButton(
            toolbar,
            text="🟡 Bỏ Chọn Tất Cả",
            fg_color="#D97706",
            hover_color="#B45309",
            command=self.handle_reset_all
        )
        btn_reset.pack(side="left")

        self.scroll_frame = ctk.CTkScrollableFrame(self, corner_radius=8)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        footer = ctk.CTkFrame(self, fg_color="#1E2229", corner_radius=10)
        footer.pack(fill="x", padx=20, pady=(0, 15))

        self.lbl_summary = ctk.CTkLabel(
            footer,
            text="Tổng chọn trả: 0 cuốn | Phạt trễ: 0đ | Bồi thường: 0đ | TỔNG CỘNG: 0 VNĐ",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#10B981"
        )
        self.lbl_summary.pack(side="left", padx=20, pady=15)

        btn_confirm = ctk.CTkButton(
            footer,
            text="🚀 Xác Nhận Trả Sách",
            font=ctk.CTkFont(weight="bold", size=13),
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            height=38,
            command=self.handle_confirm_return
        )
        btn_confirm.pack(side="right", padx=(10, 20), pady=12)

        btn_cancel = ctk.CTkButton(
            footer,
            text="❌ Hủy Bỏ",
            fg_color="#4B5563",
            hover_color="#374151",
            height=38,
            command=self.destroy
        )
        btn_cancel.pack(side="right", pady=12)

    def load_grouped_data(self):
        try:
            self.books_grouped = MuonTraDAO.get_chi_tiet_phieu_gom_nhom(self.maphieu)
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", f"Không thể tải danh sách sách mượn:\n{ex}")
            self.destroy()
            return

        if not self.books_grouped:
            messagebox.showinfo("Thông báo", "Tất cả các cuốn sách trong phiếu mượn này đã được trả!")
            self.destroy()
            return

        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.rows_data.clear()

        for idx, book in enumerate(self.books_grouped):
            card = ctk.CTkFrame(self.scroll_frame, corner_radius=8)
            card.pack(fill="x", padx=5, pady=5)
            card.grid_columnconfigure(3, weight=1)

            title_txt = f"{idx+1}. {book['TENSACH']} (ISBN: {book['ISBN']})"
            lbl_title = ctk.CTkLabel(card, text=title_txt, font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
            lbl_title.grid(row=0, column=0, columnspan=5, padx=12, pady=(10, 2), sticky="w")

            sub_info = f"Giá bìa: {book['GiaBia']:,}đ | Đang mượn còn lại: {book['ConMuon']} cuốn"
            if book['SoNgayTre'] > 0:
                sub_info += f" | Trễ: {book['SoNgayTre']} ngày (Phạt trễ: {book['TienPhatTrePerBook']:,}đ/cuốn)"
            lbl_sub = ctk.CTkLabel(card, text=sub_info, font=ctk.CTkFont(size=11), text_color="#9CA3AF", anchor="w")
            lbl_sub.grid(row=1, column=0, columnspan=5, padx=12, pady=(0, 8), sticky="w")

            lbl_qty = ctk.CTkLabel(card, text="Số lượng trả:", font=ctk.CTkFont(size=12))
            lbl_qty.grid(row=2, column=0, padx=(12, 5), pady=(0, 10), sticky="w")

            txt_qty = ctk.CTkEntry(card, width=65, height=32)
            txt_qty.insert(0, str(book['ConMuon']))
            txt_qty.grid(row=2, column=1, padx=(0, 15), pady=(0, 10), sticky="w")

            lbl_status = ctk.CTkLabel(card, text="Tình trạng:", font=ctk.CTkFont(size=12))
            lbl_status.grid(row=2, column=2, padx=(0, 5), pady=(0, 10), sticky="w")

            cb_status = ctk.CTkComboBox(
                card,
                values=[
                    "🟢 Bình thường (0đ)",
                    "🟡 Bị hỏng/rách (50% giá bìa)",
                    "🔴 Bị mất sách (100% giá bìa)"
                ],
                width=230,
                height=32
            )
            cb_status.set("🟢 Bình thường (0đ)")
            cb_status.grid(row=2, column=3, padx=(0, 12), pady=(0, 10), sticky="w")

            lbl_penalty = ctk.CTkLabel(card, text="Phạt: 0 VNĐ", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FBBF24")
            lbl_penalty.grid(row=2, column=4, padx=(10, 15), pady=(0, 10), sticky="e")

            row_obj = {
                "book": book,
                "txt_qty": txt_qty,
                "cb_status": cb_status,
                "lbl_penalty": lbl_penalty
            }
            self.rows_data.append(row_obj)

            txt_qty.bind("<KeyRelease>", lambda e: self.recalculate_totals())
            cb_status.configure(command=lambda choice: self.recalculate_totals())

        self.recalculate_totals()

    def handle_select_all(self):
        for row in self.rows_data:
            row["txt_qty"].delete(0, "end")
            row["txt_qty"].insert(0, str(row["book"]["ConMuon"]))
            row["cb_status"].set("🟢 Bình thường (0đ)")
        self.recalculate_totals()

    def handle_reset_all(self):
        for row in self.rows_data:
            row["txt_qty"].delete(0, "end")
            row["txt_qty"].insert(0, "0")
            row["cb_status"].set("🟢 Bình thường (0đ)")
        self.recalculate_totals()

    def recalculate_totals(self):
        total_cuon = 0
        total_tre = 0
        total_bt = 0

        for row in self.rows_data:
            book = row["book"]
            qty_str = row["txt_qty"].get().strip()
            try:
                qty = int(qty_str) if qty_str else 0
            except ValueError:
                qty = 0

            qty = max(0, min(qty, book["ConMuon"]))

            status_str = row["cb_status"].get()
            gia_bia = book["GiaBia"]
            tre_per_book = book["TienPhatTrePerBook"]

            fine_tre = qty * tre_per_book
            fine_damage = 0

            if "Bị hỏng" in status_str:
                fine_damage = int(qty * (gia_bia * 0.5))
            elif "Bị mất" in status_str:
                fine_damage = int(qty * gia_bia)

            row_fine = fine_tre + fine_damage
            row["lbl_penalty"].configure(text=f"Phạt: {row_fine:,} VNĐ")

            total_cuon += qty
            total_tre += fine_tre
            total_bt += fine_damage

        tong_cong = total_tre + total_bt
        self.lbl_summary.configure(
            text=f"Tổng chọn trả: {total_cuon} cuốn | Phạt trễ: {total_tre:,}đ | Bồi thường: {total_bt:,}đ | TỔNG CỘNG: {tong_cong:,} VNĐ"
        )

    def handle_confirm_return(self):
        danh_sach_tra = []
        for row in self.rows_data:
            book = row["book"]
            qty_str = row["txt_qty"].get().strip()
            try:
                qty = int(qty_str) if qty_str else 0
            except ValueError:
                qty = 0

            if qty <= 0:
                continue

            if qty > book["ConMuon"]:
                messagebox.showwarning("Sai số lượng", f"Sách '{book['TENSACH']}' chỉ có {book['ConMuon']} cuốn chưa trả!")
                return

            status_str = row["cb_status"].get()
            bi_mat = "Bị mất" in status_str
            tinh_trang_tra = 0 if ("Bị hỏng" in status_str or bi_mat) else 1

            danh_sach_tra.append({
                "ISBN": book["ISBN"],
                "SoLuong": qty,
                "TinhTrangTra": tinh_trang_tra,
                "BiMat": bi_mat
            })

        if not danh_sach_tra:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn số lượng ít nhất 1 cuốn sách để trả!")
            return

        manvns = int(self.current_user.get("MANV", 1))
        try:
            res = MuonTraDAO.xac_nhan_tra_sach_theo_so_luong(
                maphieu=self.maphieu,
                danh_sach_tra=danh_sach_tra,
                manvns=manvns
            )
            messagebox.showinfo(
                "Xác Nhận Thành Công",
                f"Đã ghi nhận trả {res['TongSoCuonTra']} cuốn sách thành công!\n"
                f"- Tiền phạt trễ hạn: {res['TienPhatTre']:,} VNĐ\n"
                f"- Tiền bồi thường hư hỏng / mất: {res['TienPhatHong'] + res['TienMatSach']:,} VNĐ\n"
                f"👉 TỔNG THU CỦA ĐỘC GIẢ: {res['TongPhat']:,} VNĐ"
            )
            self.destroy()
            if self.on_success_callback:
                self.on_success_callback()
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", str(ex))

