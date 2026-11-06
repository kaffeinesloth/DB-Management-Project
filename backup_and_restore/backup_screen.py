"""Backup and restore interface widgets."""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from typing import Dict, Any, Optional
from backup_and_restore.backup_actions import BackupActions
from database import CURRENT_SESSION


class BackupScreen(ctk.CTkFrame):
    """Màn hình Sao lưu & Phục hồi CSDL SQL Server."""

    def __init__(self, master, current_user: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(master, fg_color="transparent")
        self.current_user = current_user or CURRENT_SESSION.get("user_info") or {}

        self._build_ui()
        self.load_history()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Header & Actions bar
        top_frame = ctk.CTkFrame(self, corner_radius=12)
        top_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")

        ctk.CTkLabel(
            top_frame,
            text="SAO LƯU & PHỤC HỒI CƠ SỞ DỮ LIỆU",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left", padx=20, pady=16)

        # 2. Main content container
        content_frame = ctk.CTkFrame(self, corner_radius=12)
        content_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=0)
        content_frame.grid_rowconfigure(0, weight=1)

        # 2.1 Left: Backup History Table
        left_table_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_table_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        left_table_frame.grid_rowconfigure(1, weight=1)
        left_table_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left_table_frame,
            text="Lịch sử các bản sao lưu (.BAK):",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        # Treeview
        tree_container = tk.Frame(left_table_frame, bg="#1E2229")
        tree_container.grid(row=1, column=0, sticky="nsew")
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        cols = ("filename", "database", "date", "size", "user")
        self.tree = ttk.Treeview(tree_container, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("filename", text="Tên Tệp Sao Lưu (.BAK)")
        self.tree.heading("database", text="CSDL")
        self.tree.heading("date", text="Thời Điểm Hoàn Thành")
        self.tree.heading("size", text="Kích Thước (MB)")
        self.tree.heading("user", text="Tài Khoản Thực Hiện")

        self.tree.column("filename", width=250, anchor="w")
        self.tree.column("database", width=120, anchor="center")
        self.tree.column("date", width=160, anchor="center")
        self.tree.column("size", width=110, anchor="e")
        self.tree.column("user", width=100, anchor="center")

        scroll_y = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")

        # 2.2 Right: Operation Controls
        right_panel = ctk.CTkFrame(content_frame, width=320, corner_radius=10)
        right_panel.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="ns")
        right_panel.pack_propagate(False)

        ctk.CTkLabel(
            right_panel,
            text="Thao Tác Bảo Trì",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(15, 12))

        ctk.CTkLabel(right_panel, text="Tên tệp backup (tùy chọn):", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(5, 2))
        self.txt_backup_name = ctk.CTkEntry(
            right_panel,
            placeholder_text="Để trống để tự tạo timestamp...",
            width=280
        )
        self.txt_backup_name.pack(padx=20, pady=(0, 15))

        self.btn_create = ctk.CTkButton(
            right_panel,
            text="💾 Tạo Bản Sao Lưu Ngay",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            width=280,
            fg_color="#10B981",
            hover_color="#059669",
            command=self._handle_create_backup
        )
        self.btn_create.pack(padx=20, pady=8)

        self.btn_verify = ctk.CTkButton(
            right_panel,
            text="🔍 Kiểm Tra Bản Sao Lưu (Verify)",
            font=ctk.CTkFont(size=13),
            height=36,
            width=280,
            fg_color="#3B82F6",
            hover_color="#2563EB",
            command=self._handle_verify_backup
        )
        self.btn_verify.pack(padx=20, pady=8)

        ctk.CTkButton(
            right_panel,
            text="🔄 Làm Mới Danh Sách",
            font=ctk.CTkFont(size=13),
            height=36,
            width=280,
            fg_color=("#E5E7EB", "#374151"),
            text_color=("#111827", "#F9FAFB"),
            command=self.load_history
        ).pack(padx=20, pady=8)

        # Warning & Note
        note_box = ctk.CTkFrame(right_panel, fg_color=("#FEF3C7", "#78350F"), corner_radius=8)
        note_box.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            note_box,
            text="Lưu ý kỹ thuật:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#92400E", "#FDE68A")
        ).pack(anchor="w", padx=10, pady=(8, 2))

        ctk.CTkLabel(
            note_box,
            text="Bản sao lưu được lưu trữ an toàn trong phân vùng Docker Volume (/var/opt/mssql/backups).",
            font=ctk.CTkFont(size=10),
            text_color=("#92400E", "#FDE68A"),
            wraplength=260,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 8))

    def load_history(self) -> None:
        """Nạp danh sách các bản backup từ CSDL."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        history = BackupActions.get_backup_history()
        for h in history:
            self.tree.insert("", "end", values=(
                h.get("filename"),
                h.get("database_name"),
                h.get("date_str"),
                h.get("SizeMB"),
                h.get("user_name")
            ))

    def _handle_create_backup(self) -> None:
        custom_name = self.txt_backup_name.get().strip()
        self.btn_create.configure(state="disabled", text="Đang tạo backup...")
        self.update_idletasks()

        try:
            filename = BackupActions.create_backup(custom_name if custom_name else None)
            messagebox.showinfo("Thành công", f"Đã sao lưu thành công CSDL!\nTệp sao lưu: {filename}")
            self.txt_backup_name.delete(0, "end")
            self.load_history()
        except Exception as ex:
            messagebox.showerror("Lỗi Sao Lưu", f"Không thể tạo sao lưu:\n{ex}")
        finally:
            self.btn_create.configure(state="normal", text="💾 Tạo Bản Sao Lưu Ngay")

    def _handle_verify_backup(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Chưa chọn tệp", "Vui lòng chọn 1 bản sao lưu trong danh sách để kiểm tra!")
            return

        item = self.tree.item(selected[0])
        filename = item["values"][0]

        try:
            BackupActions.verify_backup(filename)
            messagebox.showinfo("Kết quả kiểm tra", f"Bản sao lưu '{filename}' HỢP LỆ VÀ NGUYÊN VẸN 100%!")
        except Exception as ex:
            messagebox.showerror("Lỗi Kiểm Tra", f"Tệp sao lưu không hợp lệ:\n{ex}")
