import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import ui.ctk_patch
from typing import Dict, Any, Optional
from dao.sach_dao import SachDAO

class TabSach(ctk.CTkFrame):
    """
    Giao diện Quản Lý Sách:
    - Hiển thị danh sách Cuốn sách vật lý (SACH) và Đầu sách (ISBN).
    - Tìm kiếm tức thì theo Tên sách, Mã sách, ISBN, Thể loại, Tác giả.
    - Cập nhật tình trạng sách (Tốt / Hư hỏng).
    - Form nhập thêm Cuốn sách mới và Đầu sách (ISBN) mới.
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
            text="DANH MỤC SÁCH THƯ VIỆN", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_title.pack(side="left")

        self.lbl_count = ctk.CTkLabel(
            header_frame, 
            text="Tổng: 0 cuốn sách", 
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
            placeholder_text="Nhập Tên sách, Mã sách, ISBN, Thể loại hoặc Tác giả...",
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

        # 3. Bảng Treeview (Chuẩn Dark Mode)
        tree_container = ctk.CTkFrame(left_frame, fg_color="#1E2229", corner_radius=8)
        tree_container.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="nsew")
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure(
            "Treeview",
            background="#1E2229",
            foreground="#F3F4F6",
            fieldbackground="#1E2229",
            rowheight=30,
            borderwidth=0,
            relief="flat",
            font=("Segoe UI", 10)
        )
        self.style.map(
            "Treeview",
            background=[("selected", "#2563EB")],
            foreground=[("selected", "#FFFFFF")],
            fieldbackground=[("!disabled", "#1E2229"), ("disabled", "#1E2229")]
        )
        self.style.configure(
            "Treeview.Heading",
            background="#111827",
            foreground="#F9FAFB",
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
            padding=(5, 6)
        )
        self.style.map(
            "Treeview.Heading",
            background=[("active", "#1F2937"), ("!active", "#111827")],
            foreground=[("active", "#FFFFFF"), ("!active", "#F9FAFB")]
        )

        columns = (
            "MASACH", "ISBN", "TENSACH", "THELOAI", "HOTENTG",
            "ViTri", "GiaBia", "TINHTRANG", "CHOMUON"
        )

        self.tree = ttk.Treeview(
            tree_container, 
            columns=columns, 
            show="headings", 
            selectmode="browse"
        )

        col_configs = {
            "MASACH": ("Mã Sách", 75, "center"),
            "ISBN": ("ISBN", 85, "center"),
            "TENSACH": ("Tên Đầu Sách", 180, "w"),
            "THELOAI": ("Thể Loại", 110, "w"),
            "HOTENTG": ("Tác Giả", 120, "w"),
            "ViTri": ("Vị Trí Kệ", 110, "center"),
            "GiaBia": ("Giá Bìa (VNĐ)", 95, "e"),
            "TINHTRANG": ("Tình Trạng", 90, "center"),
            "CHOMUON": ("Cho Mượn", 95, "center")
        }

        for col, (heading, width, align) in col_configs.items():
            self.tree.heading(col, text=heading, anchor=align)
            self.tree.column(col, width=width, minwidth=40, anchor=align)

        # Màu nền xen kẽ & Trạng thái
        self.tree.tag_configure("oddrow", background="#1E2229", foreground="#F3F4F6")
        self.tree.tag_configure("evenrow", background="#242830", foreground="#F3F4F6")
        self.tree.tag_configure("borrowed", background="#332B1A", foreground="#FBBF24") # Đang mượn (vàng)
        self.tree.tag_configure("damaged", background="#382226", foreground="#F87171")  # Hỏng (đỏ)

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # 4. Thanh thao tác nhanh dưới bảng
        action_bar = ctk.CTkFrame(left_frame, fg_color="transparent")
        action_bar.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="ew")

        btn_toggle_status = ctk.CTkButton(
            action_bar,
            text="Báo Hỏng / Khôi Phục Sách",
            fg_color="#D97706",
            hover_color="#B45309",
            font=ctk.CTkFont(weight="bold"),
            command=self.handle_toggle_tinh_trang
        )
        btn_toggle_status.pack(side="left", padx=(0, 10))

    def create_right_panel(self):
        right_frame = ctk.CTkScrollableFrame(self, width=340, corner_radius=12)
        right_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")

        lbl_panel_title = ctk.CTkLabel(
            right_frame, 
            text="NHẬP SÁCH VÀO KHO", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        lbl_panel_title.pack(pady=(15, 12), anchor="w")

        # Form 1: Thêm cuốn sách vật lý (SACH)
        lbl_cuon_title = ctk.CTkLabel(
            right_frame, 
            text="Thêm Cuốn Sách Vật Lý (SACH)", 
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#60A5FA"
        )
        lbl_cuon_title.pack(anchor="w", pady=(5, 8))

        lbl_ms = ctk.CTkLabel(right_frame, text="Mã cuốn sách *", font=ctk.CTkFont(size=12))
        lbl_ms.pack(anchor="w")
        self.txt_masach = ctk.CTkEntry(right_frame, placeholder_text="Ví dụ: S00103", height=35)
        self.txt_masach.pack(fill="x", pady=(2, 6))

        lbl_isbn = ctk.CTkLabel(right_frame, text="Thuộc đầu sách (ISBN) *", font=ctk.CTkFont(size=12))
        lbl_isbn.pack(anchor="w")
        self.cb_isbn = ctk.CTkComboBox(right_frame, values=["Đang tải..."], height=35)
        self.cb_isbn.pack(fill="x", pady=(2, 6))

        lbl_vt = ctk.CTkLabel(right_frame, text="Vị trí ngăn tủ / kệ", font=ctk.CTkFont(size=12))
        lbl_vt.pack(anchor="w")
        self.cb_ngantu = ctk.CTkComboBox(right_frame, values=["Chưa xếp"], height=35)
        self.cb_ngantu.pack(fill="x", pady=(2, 10))

        btn_add_cuon = ctk.CTkButton(
            right_frame,
            text="Nhập Cuốn Sách Mới",
            height=38,
            font=ctk.CTkFont(weight="bold"),
            command=self.handle_add_cuon_sach
        )
        btn_add_cuon.pack(fill="x", pady=(0, 6))

        btn_clear_cuon = ctk.CTkButton(
            right_frame,
            text="Làm Mới Form Cuốn Sách",
            height=32,
            fg_color="#4B5563",
            hover_color="#374151",
            command=self.clear_cuon_form
        )
        btn_clear_cuon.pack(fill="x", pady=(0, 15))

        # Phân cách
        separator = ctk.CTkFrame(right_frame, height=2, fg_color="#374151")
        separator.pack(fill="x", pady=10)

        # Form 2: Thêm đầu sách mới (ISBN)
        lbl_dau_title = ctk.CTkLabel(
            right_frame, 
            text="Tạo Đầu Sách Mới (ISBN)", 
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#34D399"
        )
        lbl_dau_title.pack(anchor="w", pady=(5, 8))

        lbl_new_isbn = ctk.CTkLabel(right_frame, text="Mã ISBN (10 ký tự) *", font=ctk.CTkFont(size=12))
        lbl_new_isbn.pack(anchor="w")
        self.txt_new_isbn = ctk.CTkEntry(right_frame, placeholder_text="Ví dụ: ISBN000004", height=35)
        self.txt_new_isbn.pack(fill="x", pady=(2, 6))

        lbl_tensach = ctk.CTkLabel(right_frame, text="Tên đầu sách *", font=ctk.CTkFont(size=12))
        lbl_tensach.pack(anchor="w")
        self.txt_tensach = ctk.CTkEntry(right_frame, placeholder_text="Tên sách đầy đủ...", height=35)
        self.txt_tensach.pack(fill="x", pady=(2, 6))

        lbl_gia = ctk.CTkLabel(right_frame, text="Giá bìa (VNĐ) *", font=ctk.CTkFont(size=12))
        lbl_gia.pack(anchor="w")
        self.txt_gia = ctk.CTkEntry(right_frame, placeholder_text="Ví dụ: 120000", height=35)
        self.txt_gia.pack(fill="x", pady=(2, 6))

        lbl_tl = ctk.CTkLabel(right_frame, text="Thể loại", font=ctk.CTkFont(size=12))
        lbl_tl.pack(anchor="w")
        self.cb_theloai = ctk.CTkComboBox(right_frame, values=["Chưa có"], height=35)
        self.cb_theloai.pack(fill="x", pady=(2, 6))

        lbl_tg = ctk.CTkLabel(right_frame, text="Tác giả chính", font=ctk.CTkFont(size=12))
        lbl_tg.pack(anchor="w")
        self.cb_tacgia = ctk.CTkComboBox(right_frame, values=["Chưa có"], height=35)
        self.cb_tacgia.pack(fill="x", pady=(2, 6))

        lbl_nn = ctk.CTkLabel(right_frame, text="Ngôn ngữ", font=ctk.CTkFont(size=12))
        lbl_nn.pack(anchor="w")
        self.cb_ngonngu = ctk.CTkComboBox(right_frame, values=["Chưa có"], height=35)
        self.cb_ngonngu.pack(fill="x", pady=(2, 6))

        lbl_nxb = ctk.CTkLabel(right_frame, text="Nhà xuất bản", font=ctk.CTkFont(size=12))
        lbl_nxb.pack(anchor="w")
        self.txt_nxb = ctk.CTkEntry(right_frame, placeholder_text="Ví dụ: NXB Trẻ", height=35)
        self.txt_nxb.pack(fill="x", pady=(2, 6))

        lbl_st = ctk.CTkLabel(right_frame, text="Số trang (Tùy chọn)", font=ctk.CTkFont(size=12))
        lbl_st.pack(anchor="w")
        self.txt_sotrang = ctk.CTkEntry(right_frame, placeholder_text="Ví dụ: 350", height=35)
        self.txt_sotrang.pack(fill="x", pady=(2, 6))

        lbl_ks = ctk.CTkLabel(right_frame, text="Khổ sách (Tùy chọn)", font=ctk.CTkFont(size=12))
        lbl_ks.pack(anchor="w")
        self.txt_khosach = ctk.CTkEntry(right_frame, placeholder_text="Ví dụ: 15x23 cm", height=35)
        self.txt_khosach.pack(fill="x", pady=(2, 6))

        lbl_lxb = ctk.CTkLabel(right_frame, text="Lần xuất bản", font=ctk.CTkFont(size=12))
        lbl_lxb.pack(anchor="w")
        self.txt_lanxuatban = ctk.CTkEntry(right_frame, placeholder_text="Ví dụ: 1", height=35)
        self.txt_lanxuatban.pack(fill="x", pady=(2, 6))

        lbl_nd = ctk.CTkLabel(right_frame, text="Nội dung tóm tắt", font=ctk.CTkFont(size=12))
        lbl_nd.pack(anchor="w")
        self.txt_noidung = ctk.CTkEntry(right_frame, placeholder_text="Mô tả tóm tắt nội dung sách...", height=35)
        self.txt_noidung.pack(fill="x", pady=(2, 12))

        btn_add_isbn = ctk.CTkButton(
            right_frame,
            text="Tạo Đầu Sách Mới",
            height=38,
            fg_color="#059669",
            hover_color="#047857",
            font=ctk.CTkFont(weight="bold"),
            command=self.handle_add_isbn
        )
        btn_add_isbn.pack(fill="x", pady=(0, 6))

        btn_clear_isbn = ctk.CTkButton(
            right_frame,
            text="Làm Mới Form Đầu Sách",
            height=32,
            fg_color="#4B5563",
            hover_color="#374151",
            command=self.clear_isbn_form
        )
        btn_clear_isbn.pack(fill="x", pady=(0, 20))

    def load_data(self):
        """Tải dữ liệu danh mục sách và combobox."""
        try:
            records = SachDAO.get_all_sach()
            self.display_records(records)
            self.txt_search.delete(0, "end")
            self.load_comboboxes()
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", f"Không thể tải danh sách sách:\n{ex}")

    def load_comboboxes(self):
        """Nạp dữ liệu cho các ComboBox chọn ISBN, Ngăn tủ, Thể loại, Tác giả, Ngôn ngữ."""
        try:
            # ISBN
            isbn_list = SachDAO.get_all_isbn()
            self.isbn_map = {f"{r['ISBN']} - {r['TENSACH']}": r['ISBN'] for r in isbn_list}
            if self.isbn_map:
                self.cb_isbn.configure(values=list(self.isbn_map.keys()))
                self.cb_isbn.set(list(self.isbn_map.keys())[0])

            # Ngăn tủ
            ngantu_list = SachDAO.get_danh_muc_ngan_tu()
            self.ngantu_map = {f"{r['KE']} ({r['MOTA']})": r['MANGANTU'] for r in ngantu_list}
            if self.ngantu_map:
                self.cb_ngantu.configure(values=list(self.ngantu_map.keys()))
                self.cb_ngantu.set(list(self.ngantu_map.keys())[0])

            # Thể loại
            tl_list = SachDAO.get_danh_muc_the_loai()
            self.tl_map = {r['THELOAI']: r['MATL'] for r in tl_list}
            if self.tl_map:
                self.cb_theloai.configure(values=list(self.tl_map.keys()))
                self.cb_theloai.set(list(self.tl_map.keys())[0])

            # Tác giả
            tg_list = SachDAO.get_danh_muc_tac_gia()
            self.tg_map = {r['HOTENTG']: r['MATACGIA'] for r in tg_list}
            if self.tg_map:
                self.cb_tacgia.configure(values=list(self.tg_map.keys()))
                self.cb_tacgia.set(list(self.tg_map.keys())[0])

            # Ngôn ngữ
            nn_list = SachDAO.get_danh_muc_ngon_ngu()
            self.nn_map = {r['NGONNGU']: r['MANGONNGU'] for r in nn_list}
            if self.nn_map:
                self.cb_ngonngu.configure(values=list(self.nn_map.keys()))
                self.cb_ngonngu.set(list(self.nn_map.keys())[0])

        except Exception as ex:
            print("Lỗi tải danh mục combobox:", ex)

    def display_records(self, records):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for idx, r in enumerate(records):
            is_good = r.get("TINHTRANG") == 1
            is_borrowed = r.get("CHOMUON") == 1

            tinhtrang_str = "Tốt" if is_good else "Hư hỏng"
            chomuon_str = "Đang mượn" if is_borrowed else "Sẵn có"

            if not is_good:
                tag = "damaged"
            elif is_borrowed:
                tag = "borrowed"
            else:
                tag = "oddrow" if idx % 2 != 0 else "evenrow"

            gia_str = f"{r.get('GiaBia', 0):,}"

            self.tree.insert("", "end", values=(
                r.get("MASACH"),
                r.get("ISBN"),
                r.get("TENSACH"),
                r.get("THELOAI"),
                r.get("HOTENTG"),
                r.get("ViTri"),
                gia_str,
                tinhtrang_str,
                chomuon_str
            ), tags=(tag,))

        self.lbl_count.configure(text=f"Tổng: {len(records)} cuốn sách")

    def handle_search(self):
        keyword = self.txt_search.get().strip()
        if not keyword:
            self.load_data()
            return
        try:
            records = SachDAO.search_sach(keyword)
            self.display_records(records)
        except Exception as ex:
            messagebox.showerror("Lỗi tìm kiếm", str(ex))

    def handle_toggle_tinh_trang(self):
        """Chuyển đổi tình trạng sách Tốt <-> Hư hỏng."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một cuốn sách trên bảng để cập nhật tình trạng!")
            return

        item = self.tree.item(selected[0])
        values = item.get("values", [])
        if not values or len(values) < 8:
            messagebox.showwarning("Lỗi dữ liệu", "Dòng được chọn không hợp lệ hoặc thiếu dữ liệu!")
            return

        masach = str(values[0])
        tensach = str(values[2])
        current_tt = str(values[7])

        new_status = 0 if current_tt == "Tốt" else 1
        action_name = "báo HƯ HỎNG" if new_status == 0 else "khôi phục trạng thái TỐT"

        confirm = messagebox.askyesno(
            "Xác nhận",
            f"Bạn có chắc muốn {action_name} cho cuốn sách '{masach}' ({tensach})?"
        )
        if not confirm:
            return

        try:
            success = SachDAO.cap_nhat_tinh_trang(masach, new_status)
            if success:
                messagebox.showinfo("Thành công", f"Đã cập nhật tình trạng sách '{masach}' thành công!")
                self.load_data()
            else:
                messagebox.showerror("Thất bại", "Không thể cập nhật CSDL!")
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", str(ex))

    def handle_add_cuon_sach(self):
        masach = self.txt_masach.get().strip()
        selected_isbn_key = self.cb_isbn.get()
        selected_nt_key = self.cb_ngantu.get()

        if not masach:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập Mã cuốn sách!")
            return

        isbn = getattr(self, "isbn_map", {}).get(selected_isbn_key)
        if not isbn:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng chọn Đầu sách ISBN!")
            return

        mangantu = getattr(self, "ngantu_map", {}).get(selected_nt_key)

        try:
            SachDAO.them_cuon_sach(masach, isbn, mangantu)
            messagebox.showinfo("Thành công", f"Đã thêm cuốn sách '{masach}' vào kho thành công!")
            self.clear_cuon_form()
            self.load_data()
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", f"Không thể thêm cuốn sách:\n{ex}")

    def handle_add_isbn(self):
        isbn = self.txt_new_isbn.get().strip()
        tensach = self.txt_tensach.get().strip()
        gia_str = self.txt_gia.get().strip()
        nxb = self.txt_nxb.get().strip()
        sotrang_str = self.txt_sotrang.get().strip()
        khosach = self.txt_khosach.get().strip()
        lanxb_str = self.txt_lanxuatban.get().strip()
        noidung = self.txt_noidung.get().strip()

        matl = getattr(self, "tl_map", {}).get(self.cb_theloai.get())
        matg = getattr(self, "tg_map", {}).get(self.cb_tacgia.get())
        mann = getattr(self, "nn_map", {}).get(self.cb_ngonngu.get())

        if not isbn or not tensach:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập đầy đủ Mã ISBN và Tên đầu sách!")
            return

        try:
            gia = int(gia_str) if gia_str else 0
        except ValueError:
            messagebox.showerror("Sai dữ liệu", "Giá bìa phải là số nguyên!")
            return

        try:
            sotrang = int(sotrang_str) if sotrang_str else None
        except ValueError:
            messagebox.showerror("Sai dữ liệu", "Số trang phải là số nguyên!")
            return

        try:
            lanxuatban = int(lanxb_str) if lanxb_str else 1
        except ValueError:
            messagebox.showerror("Sai dữ liệu", "Lần xuất bản phải là số nguyên!")
            return

        data = {
            "ISBN": isbn,
            "TENSACH": tensach,
            "GIA": gia,
            "NHAXB": nxb or None,
            "MATL": matl,
            "MANGONNGU": mann,
            "SOTRANG": sotrang,
            "KHOSACH": khosach or None,
            "LANXUATBAN": lanxuatban,
            "NOIDUNG": noidung or None
        }

        try:
            SachDAO.them_dau_sach(data, matacgia=matg)
            messagebox.showinfo("Thành công", f"Đã tạo đầu sách mới: {tensach} ({isbn})!")
            self.clear_isbn_form()
            self.load_data()
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", f"Không thể tạo đầu sách:\n{ex}")

    def clear_cuon_form(self):
        """Làm mới form nhập cuốn sách vật lý và khôi phục gợi ý placeholder."""
        self.focus_set()
        self.txt_masach.delete(0, "end")
        if hasattr(self, "isbn_map") and self.isbn_map:
            self.cb_isbn.set(list(self.isbn_map.keys())[0])
        if hasattr(self, "ngantu_map") and self.ngantu_map:
            self.cb_ngantu.set(list(self.ngantu_map.keys())[0])

    def clear_isbn_form(self):
        """Làm mới form tạo đầu sách mới và khôi phục gợi ý placeholder."""
        self.focus_set()
        self.txt_new_isbn.delete(0, "end")
        self.txt_tensach.delete(0, "end")
        self.txt_gia.delete(0, "end")
        self.txt_nxb.delete(0, "end")
        self.txt_sotrang.delete(0, "end")
        self.txt_khosach.delete(0, "end")
        self.txt_lanxuatban.delete(0, "end")
        self.txt_noidung.delete(0, "end")
        if hasattr(self, "tl_map") and self.tl_map:
            self.cb_theloai.set(list(self.tl_map.keys())[0])
        if hasattr(self, "tg_map") and self.tg_map:
            self.cb_tacgia.set(list(self.tg_map.keys())[0])
        if hasattr(self, "nn_map") and self.nn_map:
            self.cb_ngonngu.set(list(self.nn_map.keys())[0])

    def clear_form(self):
        """Làm mới toàn bộ các form nhập sách."""
        self.clear_cuon_form()
        self.clear_isbn_form()
