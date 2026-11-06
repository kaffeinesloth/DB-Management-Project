"""Báo cáo thống kê: thẻ KPI, độc giả quá hạn, tần suất sử dụng sách,
sách cần xem xét thanh lý và thống kê tổng hợp theo tháng / quý / năm."""

from datetime import date
from tkinter import filedialog, ttk
from typing import Any, Dict, Optional

import customtkinter as ctk
import pyodbc

from database import CURRENT_SESSION
from reports import report_actions as actions


TABS = ("Độc giả quá hạn", "Tần suất sử dụng", "Sách cần xem xét", "Thống kê tổng hợp")
PERIOD_TYPES = ("Tháng", "Quý", "Năm")
KPI_COLOR = "#3B82F6"
ERROR_COLOR = ("#b3261e", "#f2b8b5")
TEXT_COLOR = ("gray10", "gray90")


class ReportScreen(ctk.CTkFrame):
    def __init__(self, master, current_user: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(master, fg_color="transparent")
        self.current_user = current_user or CURRENT_SESSION.get("user_info") or {}
        self._result: actions.ReportResult | None = None
        today = date.today()

        self._build_kpi_cards()

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", padx=12, pady=(4, 6))

        ctk.CTkLabel(controls, text="Kỳ báo cáo").pack(side="left", padx=(0, 6))
        self.period_type = ctk.CTkSegmentedButton(
            controls, values=list(PERIOD_TYPES), command=self._on_period_type
        )
        self.period_type.set("Quý")
        self.period_type.pack(side="left", padx=(0, 8))

        self.period_value = ctk.CTkOptionMenu(controls, width=90, values=["Q1"])
        self.period_value.pack(side="left", padx=(0, 8))

        years = [str(year) for year in range(today.year - 5, today.year + 2)]
        self.year = ctk.CTkOptionMenu(controls, width=90, values=years)
        self.year.set(str(today.year))
        self.year.pack(side="left", padx=(0, 12))

        ctk.CTkButton(controls, text="Xem báo cáo", width=120, command=self.refresh).pack(
            side="left", padx=(0, 8)
        )
        self.export_button = ctk.CTkButton(
            controls, text="Xuất CSV", width=110, state="disabled", command=self.export
        )
        self.export_button.pack(side="left")

        self._on_period_type("Quý", initial_month=today.month)

        self.tabs = ctk.CTkTabview(self, command=self.run_report)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        self.tables: dict[str, ttk.Treeview] = {}
        for name in TABS:
            self.tables[name] = self._make_table(self.tabs.add(name))

        self.status = ctk.CTkLabel(self, text="", anchor="w", justify="left")
        self.status.pack(fill="x", padx=14, pady=(0, 10))

        self.after(50, self.refresh)

    # ----- KPI cards --------------------------------------------------------

    def _build_kpi_cards(self) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=6, pady=(10, 4))
        titles = (
            "Tổng đầu sách (ISBN)",
            "Cuốn sách (kho / đang mượn)",
            "Độc giả đang hoạt động",
            "Sách quá hạn hôm nay (phạt)",
        )
        self.kpi_values: list[ctk.CTkLabel] = []
        for column, title in enumerate(titles):
            row.grid_columnconfigure(column, weight=1)
            card = ctk.CTkFrame(
                row, corner_radius=10, border_width=2, border_color=KPI_COLOR,
                fg_color=("#F3F4F6", "#1F2937"),
            )
            card.grid(row=0, column=column, padx=6, pady=4, sticky="ew")
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12), text_color="#9CA3AF").pack(
                padx=12, pady=(10, 2), anchor="w"
            )
            value = ctk.CTkLabel(card, text="-", font=ctk.CTkFont(size=18, weight="bold"))
            value.pack(padx=12, pady=(0, 10), anchor="w")
            self.kpi_values.append(value)

    def _load_kpis(self) -> None:
        data = actions.overview()
        fine = f"{int(data['TienPhatUocTinh']):,} đ".replace(",", ".")
        texts = (
            str(data["TongDauSach"]),
            f"{data['TongCuonSach']} / {data['DangMuon']}",
            f"{data['DocGiaHoatDong']} thẻ",
            f"{data['SoQuaHan']} cuốn ({fine})",
        )
        for label, text in zip(self.kpi_values, texts):
            label.configure(text=text)

    # ----- period selection -------------------------------------------------

    def _on_period_type(self, value: str, initial_month: int | None = None) -> None:
        month = initial_month or date.today().month
        if value == "Tháng":
            self.period_value.configure(values=[str(m) for m in range(1, 13)], state="normal")
            self.period_value.set(str(month))
        elif value == "Quý":
            self.period_value.configure(values=[f"Q{q}" for q in range(1, 5)], state="normal")
            self.period_value.set(f"Q{(month - 1) // 3 + 1}")
        else:
            self.period_value.configure(values=["-"], state="disabled")
            self.period_value.set("-")

    def selected_period(self) -> actions.Period:
        year = int(self.year.get())
        kind = self.period_type.get()
        if kind == "Tháng":
            return actions.Period(year, month=int(self.period_value.get()))
        if kind == "Quý":
            return actions.Period(year, quarter=int(self.period_value.get().lstrip("Q")))
        return actions.Period(year)

    # ----- table ------------------------------------------------------------

    def _make_table(self, parent) -> ttk.Treeview:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        table = ttk.Treeview(frame, show="headings")
        vertical = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=table.xview)
        table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        table.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        return table

    def _fill_table(self, table: ttk.Treeview, result: actions.ReportResult) -> None:
        table.delete(*table.get_children())
        table.configure(columns=result.columns)
        wide_columns = ("Tên sách", "Độc giả", "Email", "Chỉ tiêu", "Thể loại")
        for column in result.columns:
            wide = column in wide_columns
            table.heading(column, text=column, anchor="w")
            table.column(column, width=220 if wide else 105, minwidth=60, stretch=wide, anchor="w")
        for row in result.rows:
            table.insert("", "end", values=[actions.format_value(value) for value in row])

    # ----- actions ----------------------------------------------------------

    def refresh(self) -> None:
        """Reload the KPI cards and the report on the open tab."""
        try:
            self._load_kpis()
        except (pyodbc.Error, RuntimeError, ValueError) as error:
            self._show_error(f"Không tải được số liệu tổng quan: {error}")
            return
        self.run_report()

    def run_report(self) -> None:
        tab = self.tabs.get()
        try:
            period = self.selected_period()
            if tab == TABS[0]:
                result = actions.overdue_readers(period.as_of())
            elif tab == TABS[1]:
                result = actions.usage_frequency(period)
            elif tab == TABS[2]:
                result = actions.stock_review(period)
            else:
                result = actions.period_summary(period)
        except ValueError as error:
            self._show_error(str(error))
            return
        except (pyodbc.Error, RuntimeError) as error:
            self._show_error(f"Không tải được báo cáo: {error}")
            return

        self._result = result
        self._fill_table(self.tables[tab], result)
        self.export_button.configure(state="normal")
        text = result.title + (f"  -  {result.summary}" if result.summary else "")
        if not result.rows:
            text += "  -  không có dữ liệu"
        self.status.configure(text=text, text_color=TEXT_COLOR)

    def export(self) -> None:
        if self._result is None:
            return
        default_name = self._result.title.replace("/", "-").replace(" ", "_") + ".csv"
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("Tệp CSV", "*.csv")],
        )
        if not path:
            return
        try:
            saved = actions.export_csv(self._result, path)
        except OSError as error:
            self._show_error(f"Không lưu được tệp: {error}")
            return
        self.status.configure(text=f"Đã lưu {saved}", text_color=TEXT_COLOR)

    def _show_error(self, message: str) -> None:
        self._result = None
        self.export_button.configure(state="disabled")
        self.status.configure(text=message, text_color=ERROR_COLOR)
