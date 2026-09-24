import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from datetime import datetime, timedelta
from typing import Optional
from dao.docgia_dao import DocGiaDAO

class TabDocGia(ctk.CTkFrame):
    """
    Giao diện Quản lý Độc giả (Thẻ thư viện):
    - Hiển thị danh sách độc giả dạng bảng (ttk.Treeview chuẩn Dark Mode đồng bộ).
    - Phân biệt trạng thái: Hoạt động | Quá hạn | Đã khóa.
    - Tìm kiếm tức thì theo Họ tên, CMND, SĐT, Email.
    - Form cấp thẻ mới chống tràn layout, tự động validate dữ liệu.
    - Thao tác nhanh: Gia hạn thẻ (+12 tháng), Khóa / Mở thẻ, Làm mới dữ liệu.
    """

    def __init__(self, master, current_user: dict):
        super().__init__(master, fg_color="transparent")
        self.current_user = current_user

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        # Cột 0 (Bảng dữ liệu): Co giãn linh hoạt (weight=1)
        # Cột 1 (Form thao tác): Chiều rộng cố định 350px (weight=0) để không bao giờ bị cắt chữ
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
            text="DANH SÁCH ĐỘC GIẢ THƯ VIỆN", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_title.pack(side="left")

        self.lbl_count = ctk.CTkLabel(
            header_frame, 
            text="Tổng: 0 độc giả", 
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
            placeholder_text="Nhập Tên, CMND/CCCD, SĐT hoặc Email để tìm...",
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

        # 3. Bảng Treeview (Cấu hình chuẩn Dark Mode)
        tree_container = ctk.CTkFrame(left_frame, fg_color="#1E2229", corner_radius=8)
        tree_container.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="nsew")
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # Áp dụng Dark theme đồng bộ cho toàn bộ Treeview
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
            "MADG", "HoTen", "SOCMND", "GIOITINH", 
            "DIENTHOAI", "EMAILDG", "NGAYLAMTHE", "NGAYHETHAN", "HOATDONG"
        )

        self.tree = ttk.Treeview(
            tree_container, 
            columns=columns, 
            show="headings", 
            selectmode="browse"
        )

        # Cấu hình kích thước cột tối ưu để không bị cuộn ngang
        col_configs = {
            "MADG": ("Mã ĐG", 55, "center"),
            "HoTen": ("Họ và Tên", 135, "w"),
            "SOCMND": ("Số CMND/CCCD", 105, "center"),
            "GIOITINH": ("Giới tính", 65, "center"),
            "DIENTHOAI": ("Điện thoại", 95, "center"),
            "EMAILDG": ("Email", 135, "w"),
            "NGAYLAMTHE": ("Ngày làm thẻ", 88, "center"),
            "NGAYHETHAN": ("Ngày hết hạn", 88, "center"),
            "HOATDONG": ("Trạng thái", 100, "center"),
        }

        for col, (heading, width, align) in col_configs.items():
            self.tree.heading(col, text=heading, anchor=align)
            self.tree.column(col, width=width, minwidth=40, anchor=align)

        # Màu nền xen kẽ & Trạng thái (Luôn có background tối, không bao giờ bị trắng)
        self.tree.tag_configure("oddrow", background="#1E2229", foreground="#F3F4F6")
        self.tree.tag_configure("evenrow", background="#242830", foreground="#F3F4F6")
        self.tree.tag_configure("locked", background="#382226", foreground="#F87171")
        self.tree.tag_configure("expired", background="#383020", foreground="#FBBF24")

        # Scrollbars
        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # 4. Thanh thao tác nhanh dưới bảng
        action_bar = ctk.CTkFrame(left_frame, fg_color="transparent")
        action_bar.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="ew")

        self.btn_extend = ctk.CTkButton(
            action_bar, 
            text="Gia hạn thẻ (+12 tháng)", 
            fg_color="#059669", 
            hover_color="#047857",
            font=ctk.CTkFont(weight="bold"),
            command=self.handle_extend_card
        )
        self.btn_extend.pack(side="left", padx=(0, 10))

        self.btn_toggle_status = ctk.CTkButton(
            action_bar, 
            text="Khóa / Mở thẻ", 
            fg_color="#D97706", 
            hover_color="#B45309",
            font=ctk.CTkFont(weight="bold"),
            command=self.handle_toggle_status
        )
        self.btn_toggle_status.pack(side="left")

    def create_right_panel(self):
        # Chiều rộng cố định 340px chống tràn giao diện
        right_frame = ctk.CTkScrollableFrame(self, width=340, corner_radius=12)
        right_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")

        lbl_form_title = ctk.CTkLabel(
            right_frame, 
            text="CẤP THẺ ĐỘC GIẢ MỚI", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        lbl_form_title.pack(pady=(15, 12), anchor="w")

        self.fields = {}

        # 1. Họ đệm
        lbl_ho = ctk.CTkLabel(right_frame, text="Họ đệm *", font=ctk.CTkFont(size=12))
        lbl_ho.pack(anchor="w")
        self.fields["HODG"] = ctk.CTkEntry(right_frame, placeholder_text="Ví dụ: Nguyễn Văn", height=35)
        self.fields["HODG"].pack(fill="x", pady=(2, 6))

        # 2. Tên gọi
        lbl_ten = ctk.CTkLabel(right_frame, text="Tên độc giả *", font=ctk.CTkFont(size=12))
        lbl_ten.pack(anchor="w")
        self.fields["TENDG"] = ctk.CTkEntry(right_frame, placeholder_text="Ví dụ: An", height=35)
        self.fields["TENDG"].pack(fill="x", pady=(2, 6))

        # 3. Số CMND / CCCD
        lbl_cmnd = ctk.CTkLabel(right_frame, text="Số CMND / CCCD *", font=ctk.CTkFont(size=12))
        lbl_cmnd.pack(anchor="w")
        self.fields["SOCMND"] = ctk.CTkEntry(right_frame, placeholder_text="12 chữ số CMND/CCCD", height=35)
        self.fields["SOCMND"].pack(fill="x", pady=(2, 6))

        # 4. Giới tính & Ngày sinh
        row_gender_birth = ctk.CTkFrame(right_frame, fg_color="transparent")
        row_gender_birth.pack(fill="x", pady=2)
        row_gender_birth.grid_columnconfigure(0, weight=1)
        row_gender_birth.grid_columnconfigure(1, weight=2)

        lbl_gt = ctk.CTkLabel(row_gender_birth, text="Giới tính", font=ctk.CTkFont(size=12))
        lbl_gt.grid(row=0, column=0, sticky="w")
        self.cb_gender = ctk.CTkComboBox(row_gender_birth, values=["Nam", "Nữ"], height=35, width=90)
        self.cb_gender.set("Nam")
        self.cb_gender.grid(row=1, column=0, padx=(0, 6), sticky="ew")

        lbl_ns = ctk.CTkLabel(row_gender_birth, text="Ngày sinh", font=ctk.CTkFont(size=12))
        lbl_ns.grid(row=0, column=1, sticky="w")
        self.fields["NGAYSINH"] = ctk.CTkEntry(row_gender_birth, placeholder_text="DD/MM/YYYY (VD: 15/05/2002)", height=35)
        self.fields["NGAYSINH"].grid(row=1, column=1, sticky="ew")

        # 5. Số điện thoại
        lbl_dt = ctk.CTkLabel(right_frame, text="Số điện thoại", font=ctk.CTkFont(size=12))
        lbl_dt.pack(anchor="w", pady=(6, 0))
        self.fields["DIENTHOAI"] = ctk.CTkEntry(right_frame, placeholder_text="Ví dụ: 0912345678", height=35)
        self.fields["DIENTHOAI"].pack(fill="x", pady=(2, 6))

        # 6. Địa chỉ Email
        lbl_email = ctk.CTkLabel(right_frame, text="Địa chỉ Email", font=ctk.CTkFont(size=12))
        lbl_email.pack(anchor="w")
        self.fields["EMAILDG"] = ctk.CTkEntry(right_frame, placeholder_text="Ví dụ: docgia@gmail.com", height=35)
        self.fields["EMAILDG"].pack(fill="x", pady=(2, 6))

        # 7. Địa chỉ liên hệ
        lbl_dc = ctk.CTkLabel(right_frame, text="Địa chỉ liên hệ", font=ctk.CTkFont(size=12))
        lbl_dc.pack(anchor="w")
        self.fields["DIACHI"] = ctk.CTkEntry(right_frame, placeholder_text="Số nhà, đường, quận/huyện...", height=35)
        self.fields["DIACHI"].pack(fill="x", pady=(2, 6))

        # 8. Thời hạn cấp thẻ
        lbl_han = ctk.CTkLabel(right_frame, text="Thời hạn thẻ", font=ctk.CTkFont(size=12))
        lbl_han.pack(anchor="w")
        self.cb_duration = ctk.CTkComboBox(
            right_frame, 
            values=["6 tháng", "12 tháng (1 năm)", "24 tháng (2 năm)", "36 tháng (3 năm)"],
            height=35
        )
        self.cb_duration.set("12 tháng (1 năm)")
        self.cb_duration.pack(fill="x", pady=(2, 12))

        # Ghi chú quy tắc
        lbl_note = ctk.CTkLabel(
            right_frame,
            text="Quy định:\n- Ngày làm thẻ tự động lấy ngày hiện tại.\n- Độc giả được mượn tối đa 3 cuốn sách.\n- Thời hạn mượn 30 ngày/lần.",
            font=ctk.CTkFont(size=11),
            text_color="#9CA3AF",
            justify="left"
        )
        lbl_note.pack(anchor="w", pady=(0, 15))

        # Nút hành động
        btn_create = ctk.CTkButton(
            right_frame, 
            text="Xác Nhận Cấp Thẻ", 
            height=40, 
            font=ctk.CTkFont(weight="bold"),
            command=self.handle_add_docgia
        )
        btn_create.pack(fill="x", pady=(0, 8))

        btn_clear = ctk.CTkButton(
            right_frame, 
            text="Làm Mới Form", 
            height=35, 
            fg_color="#4B5563", 
            hover_color="#374151",
            command=self.clear_form
        )
        btn_clear.pack(fill="x", pady=(0, 15))

    def load_data(self):
        """Tải toàn bộ dữ liệu độc giả vào bảng."""
        try:
            records = DocGiaDAO.get_all()
            self.display_records(records)
            self.txt_search.delete(0, "end")
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", f"Không thể tải danh sách độc giả:\n{ex}")

    def display_records(self, records):
        """Xóa dữ liệu cũ và hiển thị các dòng mới lên bảng với định dạng trực quan."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        today = datetime.now().date()

        for idx, r in enumerate(records):
            gender_str = "Nam" if r.get("GIOITINH") == 1 else "Nữ"
            hoten = f"{r.get('HODG', '')} {r.get('TENDG', '')}".strip()
            ngayhethan_str = r.get("NgayHetHan") or ""
            is_active = r.get("HOATDONG") == 1

            # Xác định trạng thái chi tiết
            is_expired = False
            if ngayhethan_str:
                try:
                    exp_date = datetime.strptime(ngayhethan_str, "%d/%m/%Y").date()
                    if exp_date < today:
                        is_expired = True
                except ValueError:
                    pass

            if not is_active:
                status_str = "Đã khóa"
                tag = "locked"
            elif is_expired:
                status_str = "Quá hạn"
                tag = "expired"
            else:
                status_str = "Hoạt động"
                tag = "oddrow" if idx % 2 != 0 else "evenrow"

            self.tree.insert("", "end", values=(
                r.get("MADG"),
                hoten,
                r.get("SOCMND") or "",
                gender_str,
                r.get("DIENTHOAI") or "",
                r.get("EMAILDG") or "",
                r.get("NgayLamThe") or "",
                ngayhethan_str,
                status_str
            ), tags=(tag,))

        self.lbl_count.configure(text=f"Tổng: {len(records)} độc giả")

    def handle_search(self):
        """Tìm kiếm dữ liệu theo từ khóa."""
        keyword = self.txt_search.get().strip()
        if not keyword:
            self.load_data()
            return

        try:
            records = DocGiaDAO.search(keyword)
            self.display_records(records)
        except Exception as ex:
            messagebox.showerror("Lỗi tìm kiếm", str(ex))

    def handle_add_docgia(self):
        """Kiểm tra tính hợp lệ và thêm mới độc giả vào CSDL."""
        ho = self.fields["HODG"].get().strip()
        ten = self.fields["TENDG"].get().strip()
        cmnd = self.fields["SOCMND"].get().strip()
        ngaysinh_str = self.fields["NGAYSINH"].get().strip()
        dienthoai = self.fields["DIENTHOAI"].get().strip()
        email = self.fields["EMAILDG"].get().strip()
        diachi = self.fields["DIACHI"].get().strip()
        gioitinh = 1 if self.cb_gender.get() == "Nam" else 0

        # 1. Kiểm tra trường bắt buộc
        if not ho or not ten:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập đầy đủ Họ đệm và Tên độc giả!")
            return

        if not cmnd:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập số CMND / CCCD!")
            return

        # 2. Kiểm tra trùng CMND/CCCD
        try:
            if DocGiaDAO.check_cmnd_exists(cmnd):
                messagebox.showerror("Trùng lặp", f"Số CMND/CCCD '{cmnd}' đã tồn tại trên hệ thống!")
                return
        except Exception as e:
            messagebox.showerror("Lỗi CSDL", f"Không thể kiểm tra CMND: {e}")
            return

        # 3. Kiểm tra trùng Email
        if email:
            try:
                if DocGiaDAO.check_email_exists(email):
                    messagebox.showerror("Trùng lặp", f"Email '{email}' đã được đăng ký trước đó!")
                    return
            except Exception as e:
                messagebox.showerror("Lỗi CSDL", f"Không thể kiểm tra Email: {e}")
                return

        # 4. Parse Ngày sinh (nếu có nhập)
        ngaysinh = None
        if ngaysinh_str:
            try:
                ngaysinh = datetime.strptime(ngaysinh_str, "%d/%m/%Y")
            except ValueError:
                messagebox.showerror("Sai định dạng", "Ngày sinh phải theo định dạng DD/MM/YYYY (Ví dụ: 15/05/2002)!")
                return

        # 5. Tính ngày làm thẻ và ngày hết hạn
        ngaylamthe = datetime.now()
        duration_map = {
            "6 tháng": 180,
            "12 tháng (1 năm)": 365,
            "24 tháng (2 năm)": 730,
            "36 tháng (3 năm)": 1095
        }
        days = duration_map.get(self.cb_duration.get(), 365)
        ngayhethan = ngaylamthe + timedelta(days=days)

        docgia_data = {
            "HODG": ho,
            "TENDG": ten,
            "SOCMND": cmnd,
            "GIOITINH": gioitinh,
            "NGAYSINH": ngaysinh,
            "DIENTHOAI": dienthoai or None,
            "EMAILDG": email or None,
            "DIACHI": diachi or None,
            "NGAYLAMTHE": ngaylamthe,
            "NGAYHETHAN": ngayhethan,
            "HOATDONG": 1
        }

        try:
            new_id = DocGiaDAO.insert(docgia_data)
            messagebox.showinfo(
                "Thành công", 
                f"Đã cấp thẻ thư viện thành công cho độc giả: {ho} {ten}!\nMã Độc Giả: {new_id}"
            )
            self.clear_form()
            self.load_data()
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", f"Không thể lưu độc giả vào CSDL:\n{ex}")

    def handle_extend_card(self):
        """Gia hạn thẻ thêm 12 tháng cho độc giả đang chọn."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một độc giả trên bảng để gia hạn thẻ!")
            return

        item = self.tree.item(selected[0])
        madg = item["values"][0]
        hoten = item["values"][1]

        confirm = messagebox.askyesno(
            "Xác nhận", 
            f"Bạn có chắc muốn gia hạn thêm 12 tháng cho thẻ độc giả '{hoten}' (Mã: {madg})?"
        )
        if not confirm:
            return

        try:
            success = DocGiaDAO.gia_han_the(madg, so_thang=12)
            if success:
                messagebox.showinfo("Thành công", f"Gia hạn thẻ cho '{hoten}' thành công!")
                self.load_data()
            else:
                messagebox.showerror("Thất bại", "Không tìm thấy thông tin để cập nhật!")
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", str(ex))

    def handle_toggle_status(self):
        """Chuyển đổi trạng thái thẻ Hoạt động <-> Đã khóa."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một độc giả trên bảng để thay đổi trạng thái!")
            return

        item = self.tree.item(selected[0])
        madg = item["values"][0]
        hoten = item["values"][1]
        current_status = item["values"][8]

        is_currently_active = "Hoạt động" in current_status or "Quá hạn" in current_status
        new_status = not is_currently_active
        action_name = "KÍCH HOẠT" if new_status else "KHÓA"

        confirm = messagebox.askyesno(
            "Xác nhận", 
            f"Bạn có muốn {action_name} thẻ độc giả '{hoten}' (Mã: {madg})?"
        )
        if not confirm:
            return

        try:
            success = DocGiaDAO.toggle_trang_thai(madg, new_status)
            if success:
                messagebox.showinfo("Thành công", f"Đã {action_name.lower()} thẻ thành công!")
                self.load_data()
            else:
                messagebox.showerror("Thất bại", "Cập nhật trạng thái không thành công!")
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", str(ex))

    def clear_form(self):
        """Xóa trắng các ô nhập trên form."""
        for field in self.fields.values():
            field.delete(0, "end")
        self.cb_gender.set("Nam")
        self.cb_duration.set("12 tháng (1 năm)")
