import datetime
from tkinter import ttk, messagebox

import customtkinter as ctk

from data.uber import get_db_connection
from ui.main_ui import DateRangePicker
from ._story import _StoryMixin
from ._analytics import _AnalyticsMixin


class RideManagementFrame(_StoryMixin, _AnalyticsMixin, ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="#f8fafc")

        self.total_db_rows = 0
        self.stats = {"cho_lau": 0, "vip": 0, "su_co": 0, "vtat_cao": 0}

        self.fetch_database_stats()

        self.setup_header()
        self.setup_f1_ui()
        self._init_dates()
        self.setup_action_buttons()
        self.setup_f1_table()

        self.f1_load_data()

        self.update_button_states()

    def fetch_database_stats(self):
        conn = get_db_connection()
        if not conn:
            return
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT COUNT(*) as total FROM rides")
            self.total_db_rows = cursor.fetchone()['total']

            cursor.execute(
                "SELECT COUNT(*) as c FROM rides "
                "WHERE `Avg VTAT` > 12 AND `Booking Status` LIKE '%Cancel%'"
            )
            self.stats["cho_lau"] = cursor.fetchone()['c']

            cursor.execute("SELECT COUNT(*) as c FROM rides WHERE `Booking Value` > 600")
            self.stats["vip"] = cursor.fetchone()['c']

            cursor.execute(
                "SELECT COUNT(*) as c FROM rides "
                "WHERE `Booking Status` LIKE '%Incomplete%'"
            )
            self.stats["su_co"] = cursor.fetchone()['c']

            cursor.execute("SELECT COUNT(*) as c FROM rides WHERE `Avg VTAT` > 15")
            self.stats["vtat_cao"] = cursor.fetchone()['c']
        except Exception as e:
            print("Stats error:", e)
        finally:
            conn.close()

    def _init_dates(self):
        """Load date range from DB for the picker defaults (like module 4)."""
        conn = get_db_connection()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("SELECT MIN(`Date`), MAX(`Date`) FROM rides")
            min_date, max_date = cur.fetchone()
            if min_date and max_date:
                min_dt = datetime.datetime.strptime(str(min_date), "%Y-%m-%d")
                max_dt = datetime.datetime.strptime(str(max_date), "%Y-%m-%d")
                if hasattr(self, "date_picker") and self.date_picker:
                    self.date_picker.set_range(min_dt.date(), max_dt.date())
        except Exception:
            pass
        finally:
            conn.close()

    # ==========================================
    # HEADER
    # ==========================================
    def setup_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 15))

        title_f = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_f.pack(side="left")
        ctk.CTkLabel(
            title_f, text="Ride Management Hub",
            font=ctk.CTkFont(family="Arial", size=24, weight="bold"),
            text_color="#0f172a"
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_f,
            text="Monitor, filter, and deep-dive every trip in the system",
            font=("Arial", 13), text_color="#94a3b8"
        ).pack(anchor="w")

        badge_frame = ctk.CTkFrame(
            header_frame, fg_color="white", corner_radius=20,
            border_width=1, border_color="#e2e8f0"
        )
        badge_frame.pack(side="right", padx=10, ipady=3, ipadx=5)

        self.badge_label = ctk.CTkLabel(
            badge_frame,
            text=f"{self.total_db_rows:,} rides shown  {self.total_db_rows:,} total",
            font=("Arial", 13, "bold"), text_color="#475569"
        )
        self.badge_label.pack(padx=12)

    # ==========================================
    # F1 - FILTER BAR
    # ==========================================
    def setup_f1_ui(self):
        filter_frame = ctk.CTkFrame(
            self, fg_color="white", corner_radius=12,
            border_width=1, border_color="#e2e8f0"
        )
        filter_frame.pack(fill="x", pady=(0, 15), ipady=8, ipadx=8)

        self.search_entry = ctk.CTkEntry(
            filter_frame, placeholder_text=" Booking ID...",
            border_color="#e2e8f0", fg_color="#f8fafc",
            corner_radius=8, text_color="black"
        )
        self.search_entry.pack(side="left", padx=(5, 10), fill="x", expand=True)
        self.search_entry.bind("<Return>", lambda e: self.f1_load_data())

        self.status_var = ctk.StringVar(value="All")
        ctk.CTkComboBox(
            filter_frame, variable=self.status_var,
            values=["All", "Completed", "Cancelled", "Incomplete"],
            width=120, border_color="#e2e8f0", button_color="#f1f5f9",
            fg_color="white", text_color="black", state="readonly"
        ).pack(side="left", padx=5)

        self.vehicle_var = ctk.StringVar(value="All")
        ctk.CTkComboBox(
            filter_frame, variable=self.vehicle_var,
            values=["All", "Auto", "Bike", "eBike", "Go Mini", "Go Sedan",
                    "Premier Sedan", "Uber XL"],
            width=130, border_color="#e2e8f0", button_color="#f1f5f9",
            fg_color="white", text_color="black", state="readonly"
        ).pack(side="left", padx=5)

        today = datetime.datetime.now()
        default_start = (today - datetime.timedelta(days=30)).date()
        default_end = today.date()
        self.date_picker = DateRangePicker(
            filter_frame,
            default_start=default_start,
            default_end=default_end,
        )
        self.date_picker.pack(side="left", padx=5)

        # Filter & Reset buttons
        ctk.CTkButton(
            filter_frame, text=" Filter", command=self.f1_load_data,
            width=90, fg_color="#2563eb", hover_color="#1d4ed8",
            corner_radius=8, font=("Arial", 13, "bold")
        ).pack(side="left", padx=(10, 5))
        ctk.CTkButton(
            filter_frame, text=" Reset", command=self.f1_reset_filters,
            width=90, fg_color="#f1f5f9", text_color="#475569",
            hover_color="#e2e8f0", corner_radius=8, font=("Arial", 13, "bold")
        ).pack(side="left", padx=(0, 5))

        self.bind("<Button-1>", lambda e: self.focus_set())
        filter_frame.bind("<Button-1>", lambda e: self.focus_set())

    # ==========================================
    # QUICK FILTERS + ACTION BUTTONS
    # ==========================================
    def setup_action_buttons(self):
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(
            action_frame, text="Quick filter:",
            text_color="#64748b", font=("Arial", 13, "bold")
        ).pack(side="left", padx=(0, 10))

        self.active_quick_filter = None
        self.qf_btns = {}

        # Long Wait
        btn_cholau = ctk.CTkButton(
            action_frame, text="Long Wait",
            command=lambda: self.toggle_quick_filter("Long Wait"),
            fg_color="#fef2f2", text_color="#ef4444",
            border_color="#fca5a5", border_width=1, corner_radius=15, width=90
        )
        btn_cholau.pack(side="left", padx=4)
        self.qf_btns["Long Wait"] = btn_cholau

        # VIP trip
        btn_vip = ctk.CTkButton(
            action_frame, text="VIP trip",
            command=lambda: self.toggle_quick_filter("VIP"),
            fg_color="#faf5ff", text_color="#a855f7",
            border_color="#d8b4fe", border_width=1, corner_radius=15, width=90
        )
        btn_vip.pack(side="left", padx=4)
        self.qf_btns["VIP"] = btn_vip

        # Incident
        btn_suco = ctk.CTkButton(
            action_frame, text="Incident",
            command=lambda: self.toggle_quick_filter("Incident"),
            fg_color="#f8fafc", text_color="#475569",
            border_color="#cbd5e1", border_width=1, corner_radius=15, width=80
        )
        btn_suco.pack(side="left", padx=4)
        self.qf_btns["Incident"] = btn_suco

        # High VTAT
        btn_vtat = ctk.CTkButton(
            action_frame, text="High VTAT",
            command=lambda: self.toggle_quick_filter("High VTAT"),
            fg_color="#fff7ed", text_color="#f97316",
            border_color="#fdba74", border_width=1, corner_radius=15, width=100
        )
        btn_vtat.pack(side="left", padx=4)
        self.qf_btns["High VTAT"] = btn_vtat

        self.btn_pattern = ctk.CTkButton(
            action_frame, text=" Find Common Patterns",
            command=self.f5_find_patterns, width=170,
            corner_radius=8, border_width=1
        )
        self.btn_pattern.pack(side="right", padx=4)

    def toggle_quick_filter(self, filter_name):
        if self.active_quick_filter == filter_name:
            self.active_quick_filter = None
        else:
            self.active_quick_filter = filter_name

        normal_font = ("Arial", 13)
        bold_font = ("Arial", 13, "bold")

        for name, btn in self.qf_btns.items():
            if name == self.active_quick_filter:
                btn.configure(border_width=2, font=bold_font)
            else:
                btn.configure(border_width=1, font=normal_font)

        self.f1_load_data()

    # ==========================================
    # TABLE
    # ==========================================
    def setup_f1_table(self):
        table_container = ctk.CTkFrame(
            self, fg_color="white", corner_radius=12,
            border_width=1, border_color="#e2e8f0"
        )
        table_container.pack(fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Treeview", rowheight=45, borderwidth=0,
            background="white", foreground="#334155", font=("Arial", 11)
        )
        style.configure(
            "Treeview.Heading", font=('Arial', 10, 'bold'),
            background="#f8fafc", foreground="#64748b",
            borderwidth=0, padding=10
        )
        style.map(
            "Treeview",
            background=[("selected", "white")],
            foreground=[("selected", "#0f172a")]
        )

        scrollbar = ttk.Scrollbar(table_container)
        scrollbar.pack(side="right", fill="y")

        self.table = ttk.Treeview(
            table_container,
            columns=(
                "SELECT", "Booking ID", "Date / Time", "ROUTE",
                "Vehicle", "Price", "VTAT", "Status", "STORY"
            ),
            show="headings", yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.table.yview)

        columns_width = {
            "SELECT": 60, "Booking ID": 110, "Date / Time": 130,
            "ROUTE": 250, "Vehicle": 90, "Price": 80, "VTAT": 80,
            "Status": 120, "STORY": 60,
        }
        for col, w in columns_width.items():
            self.table.heading(col, text=col.upper())
            self.table.column(
                col, width=w,
                anchor="center" if col not in ("ROUTE", "Date / Time", "Booking ID") else "w"
            )

        self.table.pack(fill="both", expand=True, padx=2, pady=2)
        self.table.bind("<ButtonRelease-1>", self.on_table_click)

    def on_table_click(self, event):
        region = self.table.identify_region(event.x, event.y)
        if region == "cell":
            col = self.table.identify_column(event.x)
            item_id = self.table.identify_row(event.y)

            # Column #1 = Checkbox
            if col == '#1':
                current_values = list(self.table.item(item_id, 'values'))
                if current_values[0] == '☐':
                    current_values[0] = '☑'
                else:
                    current_values[0] = '☐'
                self.table.item(item_id, values=current_values)
                self.update_button_states()

            # Column #9 = Story (eye icon)
            elif col == '#9':
                self.f3_show_trip_story(item_id)

    def update_button_states(self, event=None):
        selected_items = [
            item for item in self.table.get_children()
            if self.table.item(item)['values'][0] == '☑'
        ]
        selected_count = len(selected_items)

        if selected_count >= 2:
            self.btn_pattern.configure(
                state="normal", fg_color="white",
                border_color="#e9d5ff", text_color="#9333ea"
            )
        else:
            self.btn_pattern.configure(
                state="disabled", fg_color="transparent",
                border_color="#e2e8f0", text_color="#94a3b8"
            )

    def f1_reset_filters(self):
        self.search_entry.delete(0, 'end')
        self.date_picker.set_range(None, None)

        self.status_var.set("All")
        self.vehicle_var.set("All")

        self.active_quick_filter = None
        for btn in self.qf_btns.values():
            btn.configure(border_width=1, font=("Arial", 13))

        self.search_entry.configure(placeholder_text=" Booking ID...")

        self.winfo_toplevel().focus_set()
        self.f1_load_data()

    def f1_load_data(self, risk_tag_filter=None):
        self.focus_set()
        if not self.search_entry.get().strip():
            self.search_entry.configure(placeholder_text=" Booking ID...")

        for item in self.table.get_children():
            self.table.delete(item)

        conn = get_db_connection()
        if not conn:
            messagebox.showerror("Error", "Database connection failed!")
            return

        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM rides WHERE 1=1"
        params = []

        # 1. Search
        search_text = self.search_entry.get().strip()
        if search_text:
            query += " AND (`Booking ID` LIKE %s OR `Customer ID` LIKE %s)"
            params.extend([f"%{search_text}%", f"%{search_text}%"])

        # 2. Status
        if self.status_var.get() != "All":
            if self.status_var.get() == "Cancelled":
                query += " AND `Booking Status` LIKE %s"
                params.append("%Cancel%")
            else:
                query += " AND `Booking Status` LIKE %s"
                params.append(f"%{self.status_var.get()}%")

        # 3. Vehicle
        if self.vehicle_var.get() != "All":
            query += " AND `Vehicle Type` = %s"
            params.append(self.vehicle_var.get())

        # 4. Date range
        sql_start, sql_end = self.date_picker.get_range_iso()
        if sql_start:
            query += " AND `Date` >= %s"
            params.append(sql_start)
        if sql_end:
            query += " AND `Date` <= %s"
            params.append(sql_end)

        # 5. Quick filter
        active_tag = getattr(self, "active_quick_filter", None)

        if active_tag == "Long Wait":
            query += " AND `Avg VTAT` > 12 AND `Booking Status` LIKE %s"
            params.append("%Cancel%")
        elif active_tag == "VIP":
            query += " AND `Booking Value` > 600"
        elif active_tag == "Incident":
            query += " AND `Booking Status` LIKE %s"
            params.append("%Incomplete%")
        elif active_tag == "High VTAT":
            query += " AND `Avg VTAT` > 15"

        query += " LIMIT 100"

        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()

            shown_count = len(rows)
            self.badge_label.configure(
                text=f"{shown_count:,} rides shown  {self.total_db_rows:,} total"
            )

            for row in rows:
                # Date / Time
                try:
                    raw_date = datetime.datetime.strptime(
                        str(row.get('Date')), '%Y-%m-%d'
                    )
                    raw_time = str(row.get('Time'))[:5]
                    formatted_dt = raw_date.strftime('%b %d, %Y') + f" | {raw_time}"
                except Exception:
                    formatted_dt = f"{row.get('Date')} {str(row.get('Time'))[:5]}"

                # Route
                dist = row.get('Ride Distance', 0)
                route_info = (
                    f"{str(row.get('Pickup Location'))[:12]}  "
                    f"{str(row.get('Drop Location'))[:12]} [{dist} km]"
                )

                # Price
                price_val = f"${int(row.get('Booking Value', 0))}"

                # Status
                status = str(row.get('Booking Status', ''))
                if status == "Completed":
                    status_display = "⦾ Completed"
                elif "Cancel" in status:
                    status_display = "ⓧ Cancelled"
                else:
                    status_display = "⚠ Incomplete"

                self.table.insert("", "end", values=(
                    "☐",
                    f"#{row.get('Booking ID')}",
                    formatted_dt,
                    route_info,
                    row.get('Vehicle Type'),
                    price_val,
                    f"{int(row.get('Avg VTAT', 0))}m",
                    status_display,
                    "👁"
                ))

        except Exception as e:
            print("Load error:", e)
        finally:
            conn.close()
            self.update_button_states()

