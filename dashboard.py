"""Main navigation dashboard."""

import customtkinter as ctk

from backup_and_restore.backup_screen import BackupScreen
from book_management.book_screen import BookScreen
from borrowing_and_returns.borrowing_screen import BorrowingScreen
from reader_management.reader_screen import ReaderScreen
from reports.report_screen import ReportScreen


class Dashboard(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master)
        navigation = ctk.CTkFrame(self, width=210)
        navigation.pack(side="left", fill="y", padx=(10, 5), pady=10)
        navigation.pack_propagate(False)
        self._content = ctk.CTkFrame(self)
        self._content.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        ctk.CTkLabel(navigation, text="Library Dashboard", font=("Arial", 18, "bold")).pack(pady=20)
        modules = (
            ("Books", BookScreen),
            ("Readers", ReaderScreen),
            ("Borrowing & Returns", BorrowingScreen),
            ("Reports", ReportScreen),
            ("Backup & Restore", BackupScreen),
        )
        for label, screen_class in modules:
            ctk.CTkButton(
                navigation, text=label,
                command=lambda selected=screen_class: self.show_screen(selected),
            ).pack(fill="x", padx=12, pady=6)
        self.show_screen(BookScreen)

    def show_screen(self, screen_class) -> None:
        for widget in self._content.winfo_children():
            widget.destroy()
        screen_class(self._content).pack(fill="both", expand=True)
