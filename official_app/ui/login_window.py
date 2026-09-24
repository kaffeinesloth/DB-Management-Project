"""Login window that authenticates directly with SQL Server."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import pyodbc

from database.security import LoginDemoError, authenticate
from models.session import UserSession


class LoginWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Library Management - SQL Server Login")
        self.geometry("480x390")
        self.resizable(False, False)
        self._login_in_progress = False
        self._main_window = None

        self.login_name_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.show_password_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="")

        self._build_ui()
        self._center_window()
        self.bind("<Return>", self._submit_from_event)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=28)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)

        ttk.Label(
            outer,
            text="LIBRARY MANAGEMENT SYSTEM",
            font=("Segoe UI", 17, "bold"),
            anchor="center",
        ).grid(row=0, column=0, sticky="ew", pady=(8, 4))
        ttk.Label(
            outer,
            text="Đăng nhập bằng tài khoản SQL Server",
            anchor="center",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 22))

        form = ttk.Frame(outer)
        form.grid(row=2, column=0, sticky="ew")
        form.columnconfigure(0, weight=1)

        ttk.Label(form, text="Login Name").grid(row=0, column=0, sticky="w")
        self.login_entry = ttk.Entry(
            form, textvariable=self.login_name_var, font=("Segoe UI", 11)
        )
        self.login_entry.grid(row=1, column=0, sticky="ew", pady=(5, 14), ipady=5)

        ttk.Label(form, text="Password").grid(row=2, column=0, sticky="w")
        self.password_entry = ttk.Entry(
            form,
            textvariable=self.password_var,
            show="*",
            font=("Segoe UI", 11),
        )
        self.password_entry.grid(row=3, column=0, sticky="ew", pady=(5, 6), ipady=5)

        ttk.Checkbutton(
            form,
            text="Hiện mật khẩu",
            variable=self.show_password_var,
            command=self._toggle_password,
        ).grid(row=4, column=0, sticky="w", pady=(0, 14))

        self.login_button = ttk.Button(
            form, text="ĐĂNG NHẬP", command=self._submit_login
        )
        self.login_button.grid(row=5, column=0, sticky="ew", ipady=6)

        self.status_label = ttk.Label(
            outer,
            textvariable=self.status_var,
            foreground="#b42318",
            wraplength=410,
            justify="center",
            anchor="center",
        )
        self.status_label.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        self.login_entry.focus_set()

    def _center_window(self) -> None:
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _toggle_password(self) -> None:
        self.password_entry.configure(show="" if self.show_password_var.get() else "*")

    def _submit_from_event(self, _event: tk.Event) -> str:
        self._submit_login()
        return "break"

    def _set_login_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.login_entry.configure(state=state)
        self.password_entry.configure(state=state)
        self.login_button.configure(state=state)

    def _submit_login(self) -> None:
        if self._login_in_progress:
            return

        login_name = self.login_name_var.get().strip()
        password = self.password_var.get()
        self.status_var.set("")

        if not login_name or not password:
            self.status_var.set("Vui lòng nhập đầy đủ Login Name và Password.")
            return

        self._login_in_progress = True
        self._set_login_enabled(False)
        self.status_var.set("Đang xác thực với SQL Server...")
        self.update_idletasks()

        try:
            session, connection = authenticate(login_name, password)
        except LoginDemoError as error:
            self.password_var.set("")
            self.status_var.set(str(error))
            self.password_entry.focus_set()
        except Exception:
            self.password_var.set("")
            self.status_var.set(
                "Không thể hoàn tất đăng nhập. Hãy kiểm tra cấu hình và thử lại."
            )
            self.password_entry.focus_set()
        else:
            self._open_main_window(session, connection)
        finally:
            self._login_in_progress = False
            if self.winfo_exists() and self.state() != "withdrawn":
                self._set_login_enabled(True)

    def _open_main_window(
        self, session: UserSession, connection: pyodbc.Connection
    ) -> None:
        from ui.main_window import MainWindow

        self.password_var.set("")
        self.status_var.set("")
        self.withdraw()
        self._main_window = MainWindow(
            parent=self,
            session=session,
            connection=connection,
            on_logout=self._return_to_login,
        )

    def _return_to_login(self) -> None:
        self._main_window = None
        self._login_in_progress = False
        self.login_name_var.set("")
        self.password_var.set("")
        self.show_password_var.set(False)
        self.password_entry.configure(show="*")
        self.status_var.set("")
        self._set_login_enabled(True)
        self.deiconify()
        self._center_window()
        self.login_entry.focus_set()
