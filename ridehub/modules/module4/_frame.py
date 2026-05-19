"""
RiskAnalysisFrame: shell, filters, state management, and risk scoring.
Inherits query methods and rendering methods from mixin classes.
"""
import math
import threading
from datetime import datetime, timedelta
from tkinter import messagebox

import customtkinter as ctk
import matplotlib.pyplot as plt

from data.uber import get_db_connection
from ui.main_ui import DateRangePicker
from ._helpers import font, safe_float, make_card, COLORS, FONT_FAMILY
from ._queries import RiskQueriesMixin
from ._rendering import RiskRenderingMixin


class RiskAnalysisFrame(RiskQueriesMixin, RiskRenderingMixin, ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=COLORS["page"])
        self.refresh_ms = 90000
        self.refresh_job = None
        self.chart_canvases = []
        self.raw_rows = {"fraud": [], "drivers": []}
        self.driver_threshold = 30
        self.table_page = {"fraud": 0, "drivers": 0}
        self.page_size = 8
        self.selected_reason = None
        self.loading = False

        self._init_vars()
        self._build_shell()
        self._load_filter_options()
        self.apply_filters()

    def destroy(self):
        if self.refresh_job:
            self.after_cancel(self.refresh_job)
        plt.close("all")
        super().destroy()

    def _init_vars(self):
        self.default_start = "2024-03-01"
        self.default_end = "2024-04-01"
        self.date_picker = None
        self.region_var = ctk.StringVar(value="All")
        self.service_var = ctk.StringVar(value="All")
        self.payment_var = ctk.StringVar(value="All")
        self.status_var = ctk.StringVar(value="All")
        self.peak_var = ctk.BooleanVar(value=False)
        self.top_fraud_var = ctk.StringVar(value="")
        self.top_driver_var = ctk.StringVar(value="")
        self.risk_fraud_var = ctk.StringVar(value="All Risk")
        self.risk_driver_var = ctk.StringVar(value="All Risk")
        self.cancel_driver_type_var = ctk.StringVar(value="All cancellations")

    def _build_shell(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="Operational Analytics & Fraud Detection",
                     font=font(20, "bold"), text_color=COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(left,
                     text="Live SQL-backed ride cancellation, VTAT, cash fraud, "
                          "and driver risk monitoring",
                     font=font(11), text_color=COLORS["muted_light"]).pack(
            anchor="w", pady=(2, 0))

        self.status_label = ctk.CTkLabel(
            header, text="Ready", font=font(11), text_color=COLORS["muted"],
            fg_color=COLORS["surface"], corner_radius=20, padx=12, pady=4)
        self.status_label.pack(side="right", padx=(12, 0))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=24, pady=(0, 18))

        self.filter_card = make_card(self.scroll)
        self.filter_card.pack(fill="x", pady=(0, 14))
        self._build_filters(self.filter_card)

        self.kpi_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.kpi_frame.pack(fill="x", pady=(0, 14))

        self.middle = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.middle.pack(fill="x", pady=(0, 14))
        self.middle.grid_columnconfigure((0, 1), weight=1, uniform="middle")

        self.cancel_card = make_card(self.middle)
        self.cancel_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.vtat_card = make_card(self.middle)
        self.vtat_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.vehicle_card = make_card(self.scroll)
        self.vehicle_card.pack(fill="x", pady=(0, 14))

        self.fraud_card = make_card(self.scroll)
        self.fraud_card.pack(fill="x", pady=(0, 14))

        self.driver_card = make_card(self.scroll)
        self.driver_card.pack(fill="x", pady=(0, 18))

    def _build_filters(self, parent):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(14, 10))
        ctk.CTkLabel(top, text="Global Filters", font=font(14, "bold"),
                     text_color=COLORS["text"]).pack(side="left")
        self.loading_bar = ctk.CTkProgressBar(
            top, width=140, height=8, progress_color=COLORS["primary"],
            fg_color=COLORS["primary_light"])
        self.loading_bar.set(0)
        self.loading_bar.pack(side="right", padx=(10, 0))

        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 14))
        for i in range(8):
            grid.grid_columnconfigure(i, weight=1)

        ctk.CTkLabel(grid, text="DATE FROM", font=font(10, "bold"),
                     text_color=COLORS["muted_light"]).grid(
            row=0, column=0, sticky="w", padx=6, pady=(0, 4))
        ctk.CTkLabel(grid, text="DATE TO", font=font(10, "bold"),
                     text_color=COLORS["muted_light"]).grid(
            row=0, column=1, sticky="w", padx=6, pady=(0, 4))
        self.date_picker = DateRangePicker(
            grid,
            default_start=datetime.strptime(self.default_start, "%Y-%m-%d").date(),
            default_end=datetime.strptime(self.default_end, "%Y-%m-%d").date(),
            on_change=lambda s, e: self.apply_filters()
        )
        self.date_picker.grid(row=1, column=0, columnspan=2, sticky="ew", padx=6)
        self.region_box = self._field(grid, "Region / City", self.region_var, 2,
                                      "combo", ["All"])
        self.service_box = self._field(grid, "Service Type", self.service_var, 3,
                                       "combo", ["All"])
        self.payment_box = self._field(grid, "Payment", self.payment_var, 4,
                                       "combo", ["All"])
        self.status_box = self._field(grid, "Booking Status", self.status_var, 5,
                                      "combo", ["All"])

        peak = ctk.CTkCheckBox(grid, text="Peak hour", variable=self.peak_var,
                               font=font(12, "bold"), text_color=COLORS["text"],
                               fg_color=COLORS["primary"],
                               hover_color=COLORS["primary_dark"])
        peak.grid(row=1, column=6, sticky="w", padx=6, pady=(2, 0))

        actions = ctk.CTkFrame(grid, fg_color="transparent")
        actions.grid(row=1, column=7, sticky="e", padx=(8, 0))
        ctk.CTkButton(actions, text="Apply", width=86, height=34,
                      fg_color=COLORS["primary"],
                      hover_color=COLORS["primary_dark"],
                      command=self.apply_filters).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="Reset", width=82, height=34,
                      fg_color="#F3F4F6", hover_color="#E5E7EB",
                      text_color=COLORS["text"],
                      command=self.reset_filters).pack(side="left")

    def _field(self, parent, label, var, col, kind, values=None):
        ctk.CTkLabel(parent, text=label.upper(), font=font(10, "bold"),
                     text_color=COLORS["muted_light"], wraplength=130).grid(
            row=0, column=col, sticky="w", padx=6, pady=(0, 4))
        if kind == "entry":
            widget = ctk.CTkEntry(parent, textvariable=var, height=38,
                                  fg_color="#F9FAFB", border_color=COLORS["border"],
                                  corner_radius=8)
        else:
            widget = ctk.CTkComboBox(
                parent, variable=var, values=values or ["All"], height=38,
                fg_color="#F9FAFB", border_color=COLORS["border"],
                button_color="#F3F4F6", button_hover_color="#E5E7EB",
                text_color=COLORS["text"], state="readonly")
        widget.grid(row=1, column=col, sticky="ew", padx=6)
        return widget

    def _load_filter_options(self):
        conn = get_db_connection()
        if not conn:
            self._set_status("Database unavailable", error=True)
            return
        try:
            cur = conn.cursor()
            # Disabled DB date overriding to keep the 2024-03-01 to 2024-04-01 default
            pass
            cur.execute("""
                SELECT city FROM (
                    SELECT DISTINCT `Pickup Location` city FROM rides
                    WHERE `Pickup Location` IS NOT NULL AND `Pickup Location`<>''
                    UNION
                    SELECT DISTINCT `Drop Location` city FROM rides
                    WHERE `Drop Location` IS NOT NULL AND `Drop Location`<>''
                ) cities ORDER BY city
            """)
            self.region_box.configure(
                values=["All"] + [str(row[0]) for row in cur.fetchall()])
            for box, col in [
                (self.service_box, "Vehicle Type"),
                (self.payment_box, "Payment Method"),
                (self.status_box, "Booking Status"),
            ]:
                cur.execute(
                    f"SELECT DISTINCT `{col}` FROM rides "
                    f"WHERE `{col}` IS NOT NULL AND `{col}`<>'' ORDER BY `{col}`")
                box.configure(values=["All"] + [str(row[0]) for row in cur.fetchall()])
        except Exception as exc:
            self._set_status(f"Filter load failed: {exc}", error=True)
        finally:
            conn.close()

    def reset_filters(self):
        if self.date_picker:
            sd = datetime.strptime(self.default_start, "%Y-%m-%d").date()
            ed = datetime.strptime(self.default_end, "%Y-%m-%d").date()
            self.date_picker.set_range(sd, ed)
        self.region_var.set("All")
        self.service_var.set("All")
        self.payment_var.set("All")
        self.status_var.set("All")
        self.peak_var.set(False)
        self.risk_fraud_var.set("All Risk")
        self.risk_driver_var.set("All Risk")
        self.cancel_driver_type_var.set("All cancellations")
        self.selected_reason = None
        self.apply_filters()

    def apply_filters(self):
        if self.loading:
            return
        self.loading = True
        snapshot = self._filter_snapshot()
        self._set_status("Refreshing SQL data...")
        self.loading_bar.set(0.25)
        for frame in [self.kpi_frame, self.cancel_card, self.vtat_card,
                      self.vehicle_card, self.fraud_card, self.driver_card]:
            self._clear(frame)
        self._build_skeletons()
        thread = threading.Thread(
            target=lambda: self._load_dashboard_data(snapshot), daemon=True)
        thread.start()

    # ── Refresh & status ─────────────────────────────────────────

    def _schedule_refresh(self):
        if self.refresh_job:
            self.after_cancel(self.refresh_job)
        self.refresh_job = self.after(self.refresh_ms, self.apply_filters)

    def _set_status(self, text, error=False):
        self.status_label.configure(
            text=text, text_color=COLORS["red"] if error else COLORS["muted"])

    # ── Risk scoring ─────────────────────────────────────────────

    def _fraud_risk(self, row):
        score = int(safe_float(row.get("risk_score")))
        if score >= 80:
            return "high", "HIGH"
        if score >= 62:
            return "medium", "MEDIUM"
        return "low", "LOW"

    def _driver_risk(self, row):
        cancel_type = getattr(self, "cancel_driver_type_var", None)
        cancel_type = cancel_type.get() if cancel_type else "All cancellations"
        if cancel_type == "Cancelled by Customer":
            rate = safe_float(row.get("customer_cancel_rate"))
        elif cancel_type == "Cancelled by Driver":
            rate = safe_float(row.get("cancel_rate"))
        else:
            rate = safe_float(row.get("total_cancel_rate"))
        rating = safe_float(row.get("avg_rating"))
        if rate >= 40 or (rating and rating < 3.8):
            return "high", "HIGH"
        if rate >= 20 or (rating and rating < 4.2):
            return "medium", "MEDIUM"
        return "low", "LOW"

    # ── Table filter / page state ────────────────────────────────

    def _page(self, kind, delta):
        rows = self._filtered_rows(
            kind, self.top_fraud_var.get()
            if kind == "fraud" else self.top_driver_var.get())
        total_pages = max(1, math.ceil(len(rows) / self.page_size))
        self.table_page[kind] = min(max(0, self.table_page[kind] + delta),
                                    total_pages - 1)
        self._rerender_table(kind)

    def _risk_filter_changed(self, kind):
        self.table_page[kind] = 0
        self._rerender_table(kind)

    def _cancel_type_filter_changed(self, kind):
        self.table_page[kind] = 0
        self._rerender_table(kind)

    def _search_filter_changed(self, kind):
        self.table_page[kind] = 0
        self._rerender_table(kind)

    def _rerender_table(self, kind):
        if kind == "fraud":
            self._clear(self.fraud_card)
            self._render_fraud_table()
        else:
            self._clear(self.driver_card)
            self._render_driver_table()

    def _filtered_rows(self, kind, text):
        text = text.lower().strip()
        rows = self.raw_rows[kind]
        risk_value = (self.risk_fraud_var.get()
                      if kind == "fraud" else self.risk_driver_var.get())
        if risk_value != "All Risk":
            wanted = risk_value.split()[0].lower()
            risk_func = self._fraud_risk if kind == "fraud" else self._driver_risk
            rows = [row for row in rows if risk_func(row)[0] == wanted]
        if kind == "drivers":
            cancel_type = self.cancel_driver_type_var.get()
            if cancel_type == "Cancelled by Driver":
                rows = [row for row in rows
                        if int(row.get("driver_cancelled") or 0) > 0]
            elif cancel_type == "Cancelled by Customer":
                rows = [row for row in rows
                        if int(row.get("customer_cancelled") or 0) > 0]
        if text and text.isdigit():
            top_n = int(text)
            if top_n > 0:
                return rows[:top_n]
        return rows

    # ── Export ───────────────────────────────────────────────────

    def _export_rows(self, kind):
        rows = self._filtered_rows(
            kind, self.top_fraud_var.get()
            if kind == "fraud" else self.top_driver_var.get())
        if not rows:
            messagebox.showinfo("Export", "No rows to export.")
            return
        path = f"{kind}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        headers = list(rows[0].keys())
        with open(path, "w", encoding="utf-8") as f:
            f.write(",".join(headers) + "\n")
            for row in rows:
                f.write(",".join(
                    '"' + str(row.get(h, "")).replace('"', '""') + '"'
                    for h in headers) + "\n")
        messagebox.showinfo("Export", f"Exported {len(rows):,} rows to {path}")
