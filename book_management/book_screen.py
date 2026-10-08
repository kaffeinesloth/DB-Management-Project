"""Book management interface widgets only."""

import customtkinter as ctk


class BookScreen(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master)
        ctk.CTkLabel(self, text="Book Management", font=("Arial", 24, "bold")).pack(pady=30)
        ctk.CTkEntry(self, placeholder_text="Book title", width=360).pack(pady=8)
        ctk.CTkEntry(self, placeholder_text="Author", width=360).pack(pady=8)
        ctk.CTkButton(self, text="Add book (coming soon)", state="disabled").pack(pady=16)
