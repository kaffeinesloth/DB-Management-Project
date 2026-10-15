"""Application entry point."""

import customtkinter as ctk

from dashboard import Dashboard


class LibraryApplication(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Library Management System")
        self.geometry("1000x650")
        self.minsize(800, 500)
        Dashboard(self).pack(fill="both", expand=True)


if __name__ == "__main__":
    ctk.set_appearance_mode("system")
    LibraryApplication().mainloop()
