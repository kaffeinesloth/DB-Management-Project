"""Book management screen: physical copies (SACH) and titles (ISBN).

Two forms share ONE command bar (Thêm / Sửa / Xóa / Ghi / Phục hồi / Thoát); a selector
chooses which entity the commands act on. Each form has its own state machine:
    VIEW : inputs LOCKED, Ghi / Phục hồi OFF.
    ADD  : unlocked + cleared, focus first field.
    EDIT : unlocked EXCEPT the primary key (MASACH or ISBN).
Xóa: confirmation, immediate delete, FK error 547 -> friendly message.
Only QUANLY may change the catalogue (SQL Server permissions enforce it too).
"""

from tkinter import messagebox, ttk
from typing import Any, Dict, Optional

import customtkinter as ctk

import ctk_patch  # noqa: F401
from book_management.book_actions import SachDAO
from database import CURRENT_SESSION
from ui_state import FormMode, FormStateController, build_command_bar, confirm_exit

ENTITY_COPY = "Cuốn sách (SACH)"
ENTITY_TITLE = "Đầu sách (ISBN)"
CONDITIONS = {"Tốt": 1, "Hư hỏng": 0}

COPY_TREE_SPEC = (
    ("MASACH", "Mã Sách", 75, "center"),
    ("ISBN", "ISBN", 85, "center"),
    ("TENSACH", "Tên Đầu Sách", 180, "w"),
    ("THELOAI", "Thể Loại", 110, "w"),
    ("HOTENTG", "Tác Giả", 120, "w"),
    ("ViTri", "Vị Trí Kệ", 110, "center"),
    ("GiaBia", "Giá Bìa (VNĐ)", 95, "e"),
    ("TINHTRANG", "Tình Trạng", 90, "center"),
    ("CHOMUON", "Cho Mượn", 95, "center"),
)

TITLE_TREE_SPEC = (
    ("ISBN", "ISBN", 90, "center"),
    ("TENSACH", "Tên Đầu Sách", 185, "w"),
    ("THELOAI", "Thể Loại", 110, "w"),
    ("HOTENTG", "Tác Giả", 125, "w"),
    ("NGONNGU", "Ngôn Ngữ", 85, "center"),
    ("NHAXB", "Nhà Xuất Bản", 120, "w"),
    ("GiaBia", "Giá Bìa (VNĐ)", 95, "e"),
    ("TongBanSao", "Tổng Cuốn", 80, "center"),
    ("BanSaoKhaDung", "Sẵn Có", 75, "center"),
)


