"""Reusable button/input state machine for CRUD forms (Thêm - Xóa - Sửa - Ghi - Phục hồi).

Every data-entry screen follows the same three states:

    VIEW  (xem danh sách)  inputs LOCKED   | Thêm, Sửa, Xóa, Thoát ON  | Ghi, Phục hồi OFF
    ADD   (đang thêm)      inputs UNLOCKED, cleared, focus first field
                                           | Thêm, Sửa, Xóa, Thoát OFF | Ghi, Phục hồi ON
    EDIT  (đang sửa)       inputs UNLOCKED except the PRIMARY KEY
                                           | Thêm, Sửa, Xóa, Thoát OFF | Ghi, Phục hồi ON

The controller owns only widget states and form values; database work stays in
each screen's handlers.
"""

from enum import Enum
from tkinter import messagebox
from typing import Any, Callable, Dict, Iterable, Optional, Sequence

import customtkinter as ctk


def confirm_exit(widget: Any) -> None:
    """'Thoát': ask, then close the main window through its own close handler."""
    if not messagebox.askyesno("Thoát", "Bạn có chắc chắn muốn thoát chương trình?"):
        return
    window = widget.winfo_toplevel()
    close = getattr(window, "handle_close", None)
    if callable(close):
        close()          # MainDashboard.handle_close still blocks during backup/restore
    else:
        window.destroy()


class FormMode(Enum):
    VIEW = "view"
    ADD = "add"
    EDIT = "edit"


# Buttons that are ON while viewing and OFF while adding/editing (and vice versa).
LOCKED_TEXT_COLOR = ("gray45", "gray55")   # (light, dark) text of a locked input
VIEW_BUTTONS = ("add", "edit", "delete", "exit")
EDIT_BUTTONS = ("save", "cancel")


def _is_combo(widget: Any) -> bool:
    return isinstance(widget, ctk.CTkComboBox)


def get_value(widget: Any) -> str:
    """Read a widget value; text values are always strip()-ed before reaching the DB."""
    return str(widget.get()).strip()


def set_value(widget: Any, value: Any) -> None:
    """Write a value even if the widget is currently locked."""
    text = "" if value is None else str(value)
    if isinstance(widget, (ctk.CTkComboBox, ctk.CTkOptionMenu)):
        previous = widget.cget("state")
        widget.configure(state="normal")
        widget.set(text)
        widget.configure(state=previous)
        return
    previous = widget.cget("state")
    widget.configure(state="normal")
    widget.delete(0, "end")
    if text:
        widget.insert(0, text)
    widget.configure(state=previous)


COMMAND_BUTTONS = (
    # key,     text,         color,     hover
    ("add",    "Thêm",       "#2563EB", "#1D4ED8"),
    ("edit",   "Sửa",        "#7C3AED", "#6D28D9"),
    ("delete", "Xóa",        "#DC2626", "#B91C1C"),
    ("save",   "Ghi",        "#059669", "#047857"),
    ("cancel", "Phục hồi",   "#D97706", "#B45309"),
    ("exit",   "Thoát",      "#4B5563", "#374151"),
)


def build_command_bar(parent: Any, handlers: Dict[str, Callable[[], None]],
                      width: int = 92) -> Dict[str, Any]:
    """Create the standard Thêm / Sửa / Xóa / Ghi / Phục hồi / Thoát buttons (packed left)."""
    buttons: Dict[str, Any] = {}
    for key, text, color, hover in COMMAND_BUTTONS:
        if key not in handlers:
            continue
        button = ctk.CTkButton(
            parent, text=text, width=width, height=34, fg_color=color, hover_color=hover,
            font=ctk.CTkFont(size=13, weight="bold"), command=handlers[key],
        )
        button.pack(side="left", padx=(0, 6))
        buttons[key] = button
    return buttons


