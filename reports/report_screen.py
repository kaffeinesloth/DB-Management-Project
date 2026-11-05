"""Reports & Statistics screen: overdue readers, book usage, stock review, period summary."""

from datetime import date
from tkinter import filedialog, ttk

import customtkinter as ctk
import pyodbc

from reports import report_actions as actions


TABS = ("Overdue readers", "Book usage", "Stock review", "Period summary")
PERIOD_TYPES = ("Month", "Quarter", "Year")


class ReportScreen(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master)
        self._result: actions.ReportResult | None = None
        today = date.today()

        ctk.CTkLabel(self, text="Reports & Statistics", font=("Arial", 22, "bold")).pack(
            anchor="w", padx=16, pady=(14, 6)
        )

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(controls, text="Period").pack(side="left", padx=(0, 6))
        self.period_type = ctk.CTkSegmentedButton(
            controls, values=list(PERIOD_TYPES), command=self._on_period_type
        )
        self.period_type.set("Quarter")
        self.period_type.pack(side="left", padx=(0, 8))

        self.period_value = ctk.CTkOptionMenu(controls, width=90, values=["Q1"])
        self.period_value.pack(side="left", padx=(0, 8))

        years = [str(year) for year in range(today.year - 5, today.year + 2)]
        self.year = ctk.CTkOptionMenu(controls, width=90, values=years)
        self.year.set(str(today.year))
        self.year.pack(side="left", padx=(0, 12))

        ctk.CTkButton(controls, text="Run report", width=110, command=self.run_report).pack(
            side="left", padx=(0, 8)
        )
        self.export_button = ctk.CTkButton(
            controls, text="Export CSV", width=110, state="disabled", command=self.export
        )
        self.export_button.pack(side="left")

        self._on_period_type("Quarter", initial_month=today.month)

        self.tabs = ctk.CTkTabview(self, command=self.run_report)
        self.tabs.pack(fill="both", expand=True, padx=16, pady=(0, 6))
        self.tables: dict[str, ttk.Treeview] = {}
        for name in TABS:
            self.tables[name] = self._make_table(self.tabs.add(name))

        self.status = ctk.CTkLabel(self, text="", anchor="w", justify="left")
        self.status.pack(fill="x", padx=18, pady=(0, 12))

        self.after(50, self.run_report)

    # ----- period selection -------------------------------------------------

    def _on_period_type(self, value: str, initial_month: int | None = None) -> None:
        month = initial_month or date.today().month
        if value == "Month":
            self.period_value.configure(values=[str(m) for m in range(1, 13)], state="normal")
            self.period_value.set(str(month))
        elif value == "Quarter":
            self.period_value.configure(values=[f"Q{q}" for q in range(1, 5)], state="normal")
            self.period_value.set(f"Q{(month - 1) // 3 + 1}")
        else:
            self.period_value.configure(values=["-"], state="disabled")
            self.period_value.set("-")

    def selected_period(self) -> actions.Period:
        year = int(self.year.get())
        kind = self.period_type.get()
        if kind == "Month":
            return actions.Period(year, month=int(self.period_value.get()))
        if kind == "Quarter":
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
        for column in result.columns:
            wide = column in ("Title", "Reader", "Email", "Metric", "Category")
            table.heading(column, text=column, anchor="w")
            table.column(column, width=220 if wide else 105, minwidth=60, stretch=wide, anchor="w")
        for row in result.rows:
            table.insert("", "end", values=[actions.format_value(value) for value in row])

    # ----- actions ----------------------------------------------------------

    def run_report(self) -> None:
        tab = self.tabs.get()
        try:
            period = self.selected_period()
            if tab == "Overdue readers":
                result = actions.overdue_readers(period.as_of())
            elif tab == "Book usage":
                result = actions.usage_frequency(period)
            elif tab == "Stock review":
                result = actions.stock_review(period)
            else:
                result = actions.period_summary(period)
        except ValueError as error:
            self._show_error(str(error))
            return
        except (pyodbc.Error, RuntimeError) as error:
            self._show_error(f"Could not load the report: {error}")
            return

        self._result = result
        self._fill_table(self.tables[tab], result)
        self.export_button.configure(state="normal")
        text = result.title + (f"  -  {result.summary}" if result.summary else "")
        if not result.rows:
            text += "  -  no rows"
        self.status.configure(text=text, text_color=("gray10", "gray90"))

    def export(self) -> None:
        if self._result is None:
            return
        default_name = self._result.title.replace("/", "-").replace(" ", "_") + ".csv"
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV file", "*.csv")],
        )
        if not path:
            return
        try:
            saved = actions.export_csv(self._result, path)
        except OSError as error:
            self._show_error(f"Could not save the file: {error}")
            return
        self.status.configure(text=f"Saved {saved}", text_color=("gray10", "gray90"))

    def _show_error(self, message: str) -> None:
        self._result = None
        self.export_button.configure(state="disabled")
        self.status.configure(text=message, text_color=("#b3261e", "#f2b8b5"))
