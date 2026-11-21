"""Manager-only screen for employee SQL Server accounts.

The main page is deliberately action-oriented: select an employee, then create
an account, change its role, delete it, or reset its password.  Data entry lives
in focused dialogs instead of exposing a generic CRUD command bar.
"""

from tkinter import messagebox, ttk
from typing import Any, Dict, Optional

import customtkinter as ctk
import pyodbc

from account_management.account_actions import (
    DEFAULT_RESET_PASSWORD,
    change_account_role,
    change_own_password,
    create_employee_account,
    create_employee_with_account,
    delete_employee_account,
    list_employee_accounts,
    list_employees_without_account,
    reset_employee_password,
)
from database import friendly_message, server_message


def _friendly_db_error(error: Exception) -> str:
    """Vietnamese text for the user: known SQL Server codes, else the SP's THROW text."""
    if isinstance(error, ValueError):
        return str(error)
    return friendly_message(error, "tài khoản") or server_message(error)


class AccountScreen(ctk.CTkFrame):
    """List every employee with their account status and manage accounts."""

    ROLE_VALUES = ["THUTHU", "QUANLY"]

    def __init__(self, parent, current_user=None):
        super().__init__(parent)
        self.current_user = current_user or {}
        self.rows: Dict[str, Dict[str, Any]] = {}
        self.eligible: Dict[str, int] = {}          # "MANV - Họ tên" -> MANV (no account yet)
        self._build_ui()
        self.refresh_accounts()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="QUẢN LÝ TÀI KHOẢN SQL SERVER",
                     font=ctk.CTkFont(size=21, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(18, 4), sticky="w")
        ctk.CTkLabel(self, text="Mỗi nhân viên chỉ có tối đa 1 tài khoản đăng nhập.",
                     text_color="gray").grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        table_frame = ctk.CTkFrame(self)
        table_frame.grid(row=2, column=0, padx=20, pady=5, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("Account.Treeview", rowheight=30, background="#1F2937",
                        fieldbackground="#1F2937", foreground="#E5E7EB", borderwidth=0)
        style.configure("Account.Treeview.Heading", background="#111827", foreground="#F9FAFB",
                        relief="flat", font=("Segoe UI", 10, "bold"))
        style.map("Account.Treeview", background=[("selected", "#2563EB")],
                  foreground=[("selected", "#FFFFFF")])

        columns = ("id", "name", "email", "status", "login", "role")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10,
                                 style="Account.Treeview", selectmode="browse")
        for column, text, width in (
            ("id", "Mã NV", 65), ("name", "Họ tên", 170), ("email", "Email", 210),
            ("status", "Trạng thái", 110), ("login", "Tên đăng nhập", 130), ("role", "Nhóm quyền", 95),
        ):
            self.tree.heading(column, text=text)
            self.tree.column(column, width=width,
                             anchor="center" if column in ("id", "status", "role") else "w")
        self.tree.tag_configure("has_account", foreground="#22C55E")
        self.tree.tag_configure("no_account", foreground="#F59E0B")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # ---- selected employee and focused actions ---------------------
        action_panel = ctk.CTkFrame(self)
        action_panel.grid(row=3, column=0, padx=20, pady=(8, 16), sticky="ew")
        action_panel.grid_columnconfigure(0, weight=1)

        self.lbl_selection = ctk.CTkLabel(
            action_panel,
            text="Chọn một nhân viên trong danh sách để quản lý tài khoản.",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#9CA3AF",
        )
        self.lbl_selection.grid(row=0, column=0, padx=14, pady=(12, 8), sticky="ew")
        self.status_label = ctk.CTkLabel(action_panel, text="", text_color="gray")
        self.status_label.grid(row=0, column=1, padx=14, pady=(12, 8), sticky="e")

        actions = ctk.CTkFrame(action_panel, fg_color="transparent")
        actions.grid(row=1, column=0, columnspan=2, padx=14, pady=(0, 8), sticky="w")
        self.btn_create = ctk.CTkButton(
            actions, text="Tạo tài khoản", width=145, fg_color="#2563EB",
            hover_color="#1D4ED8", command=self.on_add,
        )
        self.btn_role = ctk.CTkButton(
            actions, text="Đổi nhóm quyền", width=145, fg_color="#7C3AED",
            hover_color="#6D28D9", command=self.on_edit,
        )
        self.btn_delete = ctk.CTkButton(
            actions, text="Xóa tài khoản", width=145, fg_color="#DC2626",
            hover_color="#B91C1C", command=self.on_delete,
        )
        self.btn_reset = ctk.CTkButton(
            actions, text="Reset mật khẩu", width=145, fg_color="#0E7490",
            hover_color="#155E75", command=self.on_reset_password,
        )
        self.btn_refresh = ctk.CTkButton(
            actions, text="Làm mới", width=110, fg_color="#475569",
            hover_color="#334155", command=self.refresh_accounts,
        )
        for button in (self.btn_create, self.btn_role, self.btn_delete,
                       self.btn_reset, self.btn_refresh):
            button.pack(side="left", padx=(0, 8))

        secondary = ctk.CTkFrame(action_panel, fg_color="transparent")
        secondary.grid(row=2, column=0, columnspan=2, padx=14, pady=(0, 12), sticky="w")
        ctk.CTkLabel(
            secondary, text="Nhân viên chưa có hồ sơ?", text_color="gray",
        ).pack(side="left", padx=(0, 8))
        self.btn_new_employee = ctk.CTkButton(
            secondary, text="Tạo nhân viên mới kèm tài khoản", width=230,
            fg_color="transparent", border_width=1, border_color="#059669",
            text_color=("#047857", "#34D399"), hover_color=("#D1FAE5", "#064E3B"),
            command=self.open_new_employee_form,
        )
        self.btn_new_employee.pack(side="left")
        self._sync_action_buttons()

    def _sync_action_buttons(self) -> None:
        """Enable only the actions that are valid for the current selection."""
        has_any_eligible = any(not r["DaCoTaiKhoan"] for r in self.rows.values())
        row = self._selected_row()

        if row is None:
            can_add = has_any_eligible
            can_manage = False
            self.lbl_selection.configure(
                text="Chọn một nhân viên trong danh sách để quản lý tài khoản.",
                text_color="#9CA3AF",
            )
        elif not row["DaCoTaiKhoan"]:
            can_add = True
            can_manage = False
            self.lbl_selection.configure(
                text=f"{row['HoTen']} chưa có tài khoản — có thể tạo tài khoản ngay.",
                text_color="#F59E0B",
            )
        elif row["LoginName"] == self.current_user.get("LoginName"):
            can_add = False
            can_manage = False
            self.lbl_selection.configure(
                text="Đang chọn tài khoản của chính bạn — hãy dùng nút 'Đổi mật khẩu' ở thanh bên.",
                text_color="#9CA3AF",
            )
        else:
            can_add = False
            can_manage = True
            role_label = self._role_label(row["RoleName"])
            self.lbl_selection.configure(
                text=f"{row['HoTen']} • {row['LoginName']} • {role_label}",
                text_color="#22C55E",
            )

        self.btn_create.configure(state="normal" if can_add else "disabled")
        self.btn_role.configure(state="normal" if can_manage else "disabled")
        self.btn_delete.configure(state="normal" if can_manage else "disabled")
        self.btn_reset.configure(state="normal" if can_manage else "disabled")

    # ---------------------------------------------------------------- data
    def refresh_accounts(self) -> None:
        try:
            rows = list_employee_accounts()
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", _friendly_db_error(error))
            return
        self.tree.delete(*self.tree.get_children())
        self.rows.clear()
        for row in rows:
            iid = str(row["MANV"])
            if self.tree.exists(iid):       # never insert a duplicate iid
                continue
            self.rows[iid] = row
            self.tree.insert("", "end", iid=iid, values=(
                row["MANV"], row["HoTen"], row["Email"],
                "Đã có" if row["DaCoTaiKhoan"] else "Chưa có",
                row["LoginName"], self._role_label(row["RoleName"]),
            ), tags=("has_account" if row["DaCoTaiKhoan"] else "no_account",))
        with_account = sum(1 for r in rows if r["DaCoTaiKhoan"])
        self.status_label.configure(text=f"{with_account}/{len(rows)} nhân viên đã có tài khoản")
        self._sync_action_buttons()

    def _selected_row(self) -> Optional[Dict[str, Any]]:
        selected = self.tree.selection()
        return self.rows.get(selected[0]) if selected else None

    def _employee_label(self, row: Dict[str, Any]) -> str:
        return f"{row['MANV']} - {row['HoTen']}"

    @staticmethod
    def _role_label(role_name: str) -> str:
        return {"THUTHU": "Thủ thư", "QUANLY": "Quản lý"}.get(role_name or "", "")

    def _on_select(self, _event=None) -> None:
        self._sync_action_buttons()

    # ------------------------------------------------------------ commands
    def on_add(self) -> None:
        selected = self._selected_row()
        try:
            eligible = list_employees_without_account()
        except Exception as error:
            messagebox.showerror("Lỗi CSDL", _friendly_db_error(error))
            return
        if not eligible:
            messagebox.showinfo("Không còn nhân viên",
                                "Tất cả nhân viên đều đã có tài khoản.\n"
                                "Hãy dùng 'Tạo nhân viên mới kèm tài khoản'.")
            return
        self.eligible = {self._employee_label(r): int(r["MANV"]) for r in eligible}
        selected_label = self._employee_label(selected) if selected and not selected["DaCoTaiKhoan"] else ""
        initial_employee = selected_label if selected_label in self.eligible else next(iter(self.eligible))
        self._open_create_account_dialog(initial_employee)

    def on_edit(self) -> None:
        row = self._selected_row()
        if not row:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn tài khoản cần sửa!")
            return
        if not row["DaCoTaiKhoan"]:
            messagebox.showwarning("Chưa có tài khoản",
                                   "Nhân viên này chưa có tài khoản. Hãy dùng nút Thêm.")
            return
        if row["LoginName"] == self.current_user.get("LoginName"):
            messagebox.showwarning("Không thể sửa", "Không thể tự đổi nhóm quyền của chính mình.")
            return
        self._open_role_dialog(row)

    def _open_create_account_dialog(self, initial_employee: str):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Tạo tài khoản")
        dialog.geometry("500x430")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        panel = ctk.CTkFrame(dialog)
        panel.pack(fill="both", expand=True, padx=18, pady=18)
        panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            panel, text="TẠO TÀI KHOẢN NHÂN VIÊN",
            font=ctk.CTkFont(size=19, weight="bold"),
        ).grid(row=0, column=0, padx=18, pady=(18, 4), sticky="w")
        ctk.CTkLabel(
            panel, text="Chỉ hiển thị nhân viên chưa có tài khoản.", text_color="gray",
        ).grid(row=1, column=0, padx=18, pady=(0, 14), sticky="w")

        ctk.CTkLabel(panel, text="Nhân viên *", anchor="w").grid(
            row=2, column=0, padx=18, pady=(3, 2), sticky="ew")
        employee = ctk.CTkComboBox(panel, values=list(self.eligible), state="readonly")
        employee.set(initial_employee)
        employee.grid(row=3, column=0, padx=18, pady=(0, 9), sticky="ew")

        ctk.CTkLabel(panel, text="Tên đăng nhập *", anchor="w").grid(
            row=4, column=0, padx=18, pady=(3, 2), sticky="ew")
        login = ctk.CTkEntry(panel, placeholder_text="Do quản lý tự đặt, ví dụ: nv_hoa")
        login.grid(row=5, column=0, padx=18, pady=(0, 9), sticky="ew")

        ctk.CTkLabel(panel, text="Mật khẩu ban đầu *", anchor="w").grid(
            row=6, column=0, padx=18, pady=(3, 2), sticky="ew")
        password_row = ctk.CTkFrame(panel, fg_color="transparent")
        password_row.grid(row=7, column=0, padx=18, pady=(0, 9), sticky="ew")
        password_row.grid_columnconfigure(0, weight=1)
        password = ctk.CTkEntry(password_row, placeholder_text="Ít nhất 6 ký tự", show="*")
        password.grid(row=0, column=0, sticky="ew")

        def toggle_password():
            password.configure(show="" if show_password.get() else "*")

        show_password = ctk.CTkCheckBox(
            password_row, text="Hiện", width=70, command=toggle_password,
        )
        show_password.grid(row=0, column=1, padx=(10, 0))

        ctk.CTkLabel(panel, text="Nhóm quyền *", anchor="w").grid(
            row=8, column=0, padx=18, pady=(3, 2), sticky="ew")
        role = ctk.CTkOptionMenu(panel, values=["Thủ thư", "Quản lý"])
        role.set("Thủ thư")
        role.grid(row=9, column=0, padx=18, pady=(0, 14), sticky="ew")

        def submit():
            employee_id = self.eligible.get(employee.get())
            try:
                if employee_id is None:
                    raise ValueError("Vui lòng chọn nhân viên trong danh sách.")
                role_code = "QUANLY" if role.get() == "Quản lý" else "THUTHU"
                create_employee_account(employee_id, login.get(), password.get(), role_code)
            except (pyodbc.Error, ValueError) as error:
                messagebox.showerror("Không thể tạo", _friendly_db_error(error), parent=dialog)
                return
            created_login = login.get().strip()
            dialog.destroy()
            self.refresh_accounts()
            if self.tree.exists(str(employee_id)):
                self.tree.selection_set(str(employee_id))
                self.tree.see(str(employee_id))
                self._on_select()
            messagebox.showinfo(
                "Thành công", f"Đã tạo tài khoản '{created_login}'.", parent=self,
            )

        buttons = ctk.CTkFrame(panel, fg_color="transparent")
        buttons.grid(row=10, column=0, padx=18, pady=(4, 18), sticky="e")
        ctk.CTkButton(
            buttons, text="Hủy", width=110, fg_color="#4B5563",
            hover_color="#374151", command=dialog.destroy,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            buttons, text="Tạo tài khoản", width=145, fg_color="#2563EB",
            hover_color="#1D4ED8", command=submit,
        ).pack(side="left")
        dialog.bind("<Return>", lambda _event: submit())
        login.focus_set()
        return dialog

    def _open_role_dialog(self, row: Dict[str, Any]):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Đổi nhóm quyền")
        dialog.geometry("430x280")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        panel = ctk.CTkFrame(dialog)
        panel.pack(fill="both", expand=True, padx=18, pady=18)
        panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            panel, text="ĐỔI NHÓM QUYỀN", font=ctk.CTkFont(size=19, weight="bold"),
        ).grid(row=0, column=0, padx=18, pady=(18, 4), sticky="w")
        ctk.CTkLabel(
            panel, text=f"{row['HoTen']} • {row['LoginName']}", text_color="gray",
        ).grid(row=1, column=0, padx=18, pady=(0, 16), sticky="w")
        ctk.CTkLabel(panel, text="Nhóm quyền mới", anchor="w").grid(
            row=2, column=0, padx=18, pady=(0, 3), sticky="ew")
        role = ctk.CTkOptionMenu(panel, values=["Thủ thư", "Quản lý"])
        role.set(self._role_label(row["RoleName"]) or "Thủ thư")
        role.grid(row=3, column=0, padx=18, pady=(0, 18), sticky="ew")

        def submit():
            role_code = "QUANLY" if role.get() == "Quản lý" else "THUTHU"
            try:
                change_account_role(row["MANV"], role_code)
            except (pyodbc.Error, ValueError) as error:
                messagebox.showerror("Không thể đổi quyền", _friendly_db_error(error), parent=dialog)
                return
            dialog.destroy()
            self.refresh_accounts()
            if self.tree.exists(str(row["MANV"])):
                self.tree.selection_set(str(row["MANV"]))
                self._on_select()
            messagebox.showinfo(
                "Thành công",
                f"Đã đổi nhóm quyền của '{row['LoginName']}' thành {self._role_label(role_code)}.",
                parent=self,
            )

        buttons = ctk.CTkFrame(panel, fg_color="transparent")
        buttons.grid(row=4, column=0, padx=18, pady=(0, 18), sticky="e")
        ctk.CTkButton(
            buttons, text="Hủy", width=100, fg_color="#4B5563",
            hover_color="#374151", command=dialog.destroy,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            buttons, text="Lưu thay đổi", width=130, fg_color="#7C3AED",
            hover_color="#6D28D9", command=submit,
        ).pack(side="left")
        return dialog

    def on_delete(self) -> None:
        row = self._selected_row()
        if not row:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn tài khoản cần xóa!")
            return
        if not row["DaCoTaiKhoan"]:
            messagebox.showwarning("Chưa có tài khoản", "Nhân viên này chưa có tài khoản để xóa.")
            return
        if row["LoginName"] == self.current_user.get("LoginName"):
            messagebox.showwarning("Không thể xóa", "Không thể xóa chính tài khoản đang đăng nhập.")
            return
        if not messagebox.askyesno(
            "Xác nhận xóa",
            "Bạn có chắc chắn muốn xóa tài khoản này không?\n\n"
            f"Tài khoản: {row['LoginName']}\nNhân viên: {row['HoTen']}",
        ):
            return
        try:
            delete_employee_account(row["MANV"])
        except (pyodbc.Error, ValueError) as error:
            messagebox.showerror("Không thể xóa", _friendly_db_error(error))
            return
        messagebox.showinfo("Thành công", f"Đã xóa tài khoản {row['LoginName']}.")
        self.refresh_accounts()

    def on_reset_password(self) -> None:
        row = self._selected_row()
        if not row or not row["DaCoTaiKhoan"]:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một nhân viên đã có tài khoản!")
            return
        if row["LoginName"] == self.current_user.get("LoginName"):
            messagebox.showwarning("Không thể reset",
                                   "Đây là tài khoản của bạn. Hãy dùng chức năng 'Đổi mật khẩu'.")
            return
        if not messagebox.askyesno(
            "Xác nhận reset mật khẩu",
            f"Đặt lại mật khẩu của '{row['LoginName']}' ({row['HoTen']}) "
            f"về mặc định '{DEFAULT_RESET_PASSWORD}'?",
        ):
            return
        try:
            password = reset_employee_password(row["MANV"])
        except (pyodbc.Error, ValueError) as error:
            messagebox.showerror("Không thể reset", _friendly_db_error(error))
            return
        messagebox.showinfo("Thành công",
                            f"Mật khẩu của '{row['LoginName']}' đã được đặt lại thành '{password}'.")

    # ------------------------------------------- new employee + account dialog
    def open_new_employee_form(self):
        """One dialog that creates both NHANVIEN and its login (it is an ADD form by nature)."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Thêm nhân viên và tài khoản")
        dialog.geometry("620x690")
        dialog.minsize(560, 620)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        panel = ctk.CTkScrollableFrame(dialog, corner_radius=0)
        panel.pack(fill="both", expand=True, padx=14, pady=14)
        panel.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(panel, text="THÊM NHÂN VIÊN VÀ TẠO TÀI KHOẢN",
                     font=ctk.CTkFont(size=19, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(8, 4), sticky="w")
        ctk.CTkLabel(panel, text="Một lần lưu sẽ tạo hồ sơ NHANVIEN và tài khoản SQL Server.",
                     text_color="gray").grid(row=1, column=0, columnspan=2, padx=12,
                                             pady=(0, 14), sticky="w")

        entries: Dict[str, ctk.CTkEntry] = {}
        for column, (key, label, placeholder) in enumerate((
            ("family_name", "Họ *", "Ví dụ: Nguyễn"), ("given_name", "Tên *", "Ví dụ: An"),
        )):
            ctk.CTkLabel(panel, text=label, anchor="w").grid(row=2, column=column, padx=12,
                                                             pady=(5, 2), sticky="ew")
            entries[key] = ctk.CTkEntry(panel, placeholder_text=placeholder)
            entries[key].grid(row=3, column=column, padx=12, pady=(0, 5), sticky="ew")

        row_index = 4
        for key, label, placeholder in (
            ("address", "Địa chỉ", "Địa chỉ liên hệ"),
            ("phone", "Điện thoại", "10 đến 11 chữ số"),
            ("email", "Email", "Ví dụ: an@library.local"),
            ("login_name", "Tên đăng nhập *", "Do quản lý tự đặt, vd: nv_an"),
            ("password", "Mật khẩu *", "Ít nhất 6 ký tự"),
        ):
            ctk.CTkLabel(panel, text=label, anchor="w").grid(row=row_index, column=0, columnspan=2,
                                                             padx=12, pady=(5, 2), sticky="ew")
            entries[key] = ctk.CTkEntry(panel, placeholder_text=placeholder,
                                        show="*" if key == "password" else "")
            entries[key].grid(row=row_index + 1, column=0, columnspan=2, padx=12,
                              pady=(0, 5), sticky="ew")
            row_index += 2

        ctk.CTkLabel(panel, text="Giới tính", anchor="w").grid(row=row_index, column=0, padx=12,
                                                               pady=(5, 2), sticky="ew")
        ctk.CTkLabel(panel, text="Nhóm quyền", anchor="w").grid(row=row_index, column=1, padx=12,
                                                                pady=(5, 2), sticky="ew")
        gender_option = ctk.CTkOptionMenu(panel, values=["Nữ", "Nam"])
        gender_option.set("Nam")
        gender_option.grid(row=row_index + 1, column=0, padx=12, pady=(0, 12), sticky="ew")
        role_option = ctk.CTkOptionMenu(panel, values=self.ROLE_VALUES)
        role_option.set("THUTHU")
        role_option.grid(row=row_index + 1, column=1, padx=12, pady=(0, 12), sticky="ew")

        def submit():
            try:
                employee_id = create_employee_with_account(
                    entries["family_name"].get(), entries["given_name"].get(),
                    gender_option.get() == "Nam", entries["address"].get(),
                    entries["phone"].get(), entries["email"].get(),
                    entries["login_name"].get(), entries["password"].get(), role_option.get(),
                )
            except (pyodbc.Error, ValueError) as error:
                messagebox.showerror("Không thể tạo", _friendly_db_error(error), parent=dialog)
                return
            except Exception:
                messagebox.showerror(
                    "Không thể tạo",
                    "Không thể tạo nhân viên và tài khoản. Vui lòng thử lại.",
                    parent=dialog,
                )
                return
            dialog.destroy()
            self.refresh_accounts()
            if self.tree.exists(str(employee_id)):
                self.tree.selection_set(str(employee_id))
                self.tree.see(str(employee_id))
            messagebox.showinfo("Thành công",
                                f"Đã tạo nhân viên mã {employee_id} và tài khoản SQL Server.",
                                parent=self)

        ctk.CTkButton(panel, text="Ghi nhân viên và tạo tài khoản", height=42,
                      font=ctk.CTkFont(weight="bold"), command=submit).grid(
            row=row_index + 2, column=0, columnspan=2, padx=12, pady=(5, 6), sticky="ew")
        ctk.CTkButton(panel, text="Hủy", height=36, fg_color="#4B5563", hover_color="#374151",
                      command=dialog.destroy).grid(
            row=row_index + 3, column=0, columnspan=2, padx=12, pady=(0, 16), sticky="ew")
        dialog.bind("<Return>", lambda _event: submit())
        entries["family_name"].focus_set()
        return dialog


class ChangePasswordDialog(ctk.CTkToplevel):
    """Hộp thoại Đổi mật khẩu cá nhân: kiểm tra mật khẩu cũ trực tiếp ở tầng SQL Server."""

    def __init__(self, master, login_name: str):
        super().__init__(master)
        self.title("Đổi mật khẩu")
        self.geometry("420x400")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        ctk.CTkLabel(self, text="ĐỔI MẬT KHẨU", font=ctk.CTkFont(size=18, weight="bold")).pack(
            pady=(18, 2))
        ctk.CTkLabel(self, text=f"Tài khoản: {login_name}", text_color="gray").pack(pady=(0, 12))

        self.entries = {}
        for key, label in (("old", "Mật khẩu cũ *"), ("new", "Mật khẩu mới * (ít nhất 6 ký tự)"),
                           ("confirm", "Nhập lại mật khẩu mới *")):
            ctk.CTkLabel(self, text=label, anchor="w").pack(fill="x", padx=30)
            entry = ctk.CTkEntry(self, show="*", height=34)
            entry.pack(fill="x", padx=30, pady=(2, 8))
            self.entries[key] = entry

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(pady=(10, 0))
        self.btn_save = ctk.CTkButton(bar, text="Ghi", width=120, fg_color="#059669",
                                      hover_color="#047857", command=self.on_save)
        self.btn_save.pack(side="left", padx=6)
        ctk.CTkButton(bar, text="Hủy", width=120, fg_color="#4B5563", hover_color="#374151",
                      command=self.destroy).pack(side="left", padx=6)
        self.bind("<Return>", lambda _e: self.on_save())
        self.entries["old"].focus_set()

    def on_save(self) -> None:
        try:
            change_own_password(self.entries["old"].get(), self.entries["new"].get(),
                                self.entries["confirm"].get())
        except ValueError as error:
            messagebox.showwarning("Không thể đổi mật khẩu", str(error), parent=self)
            return
        except pyodbc.Error as error:
            messagebox.showerror("Không thể đổi mật khẩu",
                                 friendly_message(error) or server_message(error), parent=self)
            return
        messagebox.showinfo("Thành công", "Đã đổi mật khẩu. Lần đăng nhập sau hãy dùng mật khẩu mới.",
                            parent=self)
        self.destroy()