class FormStateController:
    """Drive the Thêm / Sửa / Xóa / Ghi / Phục hồi / Thoát state machine of one form."""

    def __init__(
        self,
        inputs: Dict[str, Any],
        buttons: Dict[str, Any],
        key_fields: Iterable[str] = (),
        locked_always: Iterable[str] = (),
        view_only_widgets: Sequence[Any] = (),
        defaults: Optional[Dict[str, Any]] = None,
        on_mode_change: Optional[Callable[["FormMode"], None]] = None,
    ) -> None:
        """
        inputs            : field name -> CTkEntry / CTkComboBox / CTkOptionMenu (form order).
        buttons           : keys among add, edit, delete, save, cancel, exit.
        key_fields        : primary-key fields -> editable only in ADD, locked in EDIT.
        locked_always     : fields the user never types into (e.g. IDENTITY "tự động").
        view_only_widgets : extra buttons usable only while viewing (gia hạn, khóa thẻ...).
        defaults          : values written into inputs when "Thêm" clears the form.
        """
        self.inputs = inputs
        self.buttons = buttons
        self.key_fields = set(key_fields)
        self.locked_always = set(locked_always)
        self.view_only_widgets = list(view_only_widgets)
        self.defaults = defaults or {}
        self.on_mode_change = on_mode_change
        self.mode = FormMode.VIEW
        self._snapshot: Dict[str, str] = {}
        self._text_colors: Dict[str, Any] = {}

    # ------------------------------------------------------------ helpers
    def _set_button(self, name: str, enabled: bool) -> None:
        button = self.buttons.get(name)
        if button is not None:
            button.configure(state="normal" if enabled else "disabled")

    def _set_input(self, name: str, enabled: bool) -> None:
        widget = self.inputs[name]
        # CTkEntry keeps the same text color when disabled; dim it so a LOCKED field
        # (e.g. the primary key while editing) is visibly different from an open one.
        if name not in self._text_colors:
            self._text_colors[name] = widget.cget("text_color")
        widget.configure(text_color=self._text_colors[name] if enabled else LOCKED_TEXT_COLOR)
        if not enabled:
            widget.configure(state="disabled")
        elif _is_combo(widget):
            # Foreign keys / choices: pick from the list only, no free typing.
            widget.configure(state="readonly")
        else:
            widget.configure(state="normal")

    def _apply(self, mode: FormMode) -> None:
        self.mode = mode
        editing = mode is not FormMode.VIEW
        for name in VIEW_BUTTONS:
            self._set_button(name, not editing)
        for name in EDIT_BUTTONS:
            self._set_button(name, editing)
        for widget in self.view_only_widgets:
            widget.configure(state="disabled" if editing else "normal")
        for name in self.inputs:
            unlocked = editing and name not in self.locked_always
            if mode is FormMode.EDIT and name in self.key_fields:
                unlocked = False                       # never edit the primary key
            self._set_input(name, unlocked)
        if self.on_mode_change:
            self.on_mode_change(mode)

    def _first_editable(self) -> Optional[Any]:
        for name, widget in self.inputs.items():
            if widget.cget("state") != "disabled":
                return widget
        return None

    # ------------------------------------------------------------- values
    def values(self) -> Dict[str, str]:
        return {name: get_value(widget) for name, widget in self.inputs.items()}

    def fill(self, record: Dict[str, Any]) -> None:
        """Show ``record`` in the form (used when a row is selected while viewing)."""
        for name, widget in self.inputs.items():
            if name in record:
                set_value(widget, record[name])

    def clear(self) -> None:
        for name, widget in self.inputs.items():
            set_value(widget, self.defaults.get(name, ""))

    # -------------------------------------------------------- transitions
    def to_view(self) -> None:
        """Default state: everything locked, Ghi / Phục hồi disabled."""
        self._apply(FormMode.VIEW)

    def to_add(self) -> None:
        """'Thêm': unlock, clear the form and focus the first input."""
        self._snapshot = self.values()
        self.clear()
        self._apply(FormMode.ADD)
        first = self._first_editable()
        if first is not None:
            first.focus_set()

    def to_edit(self) -> None:
        """'Sửa': unlock everything except the primary key."""
        self._snapshot = self.values()
        self._apply(FormMode.EDIT)
        first = self._first_editable()
        if first is not None:
            first.focus_set()

    def cancel(self) -> None:
        """'Phục hồi': discard the pending add/edit and show the original values."""
        for name, widget in self.inputs.items():
            set_value(widget, self._snapshot.get(name, ""))
        self._apply(FormMode.VIEW)

    @property
    def is_editing(self) -> bool:
        return self.mode is not FormMode.VIEW