class BookScreen(ctk.CTkFrame):
    """Danh mục sách + form Thêm / Sửa / Xóa / Ghi / Phục hồi."""

    def __init__(self, master, current_user: Optional[Dict[str, Any]] = None):
        super().__init__(master, fg_color="transparent")
        self.current_user = current_user or CURRENT_SESSION.get("user_info") or {}
        self.is_manager = (self.current_user.get("RoleName") or "").upper() == "QUANLY"
        self.records: Dict[str, Dict[str, Any]] = {}
        self.maps: Dict[str, Dict[str, Any]] = {k: {} for k in ("isbn", "ngantu", "tl", "tg", "nn")}
        self.forms: Dict[str, FormStateController] = {}
        self.entity = ENTITY_COPY
        self.setup_ui()
        self.load_data()

    # ------------------------------------------------------------------ UI
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)
        self.create_left_panel()
        self.create_right_panel()
        for form in self.forms.values():
            form.to_view()

    def create_left_panel(self):
        left = ctk.CTkFrame(self, corner_radius=12)
        left.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(left, fg_color="transparent")
        header.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        self.lbl_header = ctk.CTkLabel(header, text="DANH MỤC CUỐN SÁCH THƯ VIỆN",
                                       font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl_header.pack(side="left")
        self.lbl_count = ctk.CTkLabel(header, text="Tổng: 0 cuốn sách", font=ctk.CTkFont(size=13),
                                      text_color="#9CA3AF")
        self.lbl_count.pack(side="right")

        search = ctk.CTkFrame(left, fg_color="transparent")
        search.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="ew")
        search.grid_columnconfigure(0, weight=1)
        self.txt_search = ctk.CTkEntry(search, height=36,
                                       placeholder_text="Nhập Tên sách, Mã sách, ISBN, Thể loại hoặc Tác giả...")
        self.txt_search.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.txt_search.bind("<Return>", lambda e: self.handle_search())
        self.btn_search = ctk.CTkButton(search, text="Tìm kiếm", width=90, height=36,
                                        command=self.handle_search)
        self.btn_search.grid(row=0, column=1, padx=(0, 6))
        self.btn_refresh = ctk.CTkButton(search, text="Làm mới", width=80, height=36,
                                         fg_color="#4B5563", hover_color="#374151", command=self.load_data)
        self.btn_refresh.grid(row=0, column=2)

        tree_box = ctk.CTkFrame(left, fg_color="#1E2229", corner_radius=8)
        tree_box.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="nsew")
        tree_box.grid_rowconfigure(0, weight=1)
        tree_box.grid_columnconfigure(0, weight=1)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#1E2229", foreground="#F3F4F6", fieldbackground="#1E2229",
                        rowheight=30, borderwidth=0, relief="flat", font=("Segoe UI", 10))
        style.map("Treeview", background=[("selected", "#2563EB")], foreground=[("selected", "#FFFFFF")])
        style.configure("Treeview.Heading", background="#111827", foreground="#F9FAFB", relief="flat",
                        borderwidth=0, font=("Segoe UI", 10, "bold"), padding=(5, 6))

        columns = [col for col, *_ in COPY_TREE_SPEC]
        self.tree = ttk.Treeview(tree_box, columns=columns, show="headings", selectmode="browse")
        self._configure_tree_columns()
        self.tree.tag_configure("oddrow", background="#1E2229", foreground="#F3F4F6")
        self.tree.tag_configure("evenrow", background="#242830", foreground="#F3F4F6")
        self.tree.tag_configure("borrowed", background="#332B1A", foreground="#FBBF24")
        self.tree.tag_configure("damaged", background="#382226", foreground="#F87171")
        self.tree.tag_configure("empty_copies", background="#1E293B", foreground="#93C5FD")
        vsb = ttk.Scrollbar(tree_box, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_box, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        bar = ctk.CTkFrame(left, fg_color="transparent")
        bar.grid(row=3, column=0, padx=15, pady=(0, 6), sticky="ew")
        handlers = {"exit": lambda: confirm_exit(self)}
        if self.is_manager:
            handlers = {"add": self.on_add, "edit": self.on_edit, "delete": self.on_delete,
                        "save": self.on_save, "cancel": self.on_cancel, **handlers}
        self.buttons = build_command_bar(bar, handlers)

        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.grid(row=4, column=0, padx=15, pady=(0, 15), sticky="ew")
        self.btn_toggle_status = None
        if (self.current_user.get("RoleName") or "").upper() in ("QUANLY", "THUTHU"):
            self.btn_toggle_status = ctk.CTkButton(
                actions, text="Báo Hỏng / Khôi Phục Sách", fg_color="#B45309", hover_color="#92400E",
                command=self.handle_toggle_tinh_trang)
            self.btn_toggle_status.pack(side="left")

    def create_right_panel(self):
        right = ctk.CTkScrollableFrame(self, width=340, corner_radius=12)
        right.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        ctk.CTkLabel(right, text="THÔNG TIN SÁCH", font=ctk.CTkFont(size=16, weight="bold")).pack(
            pady=(15, 8), anchor="w")

        if not self.is_manager:
            card = ctk.CTkFrame(right, fg_color=("#E2E8F0", "#1F2937"), corner_radius=10)
            card.pack(fill="x", pady=20, padx=5)
            ctk.CTkLabel(card, text="🔒 PHÂN QUYỀN VAI TRÒ", font=ctk.CTkFont(size=13, weight="bold"),
                         text_color="#F59E0B").pack(anchor="w", padx=12, pady=(12, 6))
            ctk.CTkLabel(card, font=ctk.CTkFont(size=12), text_color="#9CA3AF", justify="left",
                         wraplength=280,
                         text="Tài khoản THỦ THƯ chỉ tra cứu danh mục và báo hỏng sách khi phục vụ "
                              "mượn/trả.\n\nThêm, sửa, xóa đầu sách và cuốn sách thuộc thẩm quyền "
                              "Ban Quản Lý (QUANLY).").pack(anchor="w", padx=12, pady=(0, 15))
            self._set_view_only(True)
            return

        self.selector = ctk.CTkSegmentedButton(right, values=[ENTITY_COPY, ENTITY_TITLE],
                                               command=self._switch_entity)
        self.selector.set(ENTITY_COPY)
        self.selector.pack(fill="x", pady=(0, 6))
        self.lbl_mode = ctk.CTkLabel(right, text="", font=ctk.CTkFont(size=12), anchor="w",
                                     justify="left", wraplength=320)
        self.lbl_mode.pack(anchor="w", pady=(0, 6))

        self.frame_copy = ctk.CTkFrame(right, fg_color="transparent")
        self.frame_title = ctk.CTkFrame(right, fg_color="transparent")

        def entry(parent, label, placeholder=""):
            ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=12)).pack(anchor="w")
            widget = ctk.CTkEntry(parent, placeholder_text=placeholder, height=34)
            widget.pack(fill="x", pady=(2, 6))
            return widget

        def combo(parent, label, values):
            ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=12)).pack(anchor="w")
            widget = ctk.CTkComboBox(parent, values=values, height=34)
            widget.pack(fill="x", pady=(2, 6))
            return widget

        # Form 1: physical copy (SACH) — primary key MASACH
        copy_inputs = {
            "MASACH": entry(self.frame_copy, "Mã cuốn sách (khóa chính) *", "Ví dụ: S00103"),
            "ISBN": combo(self.frame_copy, "Thuộc đầu sách (ISBN) *", [""]),
            "NGANTU": combo(self.frame_copy, "Vị trí ngăn tủ / kệ *", [""]),
            "TINHTRANG": combo(self.frame_copy, "Tình trạng", list(CONDITIONS)),
        }
        # Form 2: title (ISBN) — primary key ISBN
        title_inputs = {
            "ISBN": entry(self.frame_title, "Mã ISBN (khóa chính, 10 ký tự) *", "Ví dụ: ISBN000004"),
            "TENSACH": entry(self.frame_title, "Tên đầu sách *", "Tên sách đầy đủ..."),
            "GIA": entry(self.frame_title, "Giá bìa (VNĐ) *", "Ví dụ: 120000"),
            "THELOAI": combo(self.frame_title, "Thể loại", [""]),
            "TACGIA": combo(self.frame_title, "Tác giả chính", [""]),
            "NGONNGU": combo(self.frame_title, "Ngôn ngữ", [""]),
            "NHAXB": entry(self.frame_title, "Nhà xuất bản", "Ví dụ: NXB Trẻ"),
            "SOTRANG": entry(self.frame_title, "Số trang", "Ví dụ: 350"),
            "KHOSACH": entry(self.frame_title, "Khổ sách (tối đa 5 ký tự)", "Ví dụ: A5"),
            "LANXUATBAN": entry(self.frame_title, "Lần xuất bản", "Ví dụ: 1"),
            "NOIDUNG": entry(self.frame_title, "Nội dung tóm tắt", "Mô tả tóm tắt..."),
        }
        view_only = [w for w in (self.btn_search, self.btn_refresh, self.txt_search,
                                 self.btn_toggle_status, self.selector) if w is not None]
        self.forms[ENTITY_COPY] = FormStateController(
            copy_inputs, self.buttons, key_fields=("MASACH",), view_only_widgets=view_only,
            defaults={"TINHTRANG": "Tốt"}, on_mode_change=self._on_mode_change)
        self.forms[ENTITY_TITLE] = FormStateController(
            title_inputs, self.buttons, key_fields=("ISBN",), view_only_widgets=view_only,
            defaults={"LANXUATBAN": "1"}, on_mode_change=self._on_mode_change)
        self.frame_copy.pack(fill="x")

    def _set_view_only(self, _value: bool) -> None:
        """Non-managers: no form, only Thoát and the status action are available."""
        self.lbl_mode = None

    @property
    def form(self) -> Optional[FormStateController]:
        return self.forms.get(self.entity)

    def _configure_tree_columns(self) -> None:
        spec = COPY_TREE_SPEC if self.entity == ENTITY_COPY else TITLE_TREE_SPEC
        self.tree.delete(*self.tree.get_children())
        self.records.clear()
        self.tree.configure(columns=[col for col, *_ in spec], displaycolumns="#all")
        for col, heading, width, align in spec:
            self.tree.heading(col, text=heading, anchor=align)
            self.tree.column(col, width=width, minwidth=40, anchor=align)
        if hasattr(self, "lbl_header"):
            self.lbl_header.configure(
                text="DANH MỤC CUỐN SÁCH THƯ VIỆN"
                if self.entity == ENTITY_COPY
                else "DANH MỤC ĐẦU SÁCH (ISBN)"
            )

    def _switch_entity(self, entity: str) -> None:
        if self.form and self.form.is_editing:          # cannot switch in the middle of Thêm/Sửa
            self.selector.set(self.entity)
            return
        if entity == self.entity:
            return
        prev = self._selected()
        prev_isbn = str(prev.get("ISBN", "")).strip() if prev else ""
        self.entity = entity
        self.frame_copy.pack_forget()
        self.frame_title.pack_forget()
        (self.frame_copy if entity == ENTITY_COPY else self.frame_title).pack(fill="x")
        self._configure_tree_columns()
        self.load_data()
        if entity == ENTITY_TITLE and prev_isbn and self.tree.exists(prev_isbn):
            self.tree.selection_set(prev_isbn)
            self.tree.see(prev_isbn)
            self._on_select()

    def _on_mode_change(self, mode: FormMode) -> None:
        self.tree.configure(selectmode="browse" if mode is FormMode.VIEW else "none")
        if self.btn_toggle_status is not None and mode is FormMode.VIEW:
            self.btn_toggle_status.configure(
                state="normal" if self.entity == ENTITY_COPY else "disabled"
            )
        if self.lbl_mode is None:
            return
        target = "cuốn sách" if self.entity == ENTITY_COPY else "đầu sách"
        key = "MASACH" if self.entity == ENTITY_COPY else "ISBN"
        self.lbl_mode.configure(**{
            FormMode.VIEW: {"text": f"Chế độ xem {target} — chọn một dòng để xem chi tiết.",
                            "text_color": "#9CA3AF"},
            FormMode.ADD: {"text": f"ĐANG THÊM {target} mới — Ghi để lưu, Phục hồi để hủy.",
                           "text_color": "#60A5FA"},
            FormMode.EDIT: {"text": f"ĐANG SỬA {target} — khóa chính {key} bị khóa. Ghi để lưu, "
                                    "Phục hồi để hủy.", "text_color": "#A78BFA"},
        }[mode])

    # ---------------------------------------------------------------- data
    def load_data(self):
        try:
            records = (
                SachDAO.get_all_sach()
                if self.entity == ENTITY_COPY
                else SachDAO.get_all_isbn()
            )
            self.display_records(records)
            self.txt_search.delete(0, "end")
            self.load_comboboxes()
        except ValueError as error:
            messagebox.showwarning("Cảnh báo", str(error))
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", f"Không thể tải danh sách sách:\n{error}")

    def load_comboboxes(self):
        """Fill the foreign-key ComboBoxes (only the manager has the forms)."""
        if not self.forms:
            return
        self.maps["isbn"] = {f"{r['ISBN'].strip()} - {r['TENSACH']}": r["ISBN"].strip()
                             for r in SachDAO.get_all_isbn()}
        self.maps["ngantu"] = {f"{r['KE']} ({r['MOTA']})": r["MANGANTU"] for r in SachDAO.get_danh_muc_ngan_tu()}
        self.maps["tl"] = {r["THELOAI"]: r["MATL"] for r in SachDAO.get_danh_muc_the_loai()}
        self.maps["tg"] = {r["HOTENTG"]: r["MATACGIA"] for r in SachDAO.get_danh_muc_tac_gia()}
        self.maps["nn"] = {r["NGONNGU"]: r["MANGONNGU"] for r in SachDAO.get_danh_muc_ngon_ngu()}
        copy_inputs = self.forms[ENTITY_COPY].inputs
        title_inputs = self.forms[ENTITY_TITLE].inputs
        for widget, key in ((copy_inputs["ISBN"], "isbn"), (copy_inputs["NGANTU"], "ngantu"),
                            (title_inputs["THELOAI"], "tl"), (title_inputs["TACGIA"], "tg"),
                            (title_inputs["NGONNGU"], "nn")):
            widget.configure(values=list(self.maps[key]) or [""])
        first = lambda key: next(iter(self.maps[key]), "")  # noqa: E731
        self.forms[ENTITY_COPY].defaults.update(ISBN=first("isbn"), NGANTU=first("ngantu"))
        self.forms[ENTITY_TITLE].defaults.update(THELOAI=first("tl"), TACGIA=first("tg"), NGONNGU=first("nn"))

    def display_records(self, records):
        self.tree.delete(*self.tree.get_children())
        self.records.clear()
        if self.entity == ENTITY_COPY:
            for idx, r in enumerate(records):
                iid = str(r.get("MASACH", "")).strip()
                if not iid or self.tree.exists(iid):
                    continue
                good, borrowed = r.get("TINHTRANG") == 1, r.get("CHOMUON") == 1
                tag = "damaged" if not good else ("borrowed" if borrowed else ("oddrow" if idx % 2 else "evenrow"))
                self.records[iid] = r
                self.tree.insert("", "end", iid=iid, tags=(tag,), values=(
                    r.get("MASACH"), str(r.get("ISBN", "")).strip(), r.get("TENSACH"),
                    r.get("THELOAI") or "Chưa phân loại", r.get("HOTENTG") or "Chưa rõ",
                    r.get("ViTri"), f"{r.get('GiaBia', 0):,}",
                    "Tốt" if good else "Hư hỏng", "Đang mượn" if borrowed else "Sẵn có",
                ))
            self.lbl_count.configure(text=f"Tổng: {len(self.records)} cuốn sách")
        else:
            for idx, r in enumerate(records):
                iid = str(r.get("ISBN", "")).strip()
                if not iid or self.tree.exists(iid):
                    continue
                tong = int(r.get("TongBanSao") or 0)
                san_co = int(r.get("BanSaoKhaDung") or 0)
                gia = int(r.get("GiaBia") if r.get("GiaBia") is not None else (r.get("GIA") or 0))
                tag = "empty_copies" if tong == 0 else ("oddrow" if idx % 2 else "evenrow")
                self.records[iid] = r
                self.tree.insert("", "end", iid=iid, tags=(tag,), values=(
                    iid, r.get("TENSACH"), r.get("THELOAI") or "Chưa phân loại",
                    r.get("HOTENTG") or "Chưa rõ", r.get("NGONNGU") or "Chưa rõ",
                    r.get("NHAXB") or "", f"{gia:,}", tong, san_co,
                ))
            self.lbl_count.configure(text=f"Tổng: {len(self.records)} đầu sách")
        for form in self.forms.values():
            form.clear()
        if self.form:
            self.form.to_view()

    def handle_search(self):
        keyword = self.txt_search.get().strip()
        if not keyword:
            self.load_data()
            return
        try:
            records = (
                SachDAO.search_sach(keyword)
                if self.entity == ENTITY_COPY
                else SachDAO.search_isbn(keyword)
            )
            self.display_records(records)
        except ValueError as error:
            messagebox.showwarning("Cảnh báo", str(error))
        except Exception as error:
            messagebox.showerror("Lỗi tìm kiếm", str(error))

    def _selected(self) -> Optional[Dict[str, Any]]:
        selection = self.tree.selection()
        return self.records.get(selection[0]) if selection else None

    def _label(self, key: str, value: Any) -> str:
        for label, item in self.maps[key].items():
            if str(item).strip() == str(value).strip():
                return label
        return ""

    def _on_select(self, _event=None):
        if not self.form or self.form.is_editing:
            return
        record = self._selected()
        if not record:
            return
        if self.entity == ENTITY_COPY:
            self.form.fill({
                "MASACH": record["MASACH"], "ISBN": self._label("isbn", record["ISBN"]),
                "NGANTU": self._label("ngantu", record.get("MANGANTU")),
                "TINHTRANG": "Tốt" if record.get("TINHTRANG") == 1 else "Hư hỏng",
            })
        else:
            try:
                detail = SachDAO.get_dau_sach(record["ISBN"]) or {}
            except Exception as error:
                messagebox.showerror("Lỗi CSDL", f"Không thể tải đầu sách:\n{error}")
                return
            self.form.fill({
                "ISBN": str(detail.get("ISBN", "")).strip(), "TENSACH": detail.get("TENSACH"),
                "GIA": detail.get("GIA"), "THELOAI": self._label("tl", detail.get("MATL")),
                "TACGIA": self._label("tg", detail.get("MATACGIA")),
                "NGONNGU": self._label("nn", detail.get("MANGONNGU")), "NHAXB": detail.get("NHAXB"),
                "SOTRANG": detail.get("SOTRANG"), "KHOSACH": detail.get("KHOSACH"),
                "LANXUATBAN": detail.get("LANXUATBAN"), "NOIDUNG": detail.get("NOIDUNG"),
            })

    @staticmethod
    def _int_or_none(text: str, label: str) -> Optional[int]:
        if not text:
            return None
        try:
            return int(text)
        except ValueError as error:
            raise ValueError(f"{label} phải là số nguyên!") from error

    # ------------------------------------------------------------ commands
    def on_add(self):
        self.form.to_add()

    def on_edit(self):
        if not self._selected():
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một dòng sách cần sửa!")
            return
        self.form.to_edit()

    def on_cancel(self):
        self.form.cancel()
        self._on_select()

    def on_save(self):
        """'Ghi' for the active entity: INSERT (Thêm) or UPDATE (Sửa)."""
        values = self.form.values()
        adding = self.form.mode is FormMode.ADD
        try:
            if self.entity == ENTITY_COPY:
                isbn = self.maps["isbn"].get(values["ISBN"])
                mangantu = self.maps["ngantu"].get(values["NGANTU"])
                if not values["MASACH"]:
                    raise ValueError("Vui lòng nhập Mã cuốn sách!")
                if not isbn or mangantu is None:
                    raise ValueError("Vui lòng chọn Đầu sách (ISBN) và Vị trí ngăn tủ!")
                condition = CONDITIONS.get(values["TINHTRANG"], 1)
                if adding:
                    SachDAO.them_cuon_sach(values["MASACH"], isbn, mangantu, condition)
                else:
                    SachDAO.cap_nhat_cuon_sach(values["MASACH"], isbn, mangantu, condition)
                key, message = values["MASACH"], f"Đã ghi cuốn sách '{values['MASACH']}'."
            else:
                gia = self._int_or_none(values["GIA"], "Giá bìa")
                if gia is None:
                    raise ValueError("Vui lòng nhập Giá bìa!")
                data = {
                    "ISBN": values["ISBN"], "TENSACH": values["TENSACH"], "GIA": gia,
                    "MATL": self.maps["tl"].get(values["THELOAI"]),
                    "MANGONNGU": self.maps["nn"].get(values["NGONNGU"]),
                    "NHAXB": values["NHAXB"], "SOTRANG": self._int_or_none(values["SOTRANG"], "Số trang"),
                    "KHOSACH": values["KHOSACH"],
                    "LANXUATBAN": self._int_or_none(values["LANXUATBAN"], "Lần xuất bản") or 1,
                    "NOIDUNG": values["NOIDUNG"],
                }
                matg = self.maps["tg"].get(values["TACGIA"])
                if adding:
                    SachDAO.them_dau_sach(data, matacgia=matg)
                else:
                    SachDAO.cap_nhat_dau_sach(data, matacgia=matg)
                key = values["ISBN"].strip()
                message = f"Đã ghi đầu sách '{values['TENSACH']}' ({key})."
        except ValueError as error:
            messagebox.showwarning("Không thể ghi", str(error))       # form stays open
            return
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", f"Không thể ghi dữ liệu:\n{error}")
            return
        messagebox.showinfo("Thành công", message)
        self.load_data()                          # reload grid + combos -> VIEW, inputs locked
        if key and self.tree.exists(key):
            self.tree.selection_set(key)
            self.tree.see(key)
            self._on_select()

    def on_delete(self):
        record = self._selected()
        if not record:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một dòng sách cần xóa!")
            return
        if self.entity == ENTITY_COPY:
            what = f"Cuốn sách: {record['MASACH']} - {record['TENSACH']}"
            action = lambda: SachDAO.huy_cuon_sach(record["MASACH"])  # noqa: E731
        else:
            what = f"Đầu sách: {str(record['ISBN']).strip()} - {record['TENSACH']}"
            action = lambda: SachDAO.xoa_dau_sach(record["ISBN"])  # noqa: E731
        if not messagebox.askyesno("Xác nhận xóa",
                                   f"Bạn có chắc chắn muốn xóa bản ghi này không?\n\n{what}",
                                   icon="warning"):
            return
        try:
            action()                              # deletes immediately, no extra Ghi
        except ValueError as error:               # FK 547 -> "đã phát sinh giao dịch..."
            messagebox.showerror("Không thể xóa", str(error))
            return
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", f"Không thể xóa:\n{error}")
            return
        messagebox.showinfo("Thành công", f"Đã xóa {what.split(':')[0].lower()} thành công.")
        self.load_data()

    def handle_toggle_tinh_trang(self):
        record = self._selected()
        if not record:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một cuốn sách trên bảng để cập nhật tình trạng!")
            return
        new_status = 0 if record.get("TINHTRANG") == 1 else 1
        action = "báo HƯ HỎNG" if new_status == 0 else "khôi phục trạng thái TỐT"
        if not messagebox.askyesno("Xác nhận",
                                   f"Bạn có chắc muốn {action} cho cuốn sách '{record['MASACH']}' "
                                   f"({record['TENSACH']})?"):
            return
        try:
            if SachDAO.cap_nhat_tinh_trang(record["MASACH"], new_status):
                messagebox.showinfo("Thành công", f"Đã cập nhật tình trạng sách '{record['MASACH']}'!")
                self.load_data()
            else:
                messagebox.showerror("Thất bại", "Không thể cập nhật CSDL!")
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", str(error))

    def clear_form(self):
        for form in self.forms.values():
            form.clear()
            form.to_view()


# Bí danh tương thích
TabSach = BookScreen
