"""Reader (library card) management screen.

State machine (ui_state.FormStateController):
    VIEW : all inputs LOCKED; Thêm / Sửa / Xóa / Thoát ON; Ghi / Phục hồi OFF.
           Selecting a row shows it in the locked form.
    ADD  : inputs unlocked & cleared, focus "Họ đệm"; MADG shows "(tự động)" (IDENTITY).
    EDIT : inputs unlocked EXCEPT the primary key MADG and the card term.
    Ghi  : INSERT / UPDATE via parameterized queries -> reload grid -> back to VIEW.
    Phục hồi: discard changes, show the selected row's original data, back to VIEW.
    Xóa  : confirmation dialog, deletes immediately; FK error 547 -> friendly message.
"""

from datetime import datetime
from tkinter import messagebox, ttk
from typing import Any, Dict, Optional

import customtkinter as ctk

import ctk_patch  # noqa: F401  (placeholder fix for CTkEntry)
from database import CURRENT_SESSION
from reader_management.reader_actions import DocGiaDAO
from ui_state import FormMode, FormStateController, build_command_bar, confirm_exit

AUTO_ID = "(tự động)"
DURATIONS = {"6 tháng": 6, "12 tháng (1 năm)": 12, "24 tháng (2 năm)": 24, "36 tháng (3 năm)": 36}


