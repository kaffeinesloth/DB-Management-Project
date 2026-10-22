"""
ctk_patch.py: Khắc phục triệt để lỗi mất placeholder text của CustomTkinter CTkEntry khi làm mới form.
"""

import customtkinter as ctk

_is_patched = False

def apply_ctk_entry_patch():
    global _is_patched
    if _is_patched:
        return
    _is_patched = True

    orig_init = ctk.CTkEntry.__init__

    def patched_init(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        self._is_focused = False

    ctk.CTkEntry.__init__ = patched_init

    orig_delete = ctk.CTkEntry.delete

    def patched_delete(self, first_index, last_index=None):
        orig_delete(self, first_index, last_index)
        if getattr(self, "_placeholder_text", None) is not None and self._entry.get() == "":
            try:
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
    """Hàm tiện ích giúp làm mới 1 ô CTkEntry an toàn và luôn bảo toàn placeholder_text."""
    if entry is not None:
        entry.delete(0, "end")


apply_ctk_entry_patch()
