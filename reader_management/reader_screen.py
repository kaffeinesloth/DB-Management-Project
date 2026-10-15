"""Reader management interface widgets only."""

import customtkinter as ctk


class ReaderScreen(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master)
        ctk.CTkLabel(self, text="Reader Management", font=("Arial", 24, "bold")).pack(pady=30)
        ctk.CTkEntry(self, placeholder_text="Reader name", width=360).pack(pady=8)
        ctk.CTkEntry(self, placeholder_text="Email", width=360).pack(pady=8)
        ctk.CTkButton(self, text="Add reader (coming soon)", state="disabled").pack(pady=16)
