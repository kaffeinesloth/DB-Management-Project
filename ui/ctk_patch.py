"""
ctk_patch.py: Khắc phục triệt để lỗi mất placeholder text của CustomTkinter CTkEntry khi làm mới form.

Nguyên nhân kỹ thuật:
1. CustomTkinter (CTkEntry) mặc định khởi tạo `self._is_focused = True` trong `__init__`.
2. Khi gọi `entry.delete(0, "end")`, code gốc kiểm tra:
   `if not self._is_focused and self._entry.get() == "": self._activate_placeholder()`
   Vì `_is_focused` luôn là True (hoặc vẫn là True khi bấm nút vì click chuột vào button
   trong Tkinter không tự chuyển focus khỏi Entry), điều kiện trên bị False.
3. Hậu quả: `self._entry.delete()` đã xóa toàn bộ chuỗi ký tự hiển thị (kể cả placeholder),
   nhưng `_activate_placeholder()` không được gọi lại, khiến ô nhập bị rỗng hoàn toàn.

Module này áp dụng cơ chế Monkey-patch tự động ngay khi import:
- Đặt `self._is_focused = False` khi khởi tạo widget.
- Khi gọi `entry.delete(...)`, nếu entry trống và có `placeholder_text`, tự động
  nhả focus và kích hoạt lại `_activate_placeholder()`.
"""

import customtkinter as ctk

_is_patched = False

def apply_ctk_entry_patch():
    global _is_patched
    if _is_patched:
        return
    _is_patched = True

    # 1. Patch __init__ để _is_focused khởi tạo là False thay vì True
    orig_init = ctk.CTkEntry.__init__

    def patched_init(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        self._is_focused = False

    ctk.CTkEntry.__init__ = patched_init

    # 2. Patch delete để tự khôi phục placeholder khi xóa trắng ô nhập
    orig_delete = ctk.CTkEntry.delete

    def patched_delete(self, first_index, last_index=None):
        orig_delete(self, first_index, last_index)
        if self._placeholder_text is not None and self._entry.get() == "":
            try:
                # Nếu widget đang giữ keyboard focus, nhả focus về cửa sổ cha để tránh gõ đè
                if self.focus_get() == self._entry:
                    top = self.winfo_toplevel()
                    if top:
                        top.focus_set()
            except Exception:
                pass
            self._is_focused = False
            self._activate_placeholder()

    ctk.CTkEntry.delete = patched_delete


def reset_entry(entry: ctk.CTkEntry) -> None:
    """
    Hàm tiện ích giúp làm mới 1 ô CTkEntry an toàn và luôn bảo toàn placeholder_text.
    """
    if entry is not None:
        entry.delete(0, "end")


# Tự động kích hoạt bản vá khi import module
apply_ctk_entry_patch()
