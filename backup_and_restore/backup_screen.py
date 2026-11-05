"""Backup and restore interface widgets."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Callable, Dict, Optional

import customtkinter as ctk

from backup_and_restore.backup_actions import BackupActions, get_backup_path
from database import CURRENT_SESSION


class BackupScreen(ctk.CTkFrame):
    """Màn hình Sao lưu & Phục hồi CSDL SQL Server."""

    POLL_MS = 150

    def __init__(self, master, current_user: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(master, fg_color="transparent")
        self.current_user = current_user or CURRENT_SESSION.get("user_info") or {}

        self._busy = False
        self._poll_after_id: Optional[str] = None
        self._rows: Dict[str, Dict[str, Any]] = {}

        self._build_ui()
        self.load_history()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Header
        top_frame = ctk.CTkFrame(self, corner_radius=12)
        top_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")

        ctk.CTkLabel(
            top_frame,
            text="SAO LƯU & PHỤC HỒI CƠ SỞ DỮ LIỆU",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left", padx=20, pady=16)

        ctk.CTkLabel(
            top_frame,
            text=f"Tệp: {get_backup_path()}",
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray70"),
        ).pack(side="right", padx=20)

        # 2. Main content
        content_frame = ctk.CTkFrame(self, corner_radius=12)
        content_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        # 2.1 Left: backup history table
        left = ctk.CTkFrame(content_frame, fg_color="transparent")
        left.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left,
            text="Lịch sử các bản sao lưu (bản mới nhất ở đầu):",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        tree_container = tk.Frame(left, bg="#1E2229")
        tree_container.grid(row=1, column=0, sticky="nsew")
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        cols = ("position", "name", "date", "size", "user")
        self.tree = ttk.Treeview(tree_container, columns=cols, show="headings", selectmode="browse")
        headings = {
            "position": ("Bản Số", 70, "center"),
            "name": ("Tên Bản Sao Lưu", 300, "w"),
            "date": ("Thời Điểm Backup", 160, "center"),
            "size": ("Kích Thước (MB)", 110, "e"),
            "user": ("Người Thực Hiện", 120, "center"),
        }
        for col, (text, width, anchor) in headings.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=anchor, stretch=(col == "name"))

        self.tree.tag_configure("oddrow", background="#1A1D24")
        self.tree.tag_configure("evenrow", background="#222630")

        scroll_y = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")

        # 2.2 Right: controls
        right = ctk.CTkFrame(content_frame, width=330, corner_radius=10)
        right.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="ns")

        ctk.CTkLabel(right, text="Thao Tác Bảo Trì", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(15, 12))

        ctk.CTkLabel(
            right, text="Diễn giải / Ghi chú bản sao lưu:", font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=20, pady=(5, 2))
        self.txt_note = ctk.CTkEntry(
            right, placeholder_text="VD: Bản sao lưu trước khi nhập sách đợt 2", width=290
        )
        self.txt_note.pack(padx=20, pady=(0, 10))

        self.var_reset = tk.BooleanVar(value=False)
        self.chk_reset = ctk.CTkCheckBox(
            right,
            text="Xóa tất cả các bản sao lưu cũ\ntrong tệp (Reset / WITH INIT)",
            variable=self.var_reset,
            font=ctk.CTkFont(size=12),
        )
        self.chk_reset.pack(anchor="w", padx=20, pady=(0, 12))

        btn_style = {"font": ctk.CTkFont(size=13, weight="bold"), "height": 38, "width": 290}

        self.btn_create = ctk.CTkButton(
            right, text="💾 Tạo Bản Sao Lưu", fg_color="#10B981", hover_color="#059669",
            command=self._handle_create_backup, **btn_style,
        )
        self.btn_create.pack(padx=20, pady=6)

        self.btn_restore = ctk.CTkButton(
            right, text="♻ Phục Hồi Dữ Liệu (Restore)", fg_color="#DC2626", hover_color="#B91C1C",
            command=self._handle_restore, **btn_style,
        )
        self.btn_restore.pack(padx=20, pady=6)

        self.btn_verify = ctk.CTkButton(
            right, text="🔍 Kiểm Tra Bản Sao Lưu (Verify)", fg_color="#3B82F6", hover_color="#2563EB",
            command=self._handle_verify_backup, **btn_style,
        )
        self.btn_verify.pack(padx=20, pady=6)

        self.btn_refresh = ctk.CTkButton(
            right, text="🔄 Làm Mới Danh Sách",
            fg_color=("#E5E7EB", "#374151"), text_color=("#111827", "#F9FAFB"),
            command=self.load_history, **btn_style,
        )
        self.btn_refresh.pack(padx=20, pady=6)

        # Loading indicator
        self.lbl_status = ctk.CTkLabel(
            right, text="", font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#B45309", "#FBBF24"), wraplength=290, justify="left",
        )
        self.lbl_status.pack(anchor="w", padx=20, pady=(10, 2))
        self.progress = ctk.CTkProgressBar(right, mode="indeterminate", width=290)

        # Note
        note_box = ctk.CTkFrame(right, fg_color=("#FEF3C7", "#78350F"), corner_radius=8)
        note_box.pack(fill="x", padx=20, pady=(10, 15), side="bottom")
        ctk.CTkLabel(
            note_box, text="Lưu ý:", font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#92400E", "#FDE68A"),
        ).pack(anchor="w", padx=10, pady=(8, 2))
        ctk.CTkLabel(
            note_box,
            text=(
                "• Mặc định: nối tiếp bản mới vào tệp (WITH NOINIT).\n"
                "• Phục hồi sẽ ngắt mọi kết nối khác tới CSDL và ghi đè "
                "toàn bộ dữ liệu hiện tại về thời điểm của bản đã chọn."
            ),
            font=ctk.CTkFont(size=10), text_color=("#92400E", "#FDE68A"),
            wraplength=270, justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 8))

    # -------------------------------------------------------- busy / thread
    def _set_busy(self, busy: bool, message: str = "") -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        for w in (self.btn_create, self.btn_restore, self.btn_verify,
                  self.btn_refresh, self.chk_reset, self.txt_note):
            w.configure(state=state)
        self.lbl_status.configure(text=message)
        if busy:
            self.progress.pack(padx=20, pady=(0, 8), after=self.lbl_status)
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.pack_forget()
        try:
            self.winfo_toplevel().configure(cursor="watch" if busy else "")
        except Exception:
            pass

    def _run_in_background(
        self,
        message: str,
        job: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """Chạy `job` trên thread riêng để giao diện không bị treo."""
        if self._busy:
            return
        self._set_busy(True, message)
        result: Dict[str, Any] = {}

        def worker() -> None:
            try:
                result["value"] = job()
            except Exception as ex:  # noqa: BLE001 - shown to the user
                result["error"] = ex
            finally:
                result["done"] = True

        threading.Thread(target=worker, daemon=True).start()

        def poll() -> None:
            self._poll_after_id = None
            if not self.winfo_exists():
                return
            if not result.get("done"):
                self._poll_after_id = self.after(self.POLL_MS, poll)
                return
            self._set_busy(False)
            if "error" in result:
                on_error(result["error"])
            else:
                on_success(result.get("value"))

        self._poll_after_id = self.after(self.POLL_MS, poll)

    def destroy(self) -> None:
        if self._poll_after_id is not None:
            try:
                self.after_cancel(self._poll_after_id)
            except Exception:
                pass
            self._poll_after_id = None
        super().destroy()

    # ------------------------------------------------------------ actions
    def load_history(self) -> None:
        """Nạp danh sách bản sao lưu từ VIEW dbo.v_LichSuBackup."""
        if self._busy:
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._rows.clear()

        try:
            history = BackupActions.get_backup_history()
        except Exception as ex:
            self.lbl_status.configure(text=f"Không đọc được lịch sử sao lưu: {ex}")
            return

        self.lbl_status.configure(text="" if history else "Chưa có bản sao lưu nào trong tệp.")
        for idx, h in enumerate(history):
            finished = h.get("NgayGioBackup")
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            iid = self.tree.insert("", "end", values=(
                h.get("position"),
                h.get("TenBanSaoLuu") or "",
                finished.strftime("%d/%m/%Y %H:%M:%S") if finished else "",
                f"{h.get('KichThuocMB') or 0:.2f}",
                h.get("NguoiSaoLuu") or "",
            ), tags=(tag,))
            self._rows[iid] = h

    def _selected_backup(self, action_name: str) -> Optional[Dict[str, Any]]:
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning(
                "Chưa chọn bản sao lưu",
                f"Vui lòng chọn 1 bản sao lưu trong danh sách để {action_name}!",
            )
            return None
        return self._rows.get(selected[0])

    def _handle_create_backup(self) -> None:
        reset = bool(self.var_reset.get())
        note = self.txt_note.get().strip()

        if reset and self.tree.get_children():
            if not messagebox.askyesno(
                "Xác nhận xóa bản sao lưu cũ",
                "Bạn đã chọn RESET tệp sao lưu (WITH FORMAT, INIT).\n\n"
                f"Toàn bộ {len(self.tree.get_children())} bản sao lưu cũ trong tệp sẽ bị XÓA "
                "và bản mới sẽ bắt đầu lại từ Bản số 1.\n\nBạn có chắc chắn muốn tiếp tục?",
                icon="warning",
            ):
                return

        def on_success(path: str) -> None:
            self.txt_note.delete(0, "end")
            self.var_reset.set(False)
            self.load_history()
            first = self.tree.get_children()
            pos = self._rows[first[0]].get("position") if first else "?"
            messagebox.showinfo(
                "Sao lưu thành công",
                f"Đã sao lưu toàn bộ CSDL thành công!\n\nBản số: {pos}\nTệp: {path}\n"
                f"Chế độ: {'WITH INIT (reset tệp)' if reset else 'WITH NOINIT (nối tiếp)'}",
            )

        def on_error(ex: Exception) -> None:
            messagebox.showerror("Lỗi Sao Lưu", f"Không thể tạo bản sao lưu:\n\n{ex}")

        self._run_in_background(
            "Đang sao lưu CSDL, vui lòng chờ...",
            lambda: BackupActions.create_backup(overwrite_old=reset, description=note),
            on_success, on_error,
        )

    def _handle_verify_backup(self) -> None:
        row = self._selected_backup("kiểm tra")
        if not row:
            return
        pos = row["position"]

        def on_success(_: Any) -> None:
            messagebox.showinfo(
                "Kết quả kiểm tra",
                f"Bản sao lưu số {pos} ('{row.get('TenBanSaoLuu')}') HỢP LỆ và có thể phục hồi.",
            )

        def on_error(ex: Exception) -> None:
            messagebox.showerror("Lỗi Kiểm Tra", f"Bản sao lưu số {pos} không hợp lệ:\n\n{ex}")

        self._run_in_background(
            f"Đang kiểm tra bản sao lưu số {pos}...",
            lambda: BackupActions.verify_backup(pos),
            on_success, on_error,
        )

    def _handle_restore(self) -> None:
        row = self._selected_backup("phục hồi")
        if not row:
            return
        pos = row["position"]
        finished = row.get("NgayGioBackup")
        when = finished.strftime("%d/%m/%Y %H:%M:%S") if finished else "?"

        if not messagebox.askyesno(
            "Xác nhận phục hồi dữ liệu",
            "CẢNH BÁO: Toàn bộ dữ liệu hiện tại sẽ bị GHI ĐÈ về thời điểm của bản sao lưu đã chọn!\n\n"
            f"Bản số: {pos}\nTên: {row.get('TenBanSaoLuu')}\nThời điểm: {when}\n\n"
            "Mọi thay đổi sau thời điểm này sẽ bị mất và các kết nối khác tới CSDL sẽ bị ngắt.\n\n"
            "Bạn có chắc chắn muốn phục hồi?",
            icon="warning",
        ):
            return

        def on_success(_: Any) -> None:
            self.load_history()
            messagebox.showinfo(
                "Phục hồi thành công",
                f"Đã phục hồi CSDL về Bản số {pos} ({when}).\n\n"
                "Vui lòng bấm 'Làm mới' ở các màn hình khác để tải lại dữ liệu.",
            )

        def on_error(ex: Exception) -> None:
            self.load_history()
            messagebox.showerror(
                "Lỗi Phục Hồi",
                f"Không thể phục hồi bản sao lưu số {pos}:\n\n{ex}\n\n"
                "CSDL đã được đưa về chế độ MULTI_USER.",
            )

        self._run_in_background(
            f"Đang phục hồi CSDL về Bản số {pos}...\nVui lòng không đóng ứng dụng.",
            lambda: BackupActions.restore_backup(pos),
            on_success, on_error,
        )
