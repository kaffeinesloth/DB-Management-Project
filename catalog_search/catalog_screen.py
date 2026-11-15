"""Read-only book-search screen for the shared DOCGIA account."""

from tkinter import messagebox, ttk

import customtkinter as ctk

from catalog_search.catalog_actions import search_catalog
from database import friendly_message, server_message


class CatalogSearchScreen(ctk.CTkFrame):
    """A deliberately small surface: search and read, with no mutation controls."""

    def __init__(self, parent, current_user=None):
        super().__init__(parent)
        self.current_user = current_user or {}
        self._build_ui()
        self.refresh_results()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            self, text="TRA CỨU SÁCH THƯ VIỆN",
            font=ctk.CTkFont(size=23, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(22, 4), sticky="w")
        ctk.CTkLabel(
            self,
            text="Tài khoản độc giả chỉ có quyền xem danh mục và tình trạng sách.",
            text_color="gray",
        ).grid(row=1, column=0, padx=24, pady=(0, 14), sticky="w")

        search_bar = ctk.CTkFrame(self)
        search_bar.grid(row=2, column=0, padx=24, pady=(0, 10), sticky="ew")
        search_bar.grid_columnconfigure(0, weight=1)
        self.search_entry = ctk.CTkEntry(
            search_bar,
            height=40,
            placeholder_text="Nhập tên sách, mã sách, ISBN, tác giả hoặc thể loại...",
        )
        self.search_entry.grid(row=0, column=0, padx=(12, 8), pady=12, sticky="ew")
        self.available_only = ctk.CTkCheckBox(search_bar, text="Chỉ sách có sẵn")
        self.available_only.grid(row=0, column=1, padx=8, pady=12)
        ctk.CTkButton(
            search_bar, text="Tìm kiếm", width=110, height=40,
            command=self.refresh_results,
        ).grid(row=0, column=2, padx=8, pady=12)
        ctk.CTkButton(
            search_bar, text="Xóa bộ lọc", width=110, height=40,
            fg_color="#475569", hover_color="#334155", command=self.clear_filters,
        ).grid(row=0, column=3, padx=(8, 12), pady=12)

        self.summary = ctk.CTkLabel(self, text="", text_color="#9CA3AF", anchor="w")
        self.summary.grid(row=3, column=0, padx=26, pady=(0, 6), sticky="ew")

        table_frame = ctk.CTkFrame(self)
        table_frame.grid(row=4, column=0, padx=24, pady=(0, 22), sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure(
            "Catalog.Treeview", rowheight=31, background="#1F2937",
            fieldbackground="#1F2937", foreground="#E5E7EB", borderwidth=0,
        )
        style.configure(
            "Catalog.Treeview.Heading", background="#111827", foreground="#F9FAFB",
            relief="flat", font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Catalog.Treeview", background=[("selected", "#2563EB")],
            foreground=[("selected", "#FFFFFF")],
        )

        columns = ("code", "isbn", "title", "author", "category", "status", "shelf", "publisher")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", style="Catalog.Treeview",
            selectmode="browse",
        )
        for name, label, width in (
            ("code", "Mã sách", 85), ("isbn", "ISBN", 95),
            ("title", "Tên sách", 220), ("author", "Tác giả", 180),
            ("category", "Thể loại", 120), ("status", "Tình trạng", 95),
            ("shelf", "Vị trí", 130), ("publisher", "Nhà xuất bản", 160),
        ):
            self.tree.heading(name, text=label)
            self.tree.column(
                name, width=width,
                anchor="center" if name in {"code", "isbn", "status", "shelf"} else "w",
            )
        self.tree.tag_configure("available", foreground="#34D399")
        self.tree.tag_configure("borrowed", foreground="#FBBF24")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.search_entry.bind("<Return>", lambda _event: self.refresh_results())

    def clear_filters(self) -> None:
        self.search_entry.delete(0, "end")
        if self.available_only.get():
            self.available_only.toggle()
        self.refresh_results()

    def refresh_results(self) -> None:
        try:
            rows = search_catalog(self.search_entry.get(), bool(self.available_only.get()))
        except Exception as error:
            messagebox.showerror(
                "Không thể tra cứu",
                friendly_message(error) or server_message(error) or str(error),
            )
            return

        self.tree.delete(*self.tree.get_children())
        available_count = 0
        for index, row in enumerate(rows):
            available = row["COSAN"]
            available_count += int(available)
            shelf = " / ".join(value for value in (row["KE"], row["VITRI"]) if value)
            self.tree.insert(
                "", "end", iid=str(index),
                values=(
                    row["MASACH"], row["ISBN"], row["TENSACH"], row["TACGIA"],
                    row["THELOAI"], "Có sẵn" if available else "Đang mượn",
                    shelf, row["NHAXB"],
                ),
                tags=("available" if available else "borrowed",),
            )
        self.summary.configure(
            text=f"Tìm thấy {len(rows)} cuốn • {available_count} cuốn đang có sẵn"
        )
