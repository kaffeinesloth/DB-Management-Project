"""Manager-only screen for creating and deleting SQL Server accounts."""

from tkinter import messagebox, ttk

import customtkinter as ctk
import pyodbc

from account_management.account_actions import (
    create_employee_account,
    create_employee_with_account,
    delete_employee_account,
    list_employee_accounts,
)


def _friendly_db_error(error: Exception) -> str:
    text = str(error)
    for marker in (
        "Mã nhân viên",
        "Nhân viên",
        "Tên đăng nhập",
        "Mật khẩu",
        "Nhóm quyền",
        "Không thể xóa",
        "Họ và tên",
        "Email nhân viên",
        "Số điện thoại",
        "Tài khoản đang được sử dụng",
    ):
        index = text.find(marker)
        if index >= 0:
            return text[index:].split(". (", 1)[0].strip()
    return text


class AccountScreen(ctk.CTkFrame):
    """Show every valid employee and whether they already have an account."""

    def __init__(self, parent, current_user=None):
        super().__init__(parent)
        self.current_user = current_user or {}
        self.selected_employee_id = None
        self.password_visible = False
        self._build_ui()
        self.refresh_accounts()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        title = ctk.CTkLabel(
            self,
            text="QUẢN LÝ TÀI KHOẢN SQL SERVER",
            font=ctk.CTkFont(size=21, weight="bold"),
        )
        title.grid(row=0, column=0, padx=20, pady=(18, 4), sticky="w")

        subtitle = ctk.CTkLabel(
            self,
            text="Chọn nhân viên trong danh sách để tạo hoặc xóa tài khoản.",
            text_color="gray",
        )
        subtitle.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        table_frame = ctk.CTkFrame(self)
        table_frame.grid(row=2, column=0, padx=20, pady=5, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        tree_style = ttk.Style()
        tree_style.configure(
            "Account.Treeview",
            rowheight=30,
            background="#1F2937",
            fieldbackground="#1F2937",
            foreground="#E5E7EB",
            borderwidth=0,
        )
        tree_style.configure(
            "Account.Treeview.Heading",
            background="#111827",
            foreground="#F9FAFB",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
        )
        tree_style.map(
            "Account.Treeview",
            background=[("selected", "#2563EB")],
            foreground=[("selected", "#FFFFFF")],
        )

        columns = ("id", "name", "email", "status", "login", "role")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=11,
            style="Account.Treeview",
            selectmode="browse",
        )
        headings = {
            "id": "Mã NV",
            "name": "Họ tên",
            "email": "Email",
            "status": "Trạng thái",
            "login": "Tên đăng nhập",
            "role": "Nhóm quyền",
        }
        widths = {"id": 65, "name": 170, "email": 210, "status": 115, "login": 130, "role": 95}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="center" if column in ("id", "status", "role") else "w")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        form = ctk.CTkFrame(self)
        form.grid(row=3, column=0, padx=20, pady=(8, 8), sticky="ew")
        form.grid_columnconfigure((0, 1, 2), weight=1)

        self.selection_help = ctk.CTkLabel(
            form,
            text="Chọn một nhân viên để tiếp tục.",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#F59E0B",
            anchor="w",
        )
        self.selection_help.grid(
            row=0, column=0, columnspan=3, padx=12, pady=(10, 4), sticky="ew"
        )

        ctk.CTkLabel(form, text="Tên đăng nhập", anchor="w").grid(
            row=1, column=0, padx=(12, 6), sticky="ew"
        )
        ctk.CTkLabel(form, text="Mật khẩu", anchor="w").grid(
            row=1, column=1, padx=6, sticky="ew"
        )
        ctk.CTkLabel(form, text="Nhóm quyền", anchor="w").grid(
            row=1, column=2, padx=(6, 12), sticky="ew"
        )

        self.entry_login = ctk.CTkEntry(form, placeholder_text="Tên đăng nhập (vd: nv_5)")
        self.entry_login.grid(row=2, column=0, padx=(12, 6), pady=(3, 10), sticky="ew")
        self.entry_password = ctk.CTkEntry(form, placeholder_text="Mật khẩu (ít nhất 6 ký tự)", show="*")
        self.entry_password.grid(row=2, column=1, padx=6, pady=(3, 10), sticky="ew")
        self.role_option = ctk.CTkOptionMenu(form, values=["THUTHU", "QUANLY"])
        self.role_option.set("THUTHU")
        self.role_option.grid(row=2, column=2, padx=(6, 12), pady=(3, 10), sticky="ew")

        self.chk_show_password = ctk.CTkCheckBox(
            form,
            text="Hiện mật khẩu",
            width=120,
            font=ctk.CTkFont(size=11),
            command=self._toggle_password,
        )
        self.chk_show_password.grid(row=3, column=1, padx=6, pady=(0, 10), sticky="w")

        button_bar = ctk.CTkFrame(self, fg_color="transparent")
        button_bar.grid(row=4, column=0, padx=20, pady=(0, 18), sticky="ew")

        self.btn_create = ctk.CTkButton(
            button_bar, text="Tạo tài khoản", command=self.create_account, state="disabled"
        )
        self.btn_create.pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            button_bar,
            text="Thêm nhân viên + tài khoản",
            fg_color="#059669",
            hover_color="#047857",
            command=self.open_new_employee_form,
        ).pack(side="left", padx=8)
        self.btn_delete = ctk.CTkButton(
            button_bar,
            text="Xóa tài khoản",
            fg_color="#DC2626",
            hover_color="#B91C1C",
            command=self.delete_account,
            state="disabled",
        )
        self.btn_delete.pack(side="left", padx=8)
        ctk.CTkButton(
            button_bar, text="Làm mới", fg_color="#475569", command=self.refresh_accounts
        ).pack(side="left", padx=8)

        self.status_label = ctk.CTkLabel(button_bar, text="", text_color="gray")
        self.status_label.pack(side="right")

    def _toggle_password(self):
        self.password_visible = not self.password_visible
        self.entry_password.configure(show="" if self.password_visible else "*")

    def open_new_employee_form(self):
        """Open one form that creates both NHANVIEN and its login."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Thêm nhân viên và tài khoản")
        dialog.geometry("620x690")
        dialog.minsize(560, 620)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        panel = ctk.CTkScrollableFrame(dialog, corner_radius=0)
        panel.pack(fill="both", expand=True, padx=14, pady=14)
        panel.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            panel,
            text="THÊM NHÂN VIÊN VÀ TẠO TÀI KHOẢN",
            font=ctk.CTkFont(size=19, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=(8, 4), sticky="w")
        ctk.CTkLabel(
            panel,
            text="Một lần lưu sẽ tạo hồ sơ NHANVIEN và tài khoản SQL Server.",
            text_color="gray",
        ).grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 14), sticky="w")

        entries = {}
        for column, (key, label, placeholder) in enumerate((
            ("family_name", "Họ *", "Ví dụ: Nguyễn"),
            ("given_name", "Tên *", "Ví dụ: An"),
        )):
            ctk.CTkLabel(panel, text=label, anchor="w").grid(
                row=2, column=column,
                padx=12, pady=(5, 2), sticky="ew",
            )
            entry = ctk.CTkEntry(panel, placeholder_text=placeholder)
            entry.grid(
                row=3, column=column,
                padx=12, pady=(0, 5), sticky="ew",
            )
            entries[key] = entry

        row_index = 4
        for key, label, placeholder in (
            ("address", "Địa chỉ", "Địa chỉ liên hệ"),
            ("phone", "Điện thoại", "10 đến 11 chữ số"),
            ("email", "Email", "Ví dụ: an@library.local"),
            ("login_name", "Tên đăng nhập *", "Ví dụ: nv_an"),
            ("password", "Mật khẩu *", "Ít nhất 6 ký tự"),
        ):
            ctk.CTkLabel(panel, text=label, anchor="w").grid(
                row=row_index, column=0, columnspan=2,
                padx=12, pady=(5, 2), sticky="ew",
            )
            entry = ctk.CTkEntry(
                panel, placeholder_text=placeholder,
                show="*" if key == "password" else "",
            )
            entry.grid(
                row=row_index + 1, column=0, columnspan=2,
                padx=12, pady=(0, 5), sticky="ew",
            )
            entries[key] = entry
            row_index += 2

        ctk.CTkLabel(panel, text="Giới tính", anchor="w").grid(
            row=row_index, column=0, padx=12, pady=(5, 2), sticky="ew"
        )
        ctk.CTkLabel(panel, text="Nhóm quyền", anchor="w").grid(
            row=row_index, column=1, padx=12, pady=(5, 2), sticky="ew"
        )
        gender_option = ctk.CTkOptionMenu(panel, values=["Nữ", "Nam"])
        gender_option.set("Nam")
        gender_option.grid(row=row_index + 1, column=0, padx=12, pady=(0, 12), sticky="ew")
        role_option = ctk.CTkOptionMenu(panel, values=["THUTHU", "QUANLY"])
        role_option.set("THUTHU")
        role_option.grid(row=row_index + 1, column=1, padx=12, pady=(0, 12), sticky="ew")

        show_password = ctk.CTkCheckBox(
            panel,
            text="Hiện mật khẩu",
            command=lambda: entries["password"].configure(
                show="" if entries["password"].cget("show") == "*" else "*"
            ),
        )
        show_password.grid(
            row=row_index + 2, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="w"
        )

        def submit():
            try:
                employee_id = create_employee_with_account(
                    entries["family_name"].get(),
                    entries["given_name"].get(),
                    gender_option.get() == "Nam",
                    entries["address"].get(),
                    entries["phone"].get(),
                    entries["email"].get(),
                    entries["login_name"].get(),
                    entries["password"].get(),
                    role_option.get(),
                )
            except (pyodbc.Error, ValueError) as error:
                messagebox.showerror("Không thể tạo", _friendly_db_error(error), parent=dialog)
                return
            dialog.destroy()
            self.refresh_accounts()
            item_id = str(employee_id)
            if self.tree.exists(item_id):
                self.tree.selection_set(item_id)
                self.tree.focus(item_id)
                self.tree.see(item_id)
                self._on_select()
            messagebox.showinfo(
                "Thành công",
                f"Đã tạo nhân viên mã {employee_id} và tài khoản SQL Server.",
                parent=self,
            )

        ctk.CTkButton(
            panel,
            text="Lưu nhân viên và tạo tài khoản",
            height=42,
            font=ctk.CTkFont(weight="bold"),
            command=submit,
        ).grid(
            row=row_index + 3, column=0, columnspan=2,
            padx=12, pady=(5, 16), sticky="ew",
        )
        dialog.bind("<Return>", lambda _event: submit())
        entries["family_name"].focus_set()
        return dialog

    def refresh_accounts(self):
        try:
            rows = list_employee_accounts()
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", _friendly_db_error(error))
            return

        self.tree.delete(*self.tree.get_children())
        account_count = 0
        first_missing_id = None
        for row in rows:
            status = "Đã có" if row["DaCoTaiKhoan"] else "Chưa có"
            account_count += int(row["DaCoTaiKhoan"])
            if not row["DaCoTaiKhoan"] and first_missing_id is None:
                first_missing_id = str(row["MANV"])
            self.tree.insert(
                "",
                "end",
                iid=str(row["MANV"]),
                values=(
                    row["MANV"], row["HoTen"], row["Email"], status,
                    row["LoginName"], row["RoleName"],
                ),
                tags=("has_account" if row["DaCoTaiKhoan"] else "no_account",),
            )
        self.tree.tag_configure("has_account", foreground="#15803D")
        self.tree.tag_configure("no_account", foreground="#B45309")
        self.selected_employee_id = None
        self.btn_create.configure(state="disabled")
        self.btn_delete.configure(state="disabled")
        self.entry_login.configure(state="normal")
        self.entry_password.configure(state="normal")
        self.role_option.configure(state="normal")
        self.status_label.configure(
            text=f"{account_count}/{len(rows)} nhân viên đã có tài khoản"
        )
        if rows:
            initial_id = first_missing_id or str(rows[0]["MANV"])
            self.tree.selection_set(initial_id)
            self.tree.focus(initial_id)
            self.tree.see(initial_id)
            self._on_select()

    def _on_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        self.selected_employee_id = int(selected[0])
        values = self.tree.item(selected[0], "values")
        has_account = values[3] == "Đã có"
        is_current_account = values[4] == self.current_user.get("LoginName")
        self.btn_create.configure(
            state="disabled" if has_account else "normal",
            text="Đã có tài khoản" if has_account else f"Tạo tài khoản cho NV {self.selected_employee_id}",
        )
        self.btn_delete.configure(
            state="normal" if has_account and not is_current_account else "disabled",
            text=(
                "Không thể xóa chính mình"
                if is_current_account
                else (f"Xóa {values[4]}" if has_account else "Chưa có tài khoản để xóa")
            ),
        )
        self.entry_login.configure(state="normal")
        self.entry_login.delete(0, "end")
        self.entry_login.insert(0, values[4] if has_account else f"nv_{self.selected_employee_id}")
        self.entry_password.configure(state="normal")
        self.entry_password.delete(0, "end")
        if values[5] in ("THUTHU", "QUANLY"):
            self.role_option.set(values[5])
        self.entry_login.configure(state="disabled" if has_account else "normal")
        self.entry_password.configure(state="disabled" if has_account else "normal")
        self.role_option.configure(state="disabled" if has_account else "normal")
        if is_current_account:
            self.selection_help.configure(
                text="Đây là tài khoản đang đăng nhập — không thể tự xóa.",
                text_color="#F59E0B",
            )
        elif has_account:
            self.selection_help.configure(
                text=f"{values[1]} đã có tài khoản {values[4]}. Bạn có thể xóa tài khoản này.",
                text_color="#22C55E",
            )
        else:
            self.selection_help.configure(
                text=f"{values[1]} chưa có tài khoản. Nhập mật khẩu rồi bấm Tạo tài khoản.",
                text_color="#F59E0B",
            )
            self.entry_password.focus_set()

    def create_account(self):
        if self.selected_employee_id is None:
            return
        login_name = self.entry_login.get().strip()
        password = self.entry_password.get()
        if not login_name or len(password) < 6:
            messagebox.showwarning("Thiếu thông tin", "Nhập tên đăng nhập và mật khẩu ít nhất 6 ký tự.")
            return
        try:
            create_employee_account(
                self.selected_employee_id, login_name, password, self.role_option.get()
            )
        except (pyodbc.Error, ValueError) as error:
            messagebox.showerror("Không thể tạo", _friendly_db_error(error))
            return
        messagebox.showinfo("Thành công", "Đã tạo tài khoản SQL Server cho nhân viên.")
        self.refresh_accounts()

    def delete_account(self):
        if self.selected_employee_id is None:
            return
        values = self.tree.item(str(self.selected_employee_id), "values")
        if not messagebox.askyesno(
            "Xác nhận xóa",
            f"Xóa tài khoản {values[4]} của {values[1]}?",
        ):
            return
        try:
            delete_employee_account(self.selected_employee_id)
        except (pyodbc.Error, ValueError) as error:
            messagebox.showerror("Không thể xóa", _friendly_db_error(error))
            return
        messagebox.showinfo("Thành công", "Đã xóa tài khoản SQL Server.")
        self.refresh_accounts()
