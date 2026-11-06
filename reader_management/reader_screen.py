import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import ctk_patch
from datetime import datetime
from typing import Optional, Dict, Any
from reader_management.reader_actions import ReaderActions, DocGiaDAO
from database import CURRENT_SESSION


class ReaderScreen(ctk.CTkFrame):
    """
    Giao diện Quản lý Độc giả (Thẻ thư viện):
    - Hiển thị danh sách độc giả dạng bảng (ttk.Treeview chuẩn Dark Mode đồng bộ).
    - Phân biệt trạng thái: Hoạt động | Quá hạn | Đã khóa.
    - Tìm kiếm theo mã thẻ, Họ tên, CMND, SĐT, Email.
    - Form cấp thẻ mới chống tràn layout, tự động validate dữ liệu.
    - Gia hạn, Khóa / Mở thẻ và cấp lại thẻ bị mất trong một giao dịch.
    """

    def __init__(self, master, current_user: Optional[Dict[str, Any]] = None):
        super().__init__(master, fg_color="transparent")
        self.current_user = current_user or CURRENT_SESSION.get("user_info") or {}
        self.editing_madg: Optional[int] = None

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
            placeholder_text="Nhập Mã ĐG, Tên, CMND/CCCD, SĐT hoặc Email...",
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
        self.tree.bind("<Double-1>", lambda event: self.handle_edit_reader())
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # 4. Thanh thao tác nhanh dưới bảng
        action_bar = ctk.CTkFrame(left_frame, fg_color="transparent")
        action_bar.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="ew")

        self.btn_edit = ctk.CTkButton(
            action_bar,
            text="Sửa thông tin",
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            font=ctk.CTkFont(weight="bold"),
            command=self.handle_edit_reader
        )
        self.btn_edit.pack(side="left", padx=(0, 10))

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
        self.btn_toggle_status.pack(side="left", padx=(0, 10))

        self.btn_replace = ctk.CTkButton(
            action_bar,
            text="Cấp lại thẻ mất",
            fg_color="#DC2626",
            hover_color="#B91C1C",
            font=ctk.CTkFont(weight="bold"),
            command=self.handle_replace_lost_card
        )
        self.btn_replace.pack(side="left")

    def create_right_panel(self):
        # Chiều rộng cố định 340px chống tràn giao diện
        right_frame = ctk.CTkScrollableFrame(self, width=340, corner_radius=12)
        right_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")

        self.lbl_form_title = ctk.CTkLabel(
            right_frame, 
            text="CẤP THẺ ĐỘC GIẢ MỚI", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.lbl_form_title.pack(pady=(15, 12), anchor="w")

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
        self.fields["SOCMND"] = ctk.CTkEntry(right_frame, placeholder_text="9 hoặc 12 chữ số", height=35)
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
        self.btn_submit = ctk.CTkButton(
            right_frame, 
            text="Xác Nhận Cấp Thẻ", 
            height=40, 
            font=ctk.CTkFont(weight="bold"),
            command=self.handle_add_docgia
        )
        self.btn_submit.pack(fill="x", pady=(0, 8))

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
        except ValueError as ve:
            messagebox.showwarning("Cảnh báo", str(ve))
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
        except ValueError as ve:
            messagebox.showwarning("Cảnh báo", str(ve))
        except Exception as ex:
            messagebox.showerror("Lỗi tìm kiếm", str(ex))

    def _read_personal_form(self):
        """Read and parse the personal-information fields shared by create and edit."""
        birth_text = self.fields["NGAYSINH"].get().strip()
        try:
            birth_date = datetime.strptime(birth_text, "%d/%m/%Y") if birth_text else None
        except ValueError as error:
            raise ValueError("Ngày sinh phải theo định dạng DD/MM/YYYY!") from error
        return {
            "HODG": self.fields["HODG"].get(),
            "TENDG": self.fields["TENDG"].get(),
            "SOCMND": self.fields["SOCMND"].get(),
            "GIOITINH": 1 if self.cb_gender.get() == "Nam" else 0,
            "NGAYSINH": birth_date,
            "DIENTHOAI": self.fields["DIENTHOAI"].get(),
            "EMAILDG": self.fields["EMAILDG"].get(),
            "DIACHI": self.fields["DIACHI"].get(),
        }

    def handle_edit_reader(self):
        """Load the selected active reader into the form for a protected update."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn độc giả cần sửa thông tin!")
            return

        values = self.tree.item(selected[0])["values"]
        madg, current_status = int(values[0]), values[8]
        if current_status == "Đã khóa":
            messagebox.showwarning(
                "Dữ liệu lịch sử",
                "Không thể sửa thẻ đã khóa. Hãy chọn thẻ đang hoạt động của độc giả."
            )
            return

        try:
            reader = DocGiaDAO.get_by_id(madg)
            if not reader:
                raise ValueError(f"Không tìm thấy thẻ độc giả mã {madg}!")
            if not reader.get("HOATDONG"):
                raise ValueError("Thẻ vừa bị khóa; vui lòng làm mới danh sách!")

            self.clear_form()
            self.editing_madg = madg
            for field_name in ("HODG", "TENDG", "SOCMND", "DIENTHOAI", "EMAILDG", "DIACHI"):
                value = reader.get(field_name)
                if value is not None:
                    self.fields[field_name].insert(0, str(value))
            birth_date = reader.get("NGAYSINH")
            if birth_date:
                self.fields["NGAYSINH"].insert(0, birth_date.strftime("%d/%m/%Y"))
            self.cb_gender.set("Nam" if reader.get("GIOITINH") == 1 else "Nữ")
            self.cb_duration.configure(state="disabled")
            self.lbl_form_title.configure(text=f"CẬP NHẬT ĐỘC GIẢ - MÃ {madg}")
            self.btn_submit.configure(
                text="Lưu Cập Nhật",
                command=self.handle_update_docgia,
                fg_color="#059669",
                hover_color="#047857"
            )
            self.fields["HODG"].focus_set()
        except ValueError as error:
            messagebox.showwarning("Không thể cập nhật", str(error))
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", f"Không thể tải thông tin độc giả:\n{error}")

    def handle_update_docgia(self):
        """Save editable personal details without changing card-history fields."""
        if self.editing_madg is None:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn độc giả cần cập nhật!")
            return

        try:
            reader_data = self._read_personal_form()
            confirmed = messagebox.askyesno(
                "Xác nhận cập nhật",
                f"Lưu thay đổi thông tin cho thẻ độc giả mã {self.editing_madg}?\n\n"
                "Mã thẻ, ngày làm thẻ, ngày hết hạn và trạng thái sẽ không bị thay đổi."
            )
            if not confirmed:
                return

            updated = DocGiaDAO.update(self.editing_madg, reader_data)
            if not updated:
                raise ValueError("Không có dữ liệu nào được cập nhật!")
            messagebox.showinfo(
                "Cập nhật thành công",
                f"Đã cập nhật thông tin độc giả mã {self.editing_madg}."
            )
            self.clear_form()
            self.load_data()
        except ValueError as error:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(error))
        except PermissionError as error:
            messagebox.showerror("Không đủ quyền", str(error))
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", f"Không thể cập nhật độc giả:\n{error}")

    def handle_add_docgia(self):
        """Validate the form and issue a new library card."""
        try:
            personal_data = self._read_personal_form()
            duration_months = {
                "6 tháng": 6,
                "12 tháng (1 năm)": 12,
                "24 tháng (2 năm)": 24,
                "36 tháng (3 năm)": 36,
            }.get(self.cb_duration.get(), 12)
            issue_date = datetime.now()
            reader_data = DocGiaDAO.validate_reader_data({
                **personal_data,
                "NGAYLAMTHE": issue_date,
                "NGAYHETHAN": DocGiaDAO.add_months(issue_date, duration_months),
                "HOATDONG": 1,
            })

            if DocGiaDAO.check_cmnd_exists(reader_data["SOCMND"]):
                raise ValueError("CMND/CCCD này đã có một thẻ đang hoạt động!")
            if reader_data["EMAILDG"] and DocGiaDAO.check_email_exists(reader_data["EMAILDG"]):
                raise ValueError("Email này đã được đăng ký cho một thẻ đang hoạt động!")

            new_id = DocGiaDAO.insert(reader_data)
            messagebox.showinfo(
                "Thành công",
                f"Đã cấp thẻ cho {reader_data['HODG']} {reader_data['TENDG']}.\n"
                f"Mã độc giả mới: {new_id}"
            )
            self.clear_form()
            self.load_data()
        except ValueError as error:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(error))
        except PermissionError as error:
            messagebox.showerror("Không đủ quyền", str(error))
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", f"Không thể cấp thẻ độc giả:\n{error}")

    def handle_extend_card(self):
        """Gia hạn thẻ thêm 12 tháng cho độc giả đang chọn."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một độc giả trên bảng để gia hạn thẻ!")
            return

        item = self.tree.item(selected[0])
        madg = item["values"][0]
        hoten = item["values"][1]
        current_status = item["values"][8]

        if current_status == "Đã khóa":
            messagebox.showwarning(
                "Thẻ đã khóa",
                "Không thể gia hạn một thẻ đã khóa. Hãy chọn thẻ đang hoạt động của độc giả."
            )
            return

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
        except ValueError as ve:
            messagebox.showwarning("Cảnh báo", str(ve))
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", str(ex))

    def handle_replace_lost_card(self):
        """Lock the selected lost card and issue a new card atomically."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn thẻ bị mất cần cấp lại!")
            return

        item = self.tree.item(selected[0])
        values = item["values"]
        old_madg, hoten, current_status = values[0], values[1], values[8]
        if current_status == "Đã khóa":
            messagebox.showwarning(
                "Thẻ đã khóa",
                "Thẻ này đã bị khóa và không thể cấp lại lần nữa. Hãy chọn thẻ đang hoạt động."
            )
            return

        confirmed = messagebox.askyesno(
            "Xác nhận cấp lại thẻ mất",
            f"Cấp lại thẻ cho '{hoten}' (mã cũ: {old_madg})?\n\n"
            "Thẻ cũ sẽ bị khóa, một mã độc giả mới sẽ được tạo và lịch sử cũ vẫn được giữ. "
            "Các sách chưa trả trên thẻ cũ vẫn được tính vào giới hạn 3 cuốn."
        )
        if not confirmed:
            return

        try:
            new_madg = DocGiaDAO.cap_lai_the_mat(old_madg, so_thang=12)
            messagebox.showinfo(
                "Cấp lại thẻ thành công",
                f"Đã khóa thẻ cũ {old_madg} và cấp thẻ mới {new_madg} cho '{hoten}'."
            )
            self.load_data()
        except ValueError as error:
            messagebox.showwarning("Không thể cấp lại thẻ", str(error))
        except PermissionError as error:
            messagebox.showerror("Không đủ quyền", str(error))
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", f"Không thể cấp lại thẻ:\n{error}")

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
        except ValueError as ve:
            messagebox.showwarning("Cảnh báo", str(ve))
        except Exception as ex:
            messagebox.showerror("Lỗi CSDL", str(ex))

    def clear_form(self):
        """Xóa trắng các ô nhập trên form và khôi phục placeholder."""
        self.editing_madg = None
        self.focus_set()
        for field in self.fields.values():
            field.delete(0, "end")
        self.cb_gender.set("Nam")
        self.cb_duration.configure(state="normal")
        self.cb_duration.set("12 tháng (1 năm)")
        self.lbl_form_title.configure(text="CẤP THẺ ĐỘC GIẢ MỚI")
        self.btn_submit.configure(
            text="Xác Nhận Cấp Thẻ",
            command=self.handle_add_docgia,
            fg_color="#3B8ED0",
            hover_color="#36719F"
        )


# Bí danh tương thích
TabDocGia = ReaderScreen
