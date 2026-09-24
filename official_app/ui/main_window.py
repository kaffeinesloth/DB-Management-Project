"""Post-login placeholder window for the Chapter 5 security demo."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

import pyodbc

from models.session import UserSession


class MainWindow(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Tk,
        session: UserSession,
        connection: pyodbc.Connection,
        on_logout: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.session = session
        self._connection = connection
        self._on_logout = on_logout
        self._logging_out = False

        self.title("Library Management System")
        self.geometry("760x520")
        self.minsize(700, 480)
        self.protocol("WM_DELETE_WINDOW", self.logout)
        self._build_ui()
        self._center_window()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=30)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)

        ttk.Label(
            outer,
            text="Library Management System",
            font=("Segoe UI", 22, "bold"),
            anchor="center",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 22))

        info = ttk.LabelFrame(outer, text="Authenticated SQL Server Session", padding=18)
        info.grid(row=1, column=0, sticky="ew")
        info.columnconfigure(1, weight=1)

        values = (
            ("Employee ID", str(self.session.employee_id)),
            ("Full Name", self.session.full_name),
            ("SQL Login", self.session.login_name),
            ("Database User", self.session.database_user),
            ("Role(s)", ", ".join(self.session.roles)),
        )
        for row_number, (label, value) in enumerate(values):
            ttk.Label(info, text=f"{label}:", font=("Segoe UI", 10, "bold")).grid(
                row=row_number, column=0, sticky="nw", padx=(0, 18), pady=5
            )
            ttk.Label(info, text=value, wraplength=500).grid(
                row=row_number, column=1, sticky="nw", pady=5
            )

        placeholder = ttk.LabelFrame(outer, text="Modules (demo placeholders)", padding=16)
        placeholder.grid(row=2, column=0, sticky="ew", pady=(22, 0))
        for column in range(3):
            placeholder.columnconfigure(column, weight=1)

        buttons = (
            "Quản lý sách",
            "Quản lý độc giả",
            "Mượn / Trả sách",
            "Báo cáo",
            "Quản trị",
        )
        for index, title in enumerate(buttons):
            ttk.Button(placeholder, text=title, state="disabled").grid(
                row=index // 3,
                column=index % 3,
                sticky="ew",
                padx=5,
                pady=5,
                ipady=4,
            )

        ttk.Button(outer, text="Logout", command=self.logout).grid(
            row=3, column=0, pady=(24, 0), ipadx=26, ipady=5
        )

    def _center_window(self) -> None:
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def logout(self) -> None:
        if self._logging_out:
            return
        self._logging_out = True
        try:
            self._connection.close()
        finally:
            self.destroy()
            self._on_logout()