class ReaderScreen(ctk.CTkFrame):
    """Danh sách độc giả + form Thêm / Sửa / Xóa / Ghi / Phục hồi."""

    def __init__(self, master, current_user: Optional[Dict[str, Any]] = None):
        super().__init__(master, fg_color="transparent")
        self.current_user = current_user or CURRENT_SESSION.get("user_info") or {}
        self.records: Dict[str, Dict[str, Any]] = {}
        self.setup_ui()
        self.load_data()

    # ------------------------------------------------------------------ UI
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)
        self.create_right_panel()      # form first: the command bar needs its widgets
        self.create_left_panel()
        self.state.to_view()

    def create_left_panel(self):
        left = ctk.CTkFrame(self, corner_radius=12)
        left.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(left, fg_color="transparent")
        header.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        ctk.CTkLabel(header, text="DANH SÁCH ĐỘC GIẢ THƯ VIỆN",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        self.lbl_count = ctk.CTkLabel(header, text="Tổng: 0 độc giả", font=ctk.CTkFont(size=13),
                                      text_color="#9CA3AF")
        self.lbl_count.pack(side="right")

        search = ctk.CTkFrame(left, fg_color="transparent")
        search.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="ew")
        search.grid_columnconfigure(0, weight=1)
        self.txt_search = ctk.CTkEntry(search, height=36,
                                       placeholder_text="Nhập Mã ĐG, Tên, CMND/CCCD, SĐT hoặc Email...")
        self.txt_search.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.txt_search.bind("<Return>", lambda e: self.handle_search())
        self.btn_search = ctk.CTkButton(search, text="Tìm kiếm", width=90, height=36,
                                        command=self.handle_search)
        self.btn_search.grid(row=0, column=1, padx=(0, 6))
        self.btn_refresh = ctk.CTkButton(search, text="Làm mới", width=80, height=36,
                                         fg_color="#4B5563", hover_color="#374151",
                                         command=self.load_data)
        self.btn_refresh.grid(row=0, column=2)

        tree_box = ctk.CTkFrame(left, fg_color="#1E2229", corner_radius=8)
        tree_box.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="nsew")
        tree_box.grid_rowconfigure(0, weight=1)
        tree_box.grid_columnconfigure(0, weight=1)
        self._apply_tree_style()

        columns = ("MADG", "HoTen", "SOCMND", "GIOITINH", "DIENTHOAI", "EMAILDG",
                   "NGAYLAMTHE", "NGAYHETHAN", "HOATDONG")
        self.tree = ttk.Treeview(tree_box, columns=columns, show="headings", selectmode="browse")
        for col, (heading, width, align) in {
            "MADG": ("Mã ĐG", 55, "center"), "HoTen": ("Họ và Tên", 135, "w"),
            "SOCMND": ("Số CMND/CCCD", 105, "center"), "GIOITINH": ("Giới tính", 65, "center"),
            "DIENTHOAI": ("Điện thoại", 95, "center"), "EMAILDG": ("Email", 135, "w"),
            "NGAYLAMTHE": ("Ngày làm thẻ", 88, "center"), "NGAYHETHAN": ("Ngày hết hạn", 88, "center"),
            "HOATDONG": ("Trạng thái", 100, "center"),
        }.items():
            self.tree.heading(col, text=heading, anchor=align)
            self.tree.column(col, width=width, minwidth=40, anchor=align)
        self.tree.tag_configure("oddrow", background="#1E2229", foreground="#F3F4F6")
        self.tree.tag_configure("evenrow", background="#242830", foreground="#F3F4F6")
        self.tree.tag_configure("locked", background="#382226", foreground="#F87171")
        self.tree.tag_configure("expired", background="#383020", foreground="#FBBF24")
        vsb = ttk.Scrollbar(tree_box, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_box, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Standard command bar: Thêm / Sửa / Xóa / Ghi / Phục hồi / Thoát
        command_bar = ctk.CTkFrame(left, fg_color="transparent")
        command_bar.grid(row=3, column=0, padx=15, pady=(0, 6), sticky="ew")
        self.buttons = build_command_bar(command_bar, {
            "add": self.on_add, "edit": self.on_edit, "delete": self.on_delete,
            "save": self.on_save, "cancel": self.on_cancel, "exit": lambda: confirm_exit(self),
        })

        # Card-specific business actions (usable only while viewing)
        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.grid(row=4, column=0, padx=15, pady=(0, 15), sticky="ew")
        self.btn_extend = ctk.CTkButton(actions, text="Gia hạn thẻ (+12 tháng)", fg_color="#059669",
                                        hover_color="#047857", command=self.handle_extend_card)
        self.btn_extend.pack(side="left", padx=(0, 8))
        self.btn_toggle_status = ctk.CTkButton(actions, text="Khóa / Mở thẻ", fg_color="#B45309",
                                               hover_color="#92400E", command=self.handle_toggle_status)
        self.btn_toggle_status.pack(side="left", padx=(0, 8))
        self.btn_replace = ctk.CTkButton(actions, text="Cấp lại thẻ mất", fg_color="#9F1239",
                                         hover_color="#881337", command=self.handle_replace_lost_card)
        self.btn_replace.pack(side="left")

        self.state.buttons = self.buttons
        self.state.view_only_widgets = [self.btn_extend, self.btn_toggle_status, self.btn_replace,
                                        self.btn_search, self.btn_refresh, self.txt_search]

    def _apply_tree_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#1E2229", foreground="#F3F4F6",
                        fieldbackground="#1E2229", rowheight=30, borderwidth=0, relief="flat",
                        font=("Segoe UI", 10))
        style.map("Treeview", background=[("selected", "#2563EB")], foreground=[("selected", "#FFFFFF")],
                  fieldbackground=[("!disabled", "#1E2229"), ("disabled", "#1E2229")])
        style.configure("Treeview.Heading", background="#111827", foreground="#F9FAFB", relief="flat",
                        borderwidth=0, font=("Segoe UI", 10, "bold"), padding=(5, 6))
        style.map("Treeview.Heading", background=[("active", "#1F2937"), ("!active", "#111827")],
                  foreground=[("active", "#FFFFFF"), ("!active", "#F9FAFB")])

    def create_right_panel(self):
        right = ctk.CTkScrollableFrame(self, width=340, corner_radius=12)
        right.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")

        self.lbl_form_title = ctk.CTkLabel(right, text="THÔNG TIN ĐỘC GIẢ",
                                           font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_form_title.pack(pady=(15, 4), anchor="w")
        self.lbl_mode = ctk.CTkLabel(right, text="", font=ctk.CTkFont(size=12), anchor="w",
                                     justify="left", wraplength=320)
        self.lbl_mode.pack(anchor="w", pady=(0, 8))

        self.fields: Dict[str, Any] = {}

        def entry(key: str, label: str, placeholder: str = ""):
            ctk.CTkLabel(right, text=label, font=ctk.CTkFont(size=12)).pack(anchor="w")
            self.fields[key] = ctk.CTkEntry(right, placeholder_text=placeholder, height=34)
            self.fields[key].pack(fill="x", pady=(2, 6))

        entry("MADG", "Mã độc giả (khóa chính)")
        entry("HODG", "Họ đệm *", "Ví dụ: Nguyễn Văn")
        entry("TENDG", "Tên độc giả *", "Ví dụ: An")
        entry("SOCMND", "Số CMND / CCCD *", "9 hoặc 12 chữ số")

        row = ctk.CTkFrame(right, fg_color="transparent")
        row.pack(fill="x", pady=2)
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=2)
        ctk.CTkLabel(row, text="Giới tính", font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w")
        self.fields["GIOITINH"] = ctk.CTkComboBox(row, values=["Nam", "Nữ"], height=34, width=90)
        self.fields["GIOITINH"].grid(row=1, column=0, padx=(0, 6), sticky="ew")
        ctk.CTkLabel(row, text="Ngày sinh (dd/MM/yyyy)", font=ctk.CTkFont(size=12)).grid(
            row=0, column=1, sticky="w")
        self.fields["NGAYSINH"] = ctk.CTkEntry(row, placeholder_text="VD: 15/05/2002", height=34)
        self.fields["NGAYSINH"].grid(row=1, column=1, sticky="ew")

        ctk.CTkLabel(right, text="", height=4).pack()
        entry("DIENTHOAI", "Số điện thoại", "Ví dụ: 0912345678")
        entry("EMAILDG", "Địa chỉ Email", "Ví dụ: docgia@gmail.com")
        entry("DIACHI", "Địa chỉ liên hệ", "Số nhà, đường, quận/huyện...")

        ctk.CTkLabel(right, text="Thời hạn thẻ (chỉ khi cấp mới)", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.fields["THOIHAN"] = ctk.CTkComboBox(right, values=list(DURATIONS), height=34)
        self.fields["THOIHAN"].pack(fill="x", pady=(2, 10))

        ctk.CTkLabel(right, justify="left", text_color="#9CA3AF", font=ctk.CTkFont(size=11),
                     text="Quy định:\n- Ngày làm thẻ tự động lấy ngày hiện tại.\n"
                          "- Độc giả được mượn tối đa 3 cuốn sách.\n- Thời hạn mượn 30 ngày/lần.").pack(
            anchor="w", pady=(0, 15))

        self.state = FormStateController(
            inputs=self.fields,
            buttons={},                        # filled in create_left_panel
            key_fields=("MADG", "THOIHAN"),    # PK + card term cannot change when editing
            locked_always=("MADG",),           # IDENTITY: never typed by the user
            defaults={"MADG": AUTO_ID, "GIOITINH": "Nam", "THOIHAN": "12 tháng (1 năm)"},
            on_mode_change=self._on_mode_change,
        )

    def _on_mode_change(self, mode: FormMode) -> None:
        # The grid is frozen while adding/editing so the form cannot jump to another row.
        self.tree.configure(selectmode="browse" if mode is FormMode.VIEW else "none")
        self.lbl_mode.configure(**{
            FormMode.VIEW: {"text": "Chế độ xem — chọn một dòng để xem chi tiết.", "text_color": "#9CA3AF"},
            FormMode.ADD: {"text": "ĐANG THÊM độc giả mới — Ghi để lưu, Phục hồi để hủy.",
                           "text_color": "#60A5FA"},
            FormMode.EDIT: {"text": "ĐANG SỬA — mã độc giả (khóa chính) bị khóa. Ghi để lưu, "
                                    "Phục hồi để hủy.", "text_color": "#A78BFA"},
        }[mode])

    # ---------------------------------------------------------------- data
    def load_data(self):
        """Reload all readers (also used after every successful Ghi / Xóa)."""
        try:
            self.display_records(DocGiaDAO.get_all())
            self.txt_search.delete(0, "end")
        except ValueError as error:
            messagebox.showwarning("Cảnh báo", str(error))
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", f"Không thể tải danh sách độc giả:\n{error}")

    def display_records(self, records):
        self.tree.delete(*self.tree.get_children())
        self.records.clear()
        today = datetime.now().date()
        for idx, r in enumerate(records):
            iid = str(r.get("MADG"))
            if self.tree.exists(iid):
                continue
            expiry = r.get("NgayHetHan") or ""
            expired = False
            if expiry:
                try:
                    expired = datetime.strptime(expiry, "%d/%m/%Y").date() < today
                except ValueError:
                    expired = False
            if r.get("HOATDONG") != 1:
                status, tag = "Đã khóa", "locked"
            elif expired:
                status, tag = "Quá hạn", "expired"
            else:
                status, tag = "Hoạt động", ("oddrow" if idx % 2 else "evenrow")
            self.records[iid] = r
            self.tree.insert("", "end", iid=iid, tags=(tag,), values=(
                r.get("MADG"), f"{r.get('HODG', '')} {r.get('TENDG', '')}".strip(),
                r.get("SOCMND") or "", "Nam" if r.get("GIOITINH") == 1 else "Nữ",
                r.get("DIENTHOAI") or "", r.get("EMAILDG") or "", r.get("NgayLamThe") or "",
                expiry, status,
            ))
        self.lbl_count.configure(text=f"Tổng: {len(self.records)} độc giả")
        self.state.clear()
        self.state.to_view()

    def handle_search(self):
        keyword = self.txt_search.get().strip()
        if not keyword:
            self.load_data()
            return
        try:
            self.display_records(DocGiaDAO.search(keyword))
        except ValueError as error:
            messagebox.showwarning("Cảnh báo", str(error))
        except Exception as error:
            messagebox.showerror("Lỗi tìm kiếm", str(error))

    def _selected(self) -> Optional[Dict[str, Any]]:
        selection = self.tree.selection()
        return self.records.get(selection[0]) if selection else None

    def _record_to_form(self, r: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "MADG": r.get("MADG"), "HODG": r.get("HODG"), "TENDG": r.get("TENDG"),
            "SOCMND": r.get("SOCMND"), "GIOITINH": "Nam" if r.get("GIOITINH") == 1 else "Nữ",
            "NGAYSINH": r.get("NgaySinh") or "", "DIENTHOAI": r.get("DIENTHOAI"),
            "EMAILDG": r.get("EMAILDG"), "DIACHI": r.get("DIACHI"), "THOIHAN": "",
        }

    def _on_select(self, _event=None):
        if self.state.is_editing:
            return
        record = self._selected()
        if record:
            self.state.fill(self._record_to_form(record))

    def _read_form(self) -> Dict[str, Any]:
        """Collect form values (already strip()-ed by the controller) for the DAO."""
        values = self.state.values()
        birth_text = values["NGAYSINH"]
        try:
            birth_date = datetime.strptime(birth_text, "%d/%m/%Y") if birth_text else None
        except ValueError as error:
            raise ValueError("Ngày sinh phải theo định dạng dd/MM/yyyy (VD: 15/05/2002)!") from error
        return {
            "HODG": values["HODG"], "TENDG": values["TENDG"], "SOCMND": values["SOCMND"],
            "GIOITINH": 1 if values["GIOITINH"] == "Nam" else 0, "NGAYSINH": birth_date,
            "DIENTHOAI": values["DIENTHOAI"], "EMAILDG": values["EMAILDG"], "DIACHI": values["DIACHI"],
        }

    # ------------------------------------------------------------ commands
    def on_add(self):
        self.state.to_add()

    def on_edit(self):
        record = self._selected()
        if not record:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn độc giả cần sửa!")
            return
        if record.get("HOATDONG") != 1:
            messagebox.showwarning("Dữ liệu lịch sử",
                                   "Không thể sửa thẻ đã khóa. Hãy chọn thẻ đang hoạt động của độc giả.")
            return
        self.state.to_edit()

    def on_save(self):
        """'Ghi': INSERT (Thêm) or UPDATE (Sửa), then reload and lock the form."""
        try:
            data = self._read_form()
            if self.state.mode is FormMode.ADD:
                months = DURATIONS.get(self.state.values()["THOIHAN"], 12)
                issue = datetime.now()
                data = DocGiaDAO.validate_reader_data({
                    **data, "NGAYLAMTHE": issue,
                    "NGAYHETHAN": DocGiaDAO.add_months(issue, months), "HOATDONG": 1,
                })
                if DocGiaDAO.check_cmnd_exists(data["SOCMND"]):
                    raise ValueError("CMND/CCCD này đã có một thẻ đang hoạt động!")
                if data["EMAILDG"] and DocGiaDAO.check_email_exists(data["EMAILDG"]):
                    raise ValueError("Email này đã được đăng ký cho một thẻ đang hoạt động!")
                new_id = DocGiaDAO.insert(data)
                message, select_id = f"Đã cấp thẻ mới, mã độc giả: {new_id}.", new_id
            elif self.state.mode is FormMode.EDIT:
                madg = int(self.state.values()["MADG"])
                DocGiaDAO.update(madg, data)
                message, select_id = f"Đã cập nhật độc giả mã {madg}.", madg
            else:
                return
        except ValueError as error:
            messagebox.showwarning("Dữ liệu không hợp lệ", str(error))   # form stays open
            return
        except PermissionError as error:
            messagebox.showerror("Không đủ quyền", str(error))
            return
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", f"Không thể ghi độc giả:\n{error}")
            return
        messagebox.showinfo("Thành công", message)
        self.load_data()                       # reload grid -> VIEW state, inputs locked
        self._select_id(select_id)

    def on_cancel(self):
        """'Phục hồi': drop pending changes and show the selected row again."""
        self.state.cancel()
        self._on_select()

    def on_delete(self):
        record = self._selected()
        if not record:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn độc giả cần xóa!")
            return
        name = f"{record.get('HODG', '')} {record.get('TENDG', '')}".strip()
        if not messagebox.askyesno(
            "Xác nhận xóa",
            f"Bạn có chắc chắn muốn xóa bản ghi này không?\n\nĐộc giả: {name} (Mã: {record['MADG']})",
            icon="warning",
        ):
            return
        try:
            DocGiaDAO.delete(record["MADG"])   # deletes immediately, no extra Ghi
        except ValueError as error:            # includes FK 547 -> friendly message
            messagebox.showerror("Không thể xóa", str(error))
            return
        except PermissionError as error:
            messagebox.showerror("Không đủ quyền", str(error))
            return
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", f"Không thể xóa độc giả:\n{error}")
            return
        messagebox.showinfo("Thành công", f"Đã xóa độc giả '{name}'.")
        self.load_data()

    def _select_id(self, madg: Any) -> None:
        iid = str(madg)
        if self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.see(iid)

    # ---------------------------------------------------- card operations
    def _selected_active(self, action: str) -> Optional[Dict[str, Any]]:
        record = self._selected()
        if not record:
            messagebox.showwarning("Chưa chọn", f"Vui lòng chọn một độc giả trên bảng để {action}!")
            return None
        return record

    def handle_extend_card(self):
        record = self._selected_active("gia hạn thẻ")
        if not record:
            return
        if record.get("HOATDONG") != 1:
            messagebox.showwarning("Thẻ đã khóa", "Không thể gia hạn một thẻ đã khóa.")
            return
        name = f"{record['HODG']} {record['TENDG']}"
        if not messagebox.askyesno("Xác nhận",
                                   f"Gia hạn thêm 12 tháng cho thẻ '{name}' (Mã: {record['MADG']})?"):
            return
        try:
            if DocGiaDAO.gia_han_the(record["MADG"], so_thang=12):
                messagebox.showinfo("Thành công", f"Gia hạn thẻ cho '{name}' thành công!")
                self.load_data()
                self._select_id(record["MADG"])
            else:
                messagebox.showerror("Thất bại", "Không tìm thấy thông tin để cập nhật!")
        except ValueError as error:
            messagebox.showwarning("Cảnh báo", str(error))
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", str(error))

    def handle_replace_lost_card(self):
        record = self._selected_active("cấp lại thẻ")
        if not record:
            return
        if record.get("HOATDONG") != 1:
            messagebox.showwarning("Thẻ đã khóa", "Thẻ này đã bị khóa và không thể cấp lại lần nữa.")
            return
        name = f"{record['HODG']} {record['TENDG']}"
        if not messagebox.askyesno(
            "Xác nhận cấp lại thẻ mất",
            f"Cấp lại thẻ cho '{name}' (mã cũ: {record['MADG']})?\n\n"
            "Thẻ cũ sẽ bị khóa, một mã độc giả mới sẽ được tạo và lịch sử cũ vẫn được giữ.",
        ):
            return
        try:
            new_madg = DocGiaDAO.cap_lai_the_mat(record["MADG"], so_thang=12)
            messagebox.showinfo("Cấp lại thẻ thành công",
                                f"Đã khóa thẻ cũ {record['MADG']} và cấp thẻ mới {new_madg} cho '{name}'.")
            self.load_data()
            self._select_id(new_madg)
        except ValueError as error:
            messagebox.showwarning("Không thể cấp lại thẻ", str(error))
        except PermissionError as error:
            messagebox.showerror("Không đủ quyền", str(error))
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", f"Không thể cấp lại thẻ:\n{error}")

    def handle_toggle_status(self):
        record = self._selected_active("thay đổi trạng thái")
        if not record:
            return
        new_status = record.get("HOATDONG") != 1
        action = "KÍCH HOẠT" if new_status else "KHÓA"
        name = f"{record['HODG']} {record['TENDG']}"
        if not messagebox.askyesno("Xác nhận", f"Bạn có muốn {action} thẻ độc giả '{name}' "
                                               f"(Mã: {record['MADG']})?"):
            return
        try:
            if DocGiaDAO.toggle_trang_thai(record["MADG"], new_status):
                messagebox.showinfo("Thành công", f"Đã {action.lower()} thẻ thành công!")
                self.load_data()
                self._select_id(record["MADG"])
            else:
                messagebox.showerror("Thất bại", "Cập nhật trạng thái không thành công!")
        except ValueError as error:
            messagebox.showwarning("Cảnh báo", str(error))
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", str(error))

    def clear_form(self):
        """Backward-compatible helper: empty the form and return to VIEW."""
        self.state.clear()
        self.state.to_view()


# Bí danh tương thích
TabDocGia = ReaderScreen
