import math
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ui.main_ui import ModernTable, DateRangePicker
from ui.theme import UI_FONT, STATUS_COLORS, DEFAULT_COLOR
from ._data import load_dashboard_data


class DashboardFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._canvas_refs = []
        self._build_header()
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, pady=(15, 0))
        self.generate_report()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(header, text="Executive Operations Dashboard",
                     font=(UI_FONT, 26, "bold"), text_color="#111827").pack(side="left")

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right")

        today = datetime.now()
        default_start = datetime(2024, 3, 1).date()
        default_end = datetime(2024, 4, 1).date()
        self._date_picker = DateRangePicker(
            right,
            default_start=default_start,
            default_end=default_end,
        )
        self._date_picker.pack(side="left", padx=(0, 12), pady=2)

        # ── Generate button ───────────────────────────────────────
        ctk.CTkButton(right, text="🔄 Generate Report",
                      font=(UI_FONT, 13, "bold"),
                      fg_color="#4F46E5", hover_color="#4338CA",
                      text_color="#FFFFFF", corner_radius=8, width=165, height=40,
                      command=self.generate_report).pack(side="left")

    def generate_report(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        plt.close("all")
        self._canvas_refs.clear()
        start, end = self._date_picker.get_range_iso()
        try:
            data = load_dashboard_data(start, end)
        except Exception as e:
            messagebox.showerror("Data Load Error", str(e))
            return
        self._build_kpi_section(self.scroll, data)
        self._build_charts_row1(self.scroll, data)
        self._build_charts_row2(self.scroll, data)
        self._build_top_vehicles(self.scroll, data)
        self._build_daily_table(self.scroll, data)

    @staticmethod
    def _pct(current, previous):
        return (current - previous) / previous * 100 if previous and previous > 0 else 0.0

    def _build_kpi_section(self, parent, data):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 15))
        pct_rides = self._pct(data["total"], data["prev_total"])
        pct_rev = self._pct(data["revenue"], data["prev_revenue"])
        cards = [
            ("🚗 Total Rides", f"{data['total']:,}",
             f"{pct_rides:+.1f}% vs last month", "#3B82F6"),
            ("💰 Total Revenue", f"${data['revenue']:,.0f}",
             f"{pct_rev:+.1f}% vs last month", "#10B981"),
            ("✅ Completion Rate", f"{data['completion_rate']:.1f}%",
             "of all rides", "#8B5CF6"),
            ("⭐ Avg Driver Rating", f"{data['avg_rate']:.2f}",
             "out of 5.0", "#F59E0B"),
            ("📈 Avg Rev / Ride", f"${data['avg_rev_per_ride']:.0f}",
             "per completed ride", "#14B8A6"),
            ("⏱ Avg Pickup Time", f"{data['avg_vtat']:.1f} min",
             "driver arrival time", "#EF4444"),
        ]
        for i, (title, value, sub, color) in enumerate(cards):
            card = ctk.CTkFrame(frame, fg_color="#FFFFFF", corner_radius=12, height=125,
                                border_width=1, border_color="#E5E7EB")
            card.grid(row=0, column=i, padx=(0, 15), sticky="ew")
            card.grid_propagate(False)
            frame.grid_columnconfigure(i, weight=1)
            ctk.CTkFrame(card, fg_color=color, height=6, corner_radius=3).place(
                x=0, y=0, relwidth=1)
            ctk.CTkLabel(card, text=title, font=(UI_FONT, 12, "bold"),
                         text_color="#6B7280").place(x=15, y=20)
            ctk.CTkLabel(card, text=value, font=(UI_FONT, 24, "bold"),
                         text_color="#111827").place(x=15, y=48)
            tc = "#10B981" if "+" in sub else ("#EF4444" if "-" in sub else "#9CA3AF")
            ctk.CTkLabel(card, text=f"{'▲' if '+' in sub else '▼' if '-' in sub else ''} {sub}".strip(),
                         font=(UI_FONT, 11, "bold"), text_color=tc).place(x=15, y=93)

    def _build_charts_row1(self, parent, data):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, 15))
        row.grid_columnconfigure(0, weight=3)
        row.grid_columnconfigure(1, weight=2)

        # ── Trend chart ──
        trend_card = ctk.CTkFrame(row, fg_color="#FFFFFF", corner_radius=12,
                                  border_width=1, border_color="#E5E7EB")
        trend_card.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        ctk.CTkLabel(trend_card, text="📈 Revenue Trend vs Forecast",
                     font=(UI_FONT, 14, "bold"), text_color="#111827").pack(
            anchor="w", padx=20, pady=(15, 0))
        daily = data.get("daily_data", [])
        if daily:
            dates = [str(r["Date"]) for r in daily]
            actuals = [float(r["revenue"] or 0) for r in daily]
            avg_rev = sum(actuals) / len(actuals) if actuals else 0
            forecasts = [avg_rev * (1 + 0.015 * (i - len(actuals) / 2))
                         for i in range(len(actuals))]
            total_actual, total_forecast = sum(actuals), sum(forecasts)
            delta_pct = self._pct(total_actual, total_forecast)
            badge_color = "#10B981" if delta_pct >= 0 else "#EF4444"
            info = ctk.CTkFrame(trend_card, fg_color="#F3F4F6", corner_radius=8)
            info.pack(fill="x", padx=20, pady=(10, 0))
            ctk.CTkLabel(info, text=(
                f"  Actual: ${total_actual:,.0f}   │   "
                f"Forecast: ${total_forecast:,.0f}   │   "
                f"{'▲' if delta_pct >= 0 else '▼'} {abs(delta_pct):.1f}% vs forecast"
            ), font=(UI_FONT, 11, "bold"), text_color=badge_color).pack(pady=8)
            fig, ax = plt.subplots(figsize=(7, 3), dpi=92)
            fig.patch.set_facecolor("white")
            xs = list(range(len(dates)))
            ax.fill_between(xs, actuals, alpha=0.12, color="#3B82F6")
            line_actual, = ax.plot(xs, actuals, marker="o", color="#3B82F6",
                                   lw=2, markersize=5, label="Actual")
            line_forecast, = ax.plot(xs, forecasts, linestyle="--", color="#EF4444",
                                     lw=2, label="Forecast")
            step = max(1, len(dates) // 8)
            ax.set_xticks(range(0, len(dates), step))
            ax.set_xticklabels([dates[i][-5:] for i in range(0, len(dates), step)],
                               rotation=40, fontsize=8)
            ax.yaxis.set_major_formatter(
                plt.FuncFormatter(lambda x, _: f"${x / 1000:.0f}k"))
            ax.set_ylabel("Revenue", fontsize=9)
            ax.legend(fontsize=9, loc="upper left")
            ax.spines[["top", "right"]].set_visible(False)
            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, trend_card)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(5, 15))
            self._canvas_refs.append(canvas)
            annot = ax.annotate("", xy=(0, 0), xytext=(12, 12),
                                textcoords="offset points",
                                bbox=dict(boxstyle="round,pad=0.5", fc="#1F2937",
                                          ec="none", alpha=0.92),
                                arrowprops=dict(arrowstyle="->", color="#1F2937"),
                                fontsize=9, color="white")
            annot.set_visible(False)
            _last_xi = [None]

            def on_hover_trend(event):
                if event.inaxes != ax or event.xdata is None:
                    if annot.get_visible():
                        annot.set_visible(False)
                        canvas.draw_idle()
                    return
                xi = min(range(len(xs)), key=lambda i: abs(xs[i] - event.xdata))
                if xi == _last_xi[0]:
                    return
                _last_xi[0] = xi
                annot.xy = (xs[xi], actuals[xi])
                annot.set_text(
                    f"📅 {dates[xi]}\nActual:   ${actuals[xi]:,.0f}\n"
                    f"Forecast: ${forecasts[xi]:,.0f}")
                annot.set_visible(True)
                canvas.draw_idle()

            fig.canvas.mpl_connect("motion_notify_event", on_hover_trend)
        else:
            ctk.CTkLabel(trend_card, text="No data available",
                         text_color="#9CA3AF").pack(expand=True, pady=40)

        # ── Donut chart ──
        donut_card = ctk.CTkFrame(row, fg_color="#FFFFFF", corner_radius=12,
                                  border_width=1, border_color="#E5E7EB")
        donut_card.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(donut_card, text="🍩 Ride Status Distribution",
                     font=(UI_FONT, 14, "bold"), text_color="#111827").pack(
            anchor="w", padx=20, pady=(15, 0))
        status_dist = data.get("status_dist", {})
        if status_dist:
            total_rides = sum(status_dist.values())
            ctk.CTkLabel(donut_card,
                         text=f"Distribution across {total_rides:,} total rides",
                         font=(UI_FONT, 10), text_color="#9CA3AF").pack(
                anchor="w", padx=20, pady=(0, 4))
            labels = list(status_dist.keys())
            sizes = list(status_dist.values())
            colors = [STATUS_COLORS.get(l, DEFAULT_COLOR) for l in labels]
            fig2, ax2 = plt.subplots(figsize=(4.2, 4.0), dpi=92)
            fig2.patch.set_facecolor("white")
            wedges, _ = ax2.pie(sizes, colors=colors, startangle=90,
                                wedgeprops=dict(width=0.52, edgecolor="white",
                                                linewidth=2.5))
            for i, (wedge, sz) in enumerate(zip(wedges, sizes)):
                pct = sz / total_rides * 100
                if pct < 3:
                    continue
                mid_angle = math.radians((wedge.theta1 + wedge.theta2) / 2)
                r = 0.72
                ax2.text(r * math.cos(mid_angle), r * math.sin(mid_angle),
                         f"{pct:.1f}%", ha="center", va="center",
                         fontsize=8.5, fontweight="bold", color="white")
            ax2.text(0, 0.10, f"{total_rides:,}", ha="center", va="center",
                     fontsize=15, fontweight="bold", color="#111827")
            ax2.text(0, -0.18, "Total Rides", ha="center", va="center",
                     fontsize=8, color="#6B7280")
            patches = [mpatches.Patch(color=c, label=(
                f"{l}  {status_dist[l]:,}  "
                f"({status_dist[l] / total_rides * 100:.1f}%)"))
                for c, l in zip(colors, labels)]
            ax2.legend(handles=patches, loc="lower center", ncol=1, fontsize=7.2,
                       bbox_to_anchor=(0.5, -0.22), frameon=False,
                       handlelength=1.0, handleheight=1.0)
            fig2.tight_layout()
            canvas2 = FigureCanvasTkAgg(fig2, donut_card)
            canvas2.draw()
            canvas2.get_tk_widget().pack(fill="both", expand=True, padx=8,
                                         pady=(0, 15))
            self._canvas_refs.append(canvas2)
            annot2 = ax2.annotate("", xy=(0, 0), xytext=(10, 10),
                                  textcoords="offset points",
                                  bbox=dict(boxstyle="round,pad=0.5", fc="#1F2937",
                                            ec="none", alpha=0.92),
                                  fontsize=9, color="white")
            annot2.set_visible(False)
            _last_wi = [None]

            def on_hover_donut(event):
                if event.inaxes != ax2:
                    if _last_wi[0] is not None:
                        wedges[_last_wi[0]].set_radius(1.0)
                        _last_wi[0] = None
                    if annot2.get_visible():
                        annot2.set_visible(False)
                        canvas2.draw_idle()
                    return
                for i, wedge in enumerate(wedges):
                    if wedge.contains(event)[0]:
                        if _last_wi[0] != i:
                            if _last_wi[0] is not None:
                                wedges[_last_wi[0]].set_radius(1.0)
                            wedges[i].set_radius(1.07)
                            _last_wi[0] = i
                        annot2.xy = (event.xdata, event.ydata)
                        annot2.set_text(
                            f"{labels[i]}\n{sizes[i]:,} rides  "
                            f"({sizes[i] / total_rides * 100:.1f}%)")
                        annot2.set_visible(True)
                        canvas2.draw_idle()
                        return
                if _last_wi[0] is not None:
                    wedges[_last_wi[0]].set_radius(1.0)
                    _last_wi[0] = None
                if annot2.get_visible():
                    annot2.set_visible(False)
                    canvas2.draw_idle()

            fig2.canvas.mpl_connect("motion_notify_event", on_hover_donut)
        else:
            ctk.CTkLabel(donut_card, text="No data available",
                         text_color="#9CA3AF").pack(expand=True, pady=40)

    def _build_charts_row2(self, parent, data):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, 15))
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=2)

        # ── Payment methods pie ──
        pay_card = ctk.CTkFrame(row, fg_color="#FFFFFF", corner_radius=12,
                                border_width=1, border_color="#E5E7EB")
        pay_card.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        ctk.CTkLabel(pay_card, text="💳 Payment Methods",
                     font=(UI_FONT, 14, "bold"), text_color="#111827").pack(
            anchor="w", padx=20, pady=(15, 0))
        payment_dist = data.get("payment_dist", {})
        if payment_dist:
            labels = [k for k in payment_dist
                      if k and str(k) not in ("0", "None", "nan")]
            sizes = [payment_dist[k] for k in labels]
            total_pay = sum(sizes)
            payment_colors = {
                "Not Applicable": "#4DC4B6", "UPI": "#357EBD", "Cash": "#F27A5F",
                "Uber Wallet": "#F4B142", "Credit Card": "#9F81B0",
                "Debit Card": "#1F6F5F",
            }
            colors = [payment_colors.get(l, "#CBD5E1") for l in labels]
            fig3, ax3 = plt.subplots(figsize=(4, 3.8), dpi=92)
            fig3.patch.set_facecolor("white")
            wedges3, _ = ax3.pie(sizes, colors=colors, startangle=90,
                                 wedgeprops={"edgecolor": "#FFFFFF", "linewidth": 0})
            for i, (wedge, sz) in enumerate(zip(wedges3, sizes)):
                pct = sz / total_pay * 100
                if pct < 5:
                    continue
                mid_angle = math.radians((wedge.theta1 + wedge.theta2) / 2)
                r = 0.62
                ax3.text(r * math.cos(mid_angle), r * math.sin(mid_angle),
                         f"{pct:.0f}%", ha="center", va="center",
                         fontsize=9, fontweight="bold", color="white")
            ax3.legend([f"{l} ({s / total_pay * 100:.0f}%)"
                        for l, s in zip(labels, sizes)],
                       loc="lower center", ncol=2, fontsize=8,
                       bbox_to_anchor=(0.5, -0.12), frameon=False)
            fig3.tight_layout()
            canvas3 = FigureCanvasTkAgg(fig3, pay_card)
            canvas3.draw()
            canvas3.get_tk_widget().pack(fill="both", expand=True, padx=8,
                                         pady=(4, 15))
            self._canvas_refs.append(canvas3)
            annot3 = ax3.annotate("", xy=(0, 0), xytext=(8, 8),
                                  textcoords="offset points",
                                  bbox=dict(boxstyle="round,pad=0.5", fc="#1F2937",
                                            ec="none", alpha=0.92),
                                  fontsize=9, color="white")
            annot3.set_visible(False)
            _last_p = [None]

            def on_hover_pay(event):
                if event.inaxes != ax3:
                    if annot3.get_visible():
                        annot3.set_visible(False)
                        canvas3.draw_idle()
                    return
                for i, w in enumerate(wedges3):
                    if w.contains(event)[0]:
                        if _last_p[0] == i:
                            return
                        _last_p[0] = i
                        annot3.xy = (event.xdata, event.ydata)
                        annot3.set_text(
                            f"{labels[i]}\n{sizes[i]:,}  "
                            f"({sizes[i] / total_pay * 100:.1f}%)")
                        annot3.set_visible(True)
                        canvas3.draw_idle()
                        return
                if annot3.get_visible():
                    annot3.set_visible(False)
                    _last_p[0] = None
                    canvas3.draw_idle()

            fig3.canvas.mpl_connect("motion_notify_event", on_hover_pay)
        else:
            ctk.CTkLabel(pay_card, text="No data available",
                         text_color="#9CA3AF").pack(expand=True, pady=40)

        # ── Vehicle revenue bar chart ──
        veh_card = ctk.CTkFrame(row, fg_color="#FFFFFF", corner_radius=12,
                                border_width=1, border_color="#E5E7EB")
        veh_card.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(veh_card, text="🚙 Revenue by Vehicle Type",
                     font=(UI_FONT, 14, "bold"), text_color="#111827").pack(
            anchor="w", padx=20, pady=(15, 0))
        vehicle_rev = data.get("vehicle_rev", [])
        if vehicle_rev:
            v_types = [str(r["Vehicle Type"]) for r in vehicle_rev]
            v_revs = [float(r["rev"] or 0) for r in vehicle_rev]
            vehicle_colors = {
                "Auto": "#E63946", "Go Mini": "#F2A65A", "Go Sedan": "#F4D35E",
                "Bike": "#00AFB9", "Premier Sedan": "#0081A7", "eBike": "#9B5DE5",
                "Uber XL": "#F15BB5",
            }
            bar_colors = [vehicle_colors.get(v, "#3B82F6") for v in v_types]
            fig4, ax4 = plt.subplots(figsize=(6, 3.5), dpi=92)
            fig4.patch.set_facecolor("white")
            bars = ax4.bar(v_types, v_revs, color=bar_colors, width=0.6,
                           edgecolor="white", linewidth=1.5)
            ax4.spines[["top", "right"]].set_visible(False)
            ax4.set_ylabel("Revenue ($)", fontsize=9)
            ax4.yaxis.set_major_formatter(
                plt.FuncFormatter(lambda x, _: f"${x / 1000:.0f}k"))
            ax4.tick_params(axis="x", labelsize=9)
            max_rev = max(v_revs) if v_revs else 1
            for bar, val in zip(bars, v_revs):
                ax4.text(bar.get_x() + bar.get_width() / 2,
                         bar.get_height() + max_rev * 0.015,
                         f"${val / 1000:.0f}k", ha="center",
                         fontsize=8.5, fontweight="bold", color="#111827")
            fig4.tight_layout()
            canvas4 = FigureCanvasTkAgg(fig4, veh_card)
            canvas4.draw()
            canvas4.get_tk_widget().pack(fill="both", expand=True, padx=8,
                                         pady=(4, 15))
            self._canvas_refs.append(canvas4)
            annot4 = ax4.annotate("", xy=(0, 0), xytext=(0, 10),
                                  textcoords="offset points",
                                  bbox=dict(boxstyle="round,pad=0.5", fc="#1F2937",
                                            ec="none", alpha=0.92),
                                  fontsize=9, color="white", ha="center")
            annot4.set_visible(False)
            _last_b = [None]

            def on_hover_bar(event):
                if event.inaxes != ax4:
                    if _last_b[0] is not None:
                        bars[_last_b[0]].set_alpha(1.0)
                        _last_b[0] = None
                    if annot4.get_visible():
                        annot4.set_visible(False)
                        canvas4.draw_idle()
                    return
                for i, bar in enumerate(bars):
                    if bar.contains(event)[0]:
                        if _last_b[0] != i:
                            if _last_b[0] is not None:
                                bars[_last_b[0]].set_alpha(1.0)
                            bars[i].set_alpha(0.72)
                            _last_b[0] = i
                        annot4.xy = (bar.get_x() + bar.get_width() / 2,
                                     bar.get_height())
                        annot4.set_text(
                            f"{v_types[i]}\nRevenue: ${v_revs[i]:,.0f}")
                        annot4.set_visible(True)
                        canvas4.draw_idle()
                        return
                if _last_b[0] is not None:
                    bars[_last_b[0]].set_alpha(1.0)
                    _last_b[0] = None
                if annot4.get_visible():
                    annot4.set_visible(False)
                    canvas4.draw_idle()

            fig4.canvas.mpl_connect("motion_notify_event", on_hover_bar)
        else:
            ctk.CTkLabel(veh_card, text="No data available",
                         text_color="#9CA3AF").pack(expand=True, pady=40)

    def _build_top_vehicles(self, parent, data):
        card = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=12,
                            border_width=1, border_color="#E5E7EB")
        card.pack(fill="x", pady=(0, 15))

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(15, 4))
        ctk.CTkLabel(hdr, text="🏆 Top Performing Vehicles",
                     font=(UI_FONT, 14, "bold"), text_color="#111827").pack(side="left")
        ctk.CTkLabel(hdr, text="Ranked by total revenue",
                     font=(UI_FONT, 10), text_color="#9CA3AF").pack(side="left", padx=10)

        top_vehicles = data.get("top_vehicles", [])
        if not top_vehicles:
            ctk.CTkLabel(card, text="No data available",
                         text_color="#9CA3AF").pack(pady=12)
            return

        max_avg = max((float(r.get("avg_rev_per_ride") or 0)
                       for r in top_vehicles), default=1) or 1
        medals = ["🥇", "🥈", "🥉"]
        sorted_veh = sorted(top_vehicles,
                            key=lambda r: float(r.get("total_revenue") or 0),
                            reverse=True)

        col_defs = [
            ("RANK",          60,  "center"),
            ("VEHICLE TYPE",  140, "w"),
            ("TOTAL RIDES",   110, "e"),
            ("TOTAL REVENUE", 130, "e"),
            ("REV / RIDE",    110, "e"),
            ("AVG RATING",    110, "e"),
            ("COMPLETION",    110, "e"),
            ("EFFICIENCY",    110, "e"),
        ]

        data_rows = []
        for i, r in enumerate(sorted_veh):
            cr = float(r.get("completion_rate") or 0)
            rat = float(r.get("avg_rating") or 0)
            arpu = float(r.get("avg_rev_per_ride") or 0)
            eff = (cr / 100) * 0.4 + (rat / 5) * 0.3 + (arpu / max_avg) * 0.3
            cr_color = "#10B981" if cr >= 90 else ("#F59E0B" if cr >= 75 else "#EF4444")
            eff_color = "#3B82F6"
            rank_str = medals[i] if i < 3 else f"# {i + 1}"

            data_rows.append([
                (rank_str,                               "#111827", "bold"),
                (r.get("Vehicle Type", "N/A"),           "#111827", "normal"),
                (f"{int(r.get('total_rides') or 0):,}",  "#374151", "normal"),
                (f"${float(r.get('total_revenue') or 0):,.0f}", "#111827", "bold"),
                (f"${arpu:.0f}",                         "#374151", "normal"),
                (f"⭐ {rat:.2f}",                         "#F59E0B", "bold"),
                (f"{cr:.1f}%",                           cr_color,  "bold"),
                (f"{eff:.3f}",                           eff_color, "bold"),
            ])

        tbl = ModernTable(card, col_defs, data_rows, totals_row=None, max_scroll_rows=10)
        tbl.pack(fill="x", padx=20, pady=(0, 20))

    def _build_daily_table(self, parent, data):
        card = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=12,
                            border_width=1, border_color="#E5E7EB")
        card.pack(fill="x", pady=(0, 25))

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(15, 4))
        ctk.CTkLabel(hdr, text="📅 Performance Summary",
                     font=(UI_FONT, 14, "bold"), text_color="#111827").pack(side="left")

        daily_data = data.get("daily_data", [])
        if not daily_data:
            ctk.CTkLabel(card, text="No data available",
                         text_color="#9CA3AF").pack(pady=12)
            return

        today_str = datetime.now().strftime("%Y-%m-%d")
        col_defs = [
            ("DATE",             140, "w"),
            ("TOTAL RIDES",      120, "e"),
            ("REVENUE",          140, "e"),
            ("COMPLETION RATE",  140, "e"),
            ("AVG RATING",       120, "e"),
            ("CANCELLATIONS",    120, "e"),
            ("Δ REVENUE",        140, "e"),
        ]

        t_rides = t_rev = t_can = t_comp = t_rat_sum = rat_count = 0
        prev_rev = None
        data_rows = []

        for r in daily_data:
            date_str = str(r["Date"])
            rev = float(r["revenue"] or 0)
            total = int(r["total_rides"] or 0)
            comp = int(r["completed"] or 0)
            cr = (comp / total * 100) if total > 0 else 0
            rat = float(r["avg_rating"] or 0)
            can = int(r["cancellations"] or 0)

            if prev_rev is not None and prev_rev > 0:
                diff = rev - prev_rev
                delta_str = f"{'↗' if diff >= 0 else '↘'}  {'+' if diff >= 0 else ''}${abs(diff):,.0f}"
                delta_color = "#10B981" if diff >= 0 else "#EF4444"
            else:
                delta_str, delta_color = "—", "#9CA3AF"
            prev_rev = rev

            cr_color = "#10B981" if cr >= 95 else ("#F59E0B" if cr >= 90 else "#EF4444")
            can_color = "#EF4444" if can >= 15 else "#374151"
            is_today = date_str == today_str
            date_disp = (f"● {date_str}" if is_today else f"    {date_str}")
            date_color = "#10B981" if is_today else "#111827"
            can_disp = f"⚠ {can}" if can >= 15 else str(can)

            data_rows.append([
                (date_disp,        date_color,  "bold" if is_today else "normal"),
                (f"{total:,}",     "#374151",   "normal"),
                (f"${rev:,.0f}",   "#111827",   "bold"),
                (f"{cr:.1f}%",     cr_color,    "bold"),
                (f"★ {rat:.1f}",   "#F59E0B",   "bold"),
                (can_disp,         can_color,   "bold" if can >= 15 else "normal"),
                (delta_str,        delta_color, "bold"),
            ])

            t_rides += total
            t_rev += rev
            t_can += can
            t_comp += comp
            if rat > 0:
                t_rat_sum += rat
                rat_count += 1

        avg_cr3 = (t_comp / t_rides * 100) if t_rides > 0 else 0
        avg_rat3 = (t_rat_sum / rat_count) if rat_count > 0 else 0
        cr3_color = "#10B981" if avg_cr3 >= 95 else ("#F59E0B" if avg_cr3 >= 90 else "#EF4444")

        totals = [
            ("TOTALS / AVG",     "#111827", "bold"),
            (f"{t_rides:,}",     "#111827", "bold"),
            (f"${t_rev:,.0f}",   "#111827", "bold"),
            (f"{avg_cr3:.1f}%",  cr3_color, "bold"),
            (f"★ {avg_rat3:.2f}","#F59E0B", "bold"),
            (f"{t_can:,}",       "#374151", "bold"),
            ("—",                "#9CA3AF", "normal"),
        ]

        tbl = ModernTable(card, col_defs, data_rows, totals_row=totals, max_scroll_rows=10)
        tbl.pack(fill="x", padx=20, pady=(0, 8))