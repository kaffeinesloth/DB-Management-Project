"""Backup and restore interface widgets only."""

import customtkinter as ctk


class BackupScreen(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master)
        ctk.CTkLabel(self, text="Backup & Restore", font=("Arial", 24, "bold")).pack(pady=30)
        ctk.CTkButton(self, text="Coming soon", state="disabled").pack(pady=16)
