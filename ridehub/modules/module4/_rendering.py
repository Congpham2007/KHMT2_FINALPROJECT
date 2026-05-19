"""
Chart, table, and KPI rendering methods for RiskAnalysisFrame.
Mixed into RiskAnalysisFrame via inheritance.
"""
import math
import textwrap
from datetime import datetime

import customtkinter as ctk
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from ._helpers import font, safe_float, pct_delta, make_card, COLORS, FONT_FAMILY


class RiskRenderingMixin:
    """UI rendering methods — mixed into RiskAnalysisFrame."""

    def _render_dashboard(self, data):
        self.loading = False
        self.loading_bar.set(1)
        for frame in [self.kpi_frame, self.cancel_card, self.vtat_card,
                      self.vehicle_card, self.fraud_card, self.driver_card]:
            self._clear(frame)
        plt.close("all")
        self.chart_canvases = []
        self.raw_rows["fraud"] = data["fraud"]
        self.raw_rows["drivers"] = data["drivers"]["rows"]
        self.driver_threshold = data["drivers"]["threshold"]
        self.table_page = {"fraud": 0, "drivers": 0}

        self._render_kpis(data["kpi"])
        self._render_cancel_reasons(data["reasons"])
        self._render_vtat_analysis(data["vtat"])
        self._render_vehicle_cancel_chart(data["vehicles"])
        self._render_fraud_table()
        self._render_driver_table()
        self._set_status("Live SQL refreshed " + datetime.now().strftime("%H:%M:%S"))
        self._schedule_refresh()

    def _render_error(self, error):
        self.loading = False
        self.loading_bar.set(0)
        for frame in [self.kpi_frame, self.cancel_card, self.vtat_card,
                      self.vehicle_card, self.fraud_card, self.driver_card]:
            self._clear(frame)
        self._set_status("SQL refresh failed", error=True)
        ctk.CTkLabel(self.kpi_frame, text=error, font=font(13),
                     text_color=COLORS["red"]).pack(anchor="w", pady=12)

    def _build_skeletons(self):
        for i in range(4):
            sk = make_card(self.kpi_frame, height=112, border_color="#EFEFEF")
            sk.grid(row=0, column=i, sticky="ew",
                    padx=(0 if i == 0 else 7, 0 if i == 3 else 7))
            self.kpi_frame.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(sk, text="Loading SQL...", font=font(11),
                         text_color=COLORS["muted_light"]).place(x=18, y=42)

    def _render_kpis(self, kpis):
        current, previous = kpis
        total = int(current.get("total") or 0)
        cards = [
            ("Customer Cancelled Rides",
             current.get("customer_cancelled") or 0,
             previous.get("customer_cancelled") or 0,
             COLORS["yellow"], COLORS["yellow_bg"], "#D97706", COLORS["orange"],
             "ti-alert-triangle"),
            ("Driver Cancelled Rides",
             current.get("driver_cancelled") or 0,
             previous.get("driver_cancelled") or 0,
             "#FB923C", COLORS["orange_bg"], COLORS["orange"], COLORS["orange"],
             "ti-clock"),
            ("Incomplete / Unfinished Rides",
             current.get("incomplete") or 0,
             previous.get("incomplete") or 0,
             "#F87171", COLORS["red_bg"], COLORS["red"], COLORS["red"],
             "ti-shield-off"),
            ("Ride Completion Rate",
             (safe_float(current.get("completed")) / total * 100 if total else 0),
             (safe_float(previous.get("completed")) / safe_float(
                 previous.get("total")) * 100 if previous.get("total") else 0),
             "#34D399", COLORS["green_bg"], COLORS["green"], COLORS["green"],
             "ti-circle-check"),
        ]
        for i, card_data in enumerate(cards):
            raw_val = card_data[1]
            title = card_data[0]
            if "Completion Rate" in title:
                pct_val = min(100.0, max(0.0, safe_float(raw_val)))
            else:
                pct_val = (safe_float(raw_val) / total * 100) if total > 0 else 0.0
            self._kpi_card(i, card_data, total, pct_val)

    def _kpi_card(self, col, data, total, progress=0):
        title, value, old_value, border, icon_bg, icon_color, value_color, _ = data
        delta = pct_delta(value, old_value)
        warning = ((title != "Ride Completion Rate" and delta > 15)
                   or (title == "Ride Completion Rate" and delta < -3))

        if "Completion" in title:
            status_color = COLORS["green"] if delta >= 0 else COLORS["red"]
            bg_color = COLORS["green_bg"] if delta >= 0 else COLORS["red_bg"]
        else:
            status_color = COLORS["red"] if delta > 0 else COLORS["green"]
            bg_color = COLORS["red_bg"] if delta > 0 else COLORS["green_bg"]

        card = make_card(self.kpi_frame, height=185, border_width=2, border_color=border)
        card.grid(row=0, column=col, sticky="ew", padx=7)
        card.grid_propagate(False)
        self.kpi_frame.grid_columnconfigure(col, weight=1)

        ctk.CTkLabel(card, text=title[:1], width=36, height=36, corner_radius=18,
                     fg_color=icon_bg, text_color=icon_color,
                     font=font(18, "bold")).place(x=18, y=16)
        if "Completion Rate" not in title:
            ctk.CTkLabel(card, text=f"{delta:+.1f}%", font=font(11, "bold"),
                         fg_color=bg_color,
                         text_color=status_color, corner_radius=20, padx=9, pady=3).place(
                relx=0.95, y=17, anchor="ne")
        display = f"{value:.1f}%" if "Rate" in title else f"{int(value):,}"
        ctk.CTkLabel(card, text=display, font=font(25, "bold"),
                     text_color=value_color, wraplength=180).place(x=18, y=56)
        ctk.CTkLabel(card, text=title.upper(), font=font(10, "bold"),
                     text_color=COLORS["muted_light"], wraplength=190,
                     justify="left").place(x=18, y=88)
        ctk.CTkLabel(card, text=f"vs previous month | total {total:,}",
                     font=font(11), text_color="#CCCCCC", wraplength=190,
                     justify="left").place(x=18, y=120)

        if "Completion Rate" not in title:
            ctk.CTkLabel(card, text=f"{progress:.1f}% of total rides", font=font(9),
                         text_color=COLORS["muted"]).place(x=22, y=145)
        bar_y = 165

        pb_bg = ctk.CTkFrame(card, fg_color="#E2E8F0", height=6, corner_radius=3)
        pb_bg.place(x=22, y=bar_y, relwidth=0.74)
        pb_fill = ctk.CTkFrame(pb_bg, fg_color=value_color or border, height=6,
                               corner_radius=3)
        pb_fill.place(x=0, y=0, relheight=1.0, relwidth=0)
        self._animate_relwidth(pb_fill, min(1.0, progress / 100.0))

    def _animate_relwidth(self, widget, target, steps=15, delay=12):
        def _tick(i=[0]):
            if i[0] >= steps:
                widget.place_configure(relwidth=target)
                return
            widget.place_configure(relwidth=target * (i[0] + 1) / steps)
            i[0] += 1
            widget.after(delay, _tick)

        _tick()

    def _render_cancel_reasons(self, rows):
        self._section_header(self.cancel_card, "Cancellation Reason Distribution",
                             "Grouped customer vs driver cancellation reasons; "
                             "click a bar to drill down")
        if not rows:
            self._empty(self.cancel_card,
                        "No cancellation reason rows returned for this filter.")
            return
        reasons = [r["reason"] for r in rows]
        cust = np.array([int(r["customer_cnt"] or 0) for r in rows])
        driv = np.array([int(r["driver_cnt"] or 0) for r in rows])
        totals = cust + driv
        y = np.arange(len(reasons))

        import textwrap
        fig, ax = self._figure(8.5, max(4.6, len(reasons) * 0.42))
        ax.barh(y - 0.18, cust, height=0.34, color=COLORS["red"], alpha=0.88,
                label="Customers", picker=True)
        ax.barh(y + 0.18, driv, height=0.34, color=COLORS["orange"], alpha=0.88,
                label="Drivers", picker=True)
        ax.set_yticks(y)
        _wrap = lambda s: "\n".join(textwrap.wrap(str(s), width=26)[:2])
        ax.set_yticklabels([_wrap(r) for r in reasons], fontsize=8.5)
        ax.spines["left"].set_visible(True)
        ax.spines["left"].set_color(COLORS["border"])
        ax.spines["bottom"].set_visible(True)
        ax.spines["bottom"].set_color(COLORS["border"])
        ax.spines["right"].set_visible(False)
        ax.spines["top"].set_visible(False)
        ax.tick_params(axis="y", length=4, color=COLORS["border"], pad=8)
        ax.tick_params(axis="x", length=4, color=COLORS["border"])
        ax.invert_yaxis()
        ax.set_xlabel("Cancellation count", fontsize=8, color=COLORS["muted"])
        ax.legend(frameon=False, fontsize=8, loc="lower right")

        max_val = max(cust.max(), driv.max()) if len(cust) > 0 else 1
        ax.set_xlim(0, max_val * 1.4)

        for i, total in enumerate(totals):
            if total:
                pct = total / totals.sum() * 100
                longest_bar = max(cust[i], driv[i])
                ax.text(longest_bar + max_val * 0.05, i,
                        f"{int(total)} ({pct:.1f}%)",
                        va="center", ha="left", fontsize=7.5, color=COLORS["text"])

        annot = ax.annotate("", xy=(0, 0), xytext=(12, 12),
                            textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="white",
                                      ec=COLORS["border"]), fontsize=8)
        annot.set_visible(False)

        def on_motion(event):
            if event.inaxes != ax or event.ydata is None:
                annot.set_visible(False)
                fig.canvas.draw_idle()
                return
            idx = int(round(event.ydata))
            if 0 <= idx < len(reasons):
                annot.xy = (event.xdata or 0, event.ydata)
                annot.set_text(
                    f"{reasons[idx]}\nCustomer: {cust[idx]:,}\n"
                    f"Driver: {driv[idx]:,}")
                annot.set_visible(True)
                fig.canvas.draw_idle()

        def on_click(event):
            if event.inaxes != ax or event.ydata is None:
                return
            idx = int(round(event.ydata))
            if 0 <= idx < len(reasons):
                self.selected_reason = reasons[idx]
                self.apply_filters()

        fig.canvas.mpl_connect("motion_notify_event", on_motion)
        fig.canvas.mpl_connect("button_press_event", on_click)
        fig.subplots_adjust(left=0.22, right=0.99, top=0.95, bottom=0.12)
        self._embed(self.cancel_card, fig, toolbar=True)

    def _render_vtat_analysis(self, rows):
        self._section_header(self.vtat_card, "VTAT Cancellation Pressure",
                             "Bucket chart: ride volume bars with customer "
                             "cancellation-rate line")
        if not rows:
            self._empty(self.vtat_card,
                        "No VTAT rows returned for this filter.")
            return

        labels = [str(row["vtat_bucket"]) for row in rows]
        totals = np.array([int(row["total"] or 0) for row in rows])
        cancelled = np.array([int(row["cancelled"] or 0) for row in rows])
        rates = np.array([safe_float(row["cancel_rate"]) for row in rows])
        avg_vtat = np.array([safe_float(row["avg_vtat"]) for row in rows])

        fig, ax = self._figure(6.2, 4.6)
        x = np.arange(len(labels))
        bar_colors = [
            COLORS["green"] if rate < 8
            else COLORS["yellow"] if rate < 15
            else COLORS["orange"] if rate < 22
            else COLORS["red"]
            for rate in rates
        ]
        bars = ax.bar(x, totals, color=bar_colors, alpha=0.82, width=0.58,
                      edgecolor="white", linewidth=1.0, label="Ride volume")
        ax.set_ylabel("Ride volume", fontsize=8, color=COLORS["muted"])
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)

        ax2 = ax.twinx()
        ax2.plot(x, rates, color=COLORS["primary_dark"], linewidth=2.4,
                 marker="o", markersize=6, label="Customer cancellation rate")
        ax2.fill_between(x, rates, alpha=0.10, color=COLORS["primary_dark"])
        ax2.set_ylabel("Customer cancellation rate (%)", fontsize=8,
                       color=COLORS["muted"])
        ax2.tick_params(colors=COLORS["muted"], labelsize=8)
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_color(COLORS["border"])
        ax.set_ylim(0, 45000)

        for i, (bar, rate) in enumerate(zip(bars, rates)):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(totals) * 0.02,
                    f"{totals[i]:,}", ha="center", fontsize=7.5,
                    color=COLORS["text"])
            ax2.text(i, rate + max(rates.max(), 1) * 0.05, f"{rate:.1f}%",
                     ha="center", fontsize=7.5, color=COLORS["primary_dark"],
                     fontweight="bold")

        handles1, labels1 = ax.get_legend_handles_labels()
        handles2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(handles1 + handles2, labels1 + labels2, fontsize=8,
                  frameon=False, loc="upper left")

        annot = ax.annotate("", xy=(0, 0), xytext=(12, 12),
                            textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="white",
                                      ec=COLORS["border"]), fontsize=8)
        annot.set_visible(False)

        def on_motion(event):
            if event.inaxes not in (ax, ax2) or event.xdata is None:
                annot.set_visible(False)
                fig.canvas.draw_idle()
                return
            idx = int(round(event.xdata))
            if 0 <= idx < len(labels):
                annot.xy = (idx, totals[idx])
                annot.set_text(
                    f"{labels[idx]}\n"
                    f"Rides: {totals[idx]:,}\n"
                    f"Customer cancelled: {cancelled[idx]:,}\n"
                    f"Cancel rate: {rates[idx]:.2f}%\n"
                    f"Avg VTAT: {avg_vtat[idx]:.1f} min"
                )
                annot.set_visible(True)
                fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", on_motion)
        fig.tight_layout(pad=1.15)
        self._embed(self.vtat_card, fig, toolbar=True)

    def _render_vehicle_cancel_chart(self, rows):
        self._section_header(
            self.vehicle_card,
            "Vehicle Types With Highest Cancellation Rate",
            "Ranked by cancellation rate; each vehicle type uses its own color"
        )
        if not rows:
            self._empty(self.vehicle_card,
                        "No vehicle cancellation data returned for this filter.")
            return

        labels = [str(row["vehicle_type"])[:18] for row in rows]
        rates = np.array([safe_float(row.get("cancel_rate")) for row in rows])
        totals = np.array([int(row.get("total_rides") or 0) for row in rows])
        cancelled = np.array([int(row.get("cancelled_rides") or 0) for row in rows])
        y = np.arange(len(labels))
        vehicle_colors = {
            "Auto": "#E63946", "Go Mini": "#F2A65A", "Go Sedan": "#F4D35E",
            "Bike": "#00AFB9", "Premier Sedan": "#0081A7", "eBike": "#9B5DE5",
            "Uber XL": "#F15BB5",
        }
        colors = [vehicle_colors.get(l, "#3B82F6") for l in labels]

        fig, ax = self._figure(9.5, max(3.8, len(labels) * 0.35))

        ax.set_axisbelow(True)
        # ax.grid(axis='x', color="#94A3B8", linestyle='-', alpha=0.9, linewidth=1.5)

        bars = ax.barh(y, rates, color=colors, alpha=0.92, height=0.58,
                       edgecolor="white", linewidth=1)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=9)
        ax.invert_yaxis()
        ax.set_xlabel("Cancellation rate (%)", fontsize=9, color=COLORS["muted"])
        for i, bar in enumerate(bars):
            ax.text(
                bar.get_width() + max(rates.max(), 1) * 0.012,
                bar.get_y() + bar.get_height() / 2,
                f"{rates[i]:.1f}%  |  {cancelled[i]:,}/{totals[i]:,}",
                va="center", fontsize=8, color=COLORS["text"],
                fontweight="bold" if i < 3 else "normal",
            )

        annot = ax.annotate("", xy=(0, 0), xytext=(12, 12),
                            textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="white",
                                      ec=COLORS["border"]), fontsize=8)
        annot.set_visible(False)

        def on_motion(event):
            if event.inaxes != ax or event.ydata is None:
                annot.set_visible(False)
                fig.canvas.draw_idle()
                return
            idx = int(round(event.ydata))
            if 0 <= idx < len(rows):
                annot.xy = (event.xdata or rates[idx], idx)
                annot.set_text(
                    f"{rows[idx]['vehicle_type']}\n"
                    f"Cancel rate: {rates[idx]:.2f}%\n"
                    f"Cancelled: {cancelled[idx]:,}\n"
                    f"Total rides: {totals[idx]:,}"
                )
                annot.set_visible(True)
                fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", on_motion)
        fig.tight_layout(pad=1.1)
        self._embed(self.vehicle_card, fig, toolbar=False)

    # ── Fraud / Driver table rendering ───────────────────────────────

    def _render_fraud_table(self):
        rows = self._filtered_rows("fraud", self.top_fraud_var.get())
        self._watchlist_header(
            self.fraud_card, "$", "Cash Fraud Watchlist",
            "Payment = Cash · Status: Cancelled / Incomplete · Distance > 1 km",
            self.top_fraud_var, self.risk_fraud_var, "fraud",
            lambda: self._export_rows("fraud"),
        )
        self._custom_table(
            self.fraud_card, kind="fraud",
            headers=("BOOKING\nID", "DRIVER", "DATE", "DISTANCE", "STATUS", "RISK"),
            rows=rows,
            widths=(1.2, 1.0, 1.2, 1.0, 1.25, 0.9),
        )
        self._pager(self.fraud_card, "fraud")

    def _render_driver_table(self):
        rows = self._filtered_rows("drivers", self.top_driver_var.get())
        self._watchlist_header(
            self.driver_card, "!", "Driver Cancel Watchlist",
            f"Accepted rides >= {self.driver_threshold} · Sorted by cancellation "
            f"rate · Repeated abnormal behavior",
            self.top_driver_var, self.risk_driver_var, "drivers", None,
            self.cancel_driver_type_var,
        )
        self._custom_table(
            self.driver_card, kind="drivers",
            headers=("RANK", "DRIVER", "ACCEPTED", "CANCELLED",
                     "CANCEL RATE", "RISK"),
            rows=rows,
            widths=(0.7, 1.2, 1.0, 1.0, 1.15, 0.9),
        )
        self._pager(self.driver_card, "drivers")

    def _watchlist_header(self, parent, icon, title, subtitle, top_var, risk_var,
                          kind, export_cmd=None, cancel_type_var=None):
        rows_all = self.raw_rows[kind]
        risk_func = self._fraud_risk if kind == "fraud" else self._driver_risk
        high_count = sum(1 for row in rows_all if risk_func(row)[0] == "high")
        med_count = sum(1 for row in rows_all if risk_func(row)[0] == "medium")
        low_count = sum(1 for row in rows_all if risk_func(row)[0] == "low")

        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 8))

        icon_box = ctk.CTkLabel(
            header, text=icon, width=32, height=32, corner_radius=10,
            fg_color=COLORS["red_bg"] if kind == "fraud" else COLORS["orange_bg"],
            text_color=COLORS["red"] if kind == "fraud" else COLORS["orange"],
            font=font(17, "bold"),
        )
        icon_box.pack(side="left", padx=(0, 10))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(title_box, text=title, font=font(14, "bold"),
                     text_color=COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(title_box, text=subtitle, font=font(10),
                     text_color="#8A94A6", wraplength=560,
                     justify="left").pack(anchor="w", pady=(2, 0))

        controls = ctk.CTkFrame(header, fg_color="transparent")
        controls.pack(side="right")

        top_frame = ctk.CTkFrame(controls, fg_color="transparent")
        top_frame.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(top_frame, text="Top", font=font(12, "bold"),
                     text_color=COLORS["muted"]).pack(side="left", padx=(0, 4))

        entry = ctk.CTkEntry(
            top_frame, textvariable=top_var, placeholder_text="", width=48,
            height=28, fg_color="#F9FAFB", border_color=COLORS["border"],
            corner_radius=8, justify="center",
        )
        entry.pack(side="left")
        entry.bind("<KeyRelease>", lambda *_: self._search_filter_changed(kind))

        risk_box = ctk.CTkComboBox(
            controls, variable=risk_var,
            values=["All Risk", "High Risk", "Medium Risk", "Low Risk"],
            width=108, height=28, fg_color="#FFFFFF",
            border_color="#FCA5A5" if high_count else COLORS["border"],
            button_color=COLORS["red_bg"] if high_count else COLORS["primary_light"],
            button_hover_color="#FECACA" if high_count else "#E0E7FF",
            text_color=COLORS["text"], state="readonly",
            command=lambda *_: self._risk_filter_changed(kind),
        )
        risk_box.pack(side="left", padx=(0, 8))

        if cancel_type_var is not None:
            cancel_box = ctk.CTkComboBox(
                controls, variable=cancel_type_var,
                values=["All cancellations", "Cancelled by Driver",
                        "Cancelled by Customer"],
                width=140, height=28, fg_color="#FFFFFF",
                border_color=COLORS["border"],
                button_color=COLORS["orange_bg"],
                button_hover_color="#FED7AA",
                text_color=COLORS["text"], state="readonly",
                command=lambda *_: self._cancel_type_filter_changed(kind),
            )
            cancel_box.pack(side="left", padx=(0, 8))

        if export_cmd:
            ctk.CTkButton(
                controls, text="Export", width=74, height=28,
                fg_color=COLORS["primary"], hover_color=COLORS["primary_dark"],
                command=export_cmd,
            ).pack(side="left", padx=(0, 8))

        counts_frame = ctk.CTkFrame(controls, fg_color="transparent")
        counts_frame.pack(side="left")

        ctk.CTkLabel(
            counts_frame, text=f"{high_count} High", font=font(10, "bold"),
            fg_color="#FFF1F2", text_color="#DC2626", corner_radius=18,
            padx=8, pady=4
        ).pack(side="left", padx=(0, 4))

        ctk.CTkLabel(
            counts_frame, text=f"{med_count} Med", font=font(10, "bold"),
            fg_color="#FFF7ED", text_color="#D97706", corner_radius=18,
            padx=8, pady=4
        ).pack(side="left", padx=(0, 4))

        ctk.CTkLabel(
            counts_frame, text=f"{low_count} Low", font=font(10, "bold"),
            fg_color="#ECFDF5", text_color="#059669", corner_radius=18,
            padx=8, pady=4
        ).pack(side="left")

    def _custom_table(self, parent, kind, headers, rows, widths):
        start = self.table_page[kind] * self.page_size
        page_rows = rows[start:start + self.page_size]
        table = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=0)
        table.pack(fill="x", padx=0, pady=(0, 6))

        head = ctk.CTkFrame(table, fg_color="#F8FAFC", corner_radius=0, height=36)
        head.pack(fill="x")
        head.pack_propagate(False)
        for index, width in enumerate(widths):
            head.grid_columnconfigure(index, weight=int(width * 100))
            ctk.CTkLabel(
                head, text=headers[index], font=font(9, "bold"),
                text_color="#475569", justify="left", anchor="w",
            ).grid(row=0, column=index, sticky="nsew", padx=10, pady=5)

        if not page_rows:
            ctk.CTkLabel(
                table, text="No rows match the current search/risk filter.",
                font=font(11), text_color=COLORS["muted"],
            ).pack(pady=24)
            return

        for row_offset, row in enumerate(page_rows, start=1):
            if kind == "fraud":
                display = self._fraud_display(row)
                risk_tag, risk_label = self._fraud_risk(row)
                row_bg = ("#FFF7F7" if risk_tag == "high"
                          else "#FFFCF5" if risk_tag == "medium"
                          else "#F8FFFB")
                values = [
                    (display["booking"], "text", "bold"),
                    (display["driver"], "text", "normal"),
                    (display["date"], "text", "normal"),
                    (display["distance"], "distance", risk_tag),
                    (display["status"], "status", None),
                    (risk_label.title(), "risk", risk_tag),
                ]
            else:
                display = self._driver_display(row, start + row_offset)
                risk_tag, risk_label = self._driver_risk(row)
                row_bg = ("#FFF7F7" if risk_tag == "high"
                          else "#FFFCF5" if risk_tag == "medium"
                          else "#F8FFFB")
                values = [
                    (display["rank"], "text", "bold"),
                    (display["driver"], "text", "bold"),
                    (display["accepted"], "text", "normal"),
                    (display["cancelled"], "distance", risk_tag),
                    (display["rate"], "distance", risk_tag),
                    (risk_label.title(), "risk", risk_tag),
                ]

            row_frame = ctk.CTkFrame(table, fg_color=row_bg, corner_radius=0, height=44)
            row_frame.pack(fill="x")
            row_frame.pack_propagate(False)
            for index, width in enumerate(widths):
                row_frame.grid_columnconfigure(index, weight=int(width * 100))
                value, cell_type, weight = values[index]
                cell = ctk.CTkFrame(row_frame, fg_color="transparent")
                cell.grid(row=0, column=index, sticky="nsew", padx=6, pady=4)
                self._render_custom_cell(cell, value, cell_type, weight)
                for widget in [cell] + cell.winfo_children():
                    widget.bind("<Button-1>",
                                lambda _event, r=row, k=kind:
                                self._show_custom_detail(r, k))

            ctk.CTkFrame(table, fg_color="#F1F5F9", height=1).pack(fill="x")

    def _render_custom_cell(self, parent, value, cell_type, risk_tag):
        if cell_type == "status":
            bg, fg, border = self._status_colors(value)
            ctk.CTkLabel(parent, text=value, font=font(9, "bold"), fg_color=bg,
                         text_color=fg, corner_radius=14, padx=8, pady=2).pack(
                anchor="w", pady=5)
        elif cell_type == "risk":
            bg, fg, border = self._risk_colors(risk_tag)
            ctk.CTkLabel(parent, text=value, font=font(9, "bold"), fg_color=bg,
                         text_color=fg, corner_radius=14, padx=8, pady=2).pack(
                anchor="w", pady=5)
        elif cell_type == "distance":
            _, fg, _ = self._risk_colors(risk_tag)
            ctk.CTkLabel(parent, text=value, font=font(10, "bold"),
                         text_color=fg, wraplength=105, justify="left").pack(
                anchor="w", pady=5)
        else:
            ctk.CTkLabel(parent, text=value,
                         font=font(10, "bold" if risk_tag == "bold" else "normal"),
                         text_color="#0F172A", wraplength=135, justify="left").pack(
                anchor="w", pady=4)

    def _fraud_display(self, row):
        return {
            "booking": str(row.get("Booking ID") or "N/A"),
            "driver": str(row.get("Driver ID") or "N/A"),
            "date": self._format_date(row.get("event_time")),
            "distance": f"{safe_float(row.get('Ride Distance')):.1f} km",
            "status": self._short_status(row.get("Booking Status")),
        }

    def _driver_display(self, row, rank):
        cancel_type = self.cancel_driver_type_var.get()
        if cancel_type == "Cancelled by Customer":
            cancelled = int(row.get("customer_cancelled") or 0)
            rate = safe_float(row.get("customer_cancel_rate"))
        elif cancel_type == "Cancelled by Driver":
            cancelled = int(row.get("driver_cancelled") or 0)
            rate = safe_float(row.get("cancel_rate"))
        else:
            cancelled = (int(row.get("driver_cancelled") or 0)
                         + int(row.get("customer_cancelled") or 0))
            rate = safe_float(row.get("total_cancel_rate"))
        return {
            "rank": f"#{rank}",
            "driver": str(row.get("Driver ID") or "N/A"),
            "accepted": f"{int(row.get('accepted_rides') or 0):,}",
            "cancelled": f"{cancelled:,}",
            "rate": f"{rate:.1f}%",
        }

    def _format_date(self, value):
        text = str(value or "")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(text[:19], fmt).strftime("%b %d, %Y")
            except ValueError:
                continue
        return text[:12] or "N/A"

    def _short_status(self, status):
        status = str(status or "N/A")
        if "Incomplete" in status:
            return "Incomplete"
        if "Cancel" in status:
            return "Cancelled"
        return status

    def _status_colors(self, status):
        if "Incomplete" in str(status):
            return "#FFF7ED", "#D97706", "#FCD34D"
        if "Cancel" in str(status):
            return "#FFF1F2", "#DC2626", "#FCA5A5"
        return "#ECFDF5", "#059669", "#6EE7B7"

    def _risk_colors(self, risk_tag):
        if risk_tag == "high":
            return "#FFF1F2", "#DC2626", "#FCA5A5"
        if risk_tag == "medium":
            return "#FFF7ED", "#D97706", "#FCD34D"
        return "#ECFDF5", "#059669", "#6EE7B7"

    def _show_custom_detail(self, row, kind):
        win = ctk.CTkToplevel(self)
        win.title("Fraud Ride Detail" if kind == "fraud" else "Driver Cancel Detail")
        win.geometry("680x600")
        box = make_card(win)
        box.pack(fill="both", expand=True, padx=18, pady=18)
        title = "Fraud Ride Detail" if kind == "fraud" else "Driver Cancel Detail"
        ctk.CTkLabel(box, text=title, font=font(18, "bold"),
                     text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(18, 10))
        for key, value in row.items():
            line = ctk.CTkFrame(box, fg_color="#F9FAFB", corner_radius=8)
            line.pack(fill="x", padx=18, pady=4)
            ctk.CTkLabel(line, text=str(key), width=160, font=font(11, "bold"),
                         text_color=COLORS["muted"], anchor="w").pack(
                side="left", padx=10, pady=8)
            ctk.CTkLabel(line, text=str(value), font=font(12),
                         text_color="#093C5D", wraplength=280,
                         justify="left").pack(side="left", fill="x", expand=True,
                                              padx=10, pady=8)

    def _pager(self, parent, kind):
        rows = self._filtered_rows(
            kind, self.top_fraud_var.get()
            if kind == "fraud" else self.top_driver_var.get())
        total_pages = max(1, math.ceil(len(rows) / self.page_size))
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkLabel(bar, text=f"Showing page {self.table_page[kind] + 1} "
                               f"of {total_pages} | {len(rows):,} rows",
                     font=font(11), text_color=COLORS["muted"]).pack(side="left")
        ctk.CTkButton(bar, text="Prev", width=62, height=28,
                      fg_color="#F3F4F6", text_color=COLORS["text"],
                      hover_color="#E5E7EB",
                      command=lambda: self._page(kind, -1)).pack(
            side="right", padx=(6, 0))
        ctk.CTkButton(bar, text="Next", width=62, height=28,
                      fg_color="#F3F4F6", text_color=COLORS["text"],
                      hover_color="#E5E7EB",
                      command=lambda: self._page(kind, 1)).pack(side="right")

    def _section_header(self, parent, title, subtitle):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 2))
        ctk.CTkLabel(header, text=title, font=font(14, "bold"),
                     text_color=COLORS["text"], wraplength=520,
                     justify="left").pack(anchor="w")
        ctk.CTkLabel(header, text=subtitle, font=font(11),
                     text_color=COLORS["muted_light"], wraplength=620,
                     justify="left").pack(anchor="w")

    def _figure(self, width, height):
        plt.rcParams["font.family"] = FONT_FAMILY
        fig, ax = plt.subplots(figsize=(width, height), dpi=96)
        fig.patch.set_facecolor(COLORS["surface"])
        ax.set_facecolor("#FFFFFF")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(COLORS["border"])
        ax.tick_params(colors=COLORS["muted"], labelsize=8)
        return fig, ax

    def _embed(self, parent, fig, toolbar=False):
        holder = ctk.CTkFrame(parent, fg_color="transparent")
        holder.pack(fill="both", expand=True, padx=10, pady=(2, 12))
        canvas = FigureCanvasTkAgg(fig, master=holder)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.pack(fill="both", expand=True)
        if toolbar:
            toolbar_frame = ctk.CTkFrame(holder, fg_color="transparent", height=28)
            toolbar_frame.pack(fill="x")
            tlbr = NavigationToolbar2Tk(canvas, toolbar_frame, pack_toolbar=False)
            tlbr.update()
            tlbr.pack(side="left")
        self.chart_canvases.append(canvas)

    def _empty(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=font(12),
                     text_color=COLORS["muted"]).pack(pady=28)

    def _clear(self, parent):
        for widget in parent.winfo_children():
            widget.destroy()
