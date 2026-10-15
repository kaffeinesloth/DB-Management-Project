"""Login interface widgets only."""

import customtkinter as ctk


class LoginScreen(ctk.CTkFrame):
    def __init__(self, master, on_login) -> None:
        super().__init__(master)
        panel = ctk.CTkFrame(self)
        panel.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(panel, text="Library Login", font=("Arial", 24, "bold")).pack(
            padx=50, pady=(30, 18)
        )
        self.username_entry = ctk.CTkEntry(panel, placeholder_text="Username", width=280)
        self.username_entry.pack(padx=30, pady=8)
        self.password_entry = ctk.CTkEntry(panel, placeholder_text="Password", show="*", width=280)
        self.password_entry.pack(padx=30, pady=8)
        self.message_label = ctk.CTkLabel(panel, text="")
        self.message_label.pack(pady=4)
        ctk.CTkButton(
            panel,
            text="Log in",
            command=lambda: on_login(self.username_entry.get(), self.password_entry.get()),
        ).pack(pady=(8, 30))

    def show_message(self, message: str) -> None:
        self.message_label.configure(text=message)
