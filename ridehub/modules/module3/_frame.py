from tkinter import ttk, messagebox
import customtkinter as ctk
from data.uber import get_db_connection


class UserProfileFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.current_limit = 30
        self.max_display_limit = 100

        control_panel = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=12,
                                     border_width=1, border_color="#E5E7EB")
        control_panel.pack(fill="x", pady=(0, 20))

        top_controls = ctk.CTkFrame(control_panel, fg_color="transparent")
        top_controls.pack(fill="x", padx=15, pady=(15, 5))

        self.user_type_var = ctk.StringVar(value="Drivers")
        self.tab_menu = ctk.CTkSegmentedButton(
            top_controls, values=["Drivers", "Customers"],
            command=self.reset_and_refresh, variable=self.user_type_var,
            font=("Arial", 13, "bold"), height=35,
            selected_color="#4F46E5", selected_hover_color="#4338CA")
        self.tab_menu.pack(side="left")

        search_frame = ctk.CTkFrame(top_controls, fg_color="#F3F4F6",
                                    corner_radius=8, height=35)
        search_frame.pack(side="right", fill="x", expand=True, padx=(20, 0))
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search Booking ID...",
                                         height=35,
                                         fg_color="transparent", border_width=0,
                                         text_color="#111827",
                                         placeholder_text_color="#6B7280")
        self.search_entry.pack(fill="x", padx=10)
        self.search_entry.bind("<KeyRelease>", lambda e: self.reset_and_refresh())

        bottom_controls = ctk.CTkFrame(control_panel, fg_color="transparent")
        bottom_controls.pack(fill="x", padx=15, pady=(5, 15))

        cb_kwargs = {
            "text_color": "#111827", "font": ("Arial", 12, "bold"),
            "fg_color": "#F3F4F6", "button_color": "#F3F4F6",
            "button_hover_color": "#E5E7EB", "border_width": 0, "corner_radius": 6,
            "dropdown_fg_color": "#FFFFFF", "dropdown_hover_color": "#F3F4F6",
            "dropdown_text_color": "#111827", "state": "readonly",
            "command": self.reset_and_refresh,
        }

        bottom_controls.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.rating_filter = ctk.CTkComboBox(
            bottom_controls,
            values=["All Ratings", "⭐ 4.0+", "⭐ 4.5+", "⭐ 4.8+"], **cb_kwargs)
        self.rating_filter.set("All Ratings")
        self.rating_filter.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.trip_filter = ctk.CTkComboBox(
            bottom_controls,
            values=["All Trips", "> 3 Trips", "> 5 Trips", "> 10 Trips"], **cb_kwargs)
        self.trip_filter.set("All Trips")
        self.trip_filter.grid(row=0, column=1, padx=5, sticky="ew")

        self.risk_filter = ctk.CTkComboBox(
            bottom_controls,
            values=["All Statuses", "🔴 High Risk", "🟠 Warning",
                    "🟢 Safe", "📌 Flagged"], **cb_kwargs)
        self.risk_filter.set("All Statuses")
        self.risk_filter.grid(row=0, column=2, padx=5, sticky="ew")

        ctk.CTkButton(bottom_controls, text="🔄 Clear Filters",
                      fg_color="#F3F4F6", hover_color="#E5E7EB", border_width=0,
                      text_color="#4B5563", font=("Arial", 12, "bold"),
                      height=30, corner_radius=6, command=self.clear_filters).grid(
            row=0, column=3, padx=(5, 0), sticky="ew")

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True)
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.left_side = ctk.CTkFrame(self.main_container, width=340,
                                      fg_color="#FFFFFF", corner_radius=12,
                                      border_width=1, border_color="#E5E7EB")
        self.left_side.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.left_side.grid_propagate(False)

        list_header = ctk.CTkFrame(self.left_side, fg_color="transparent")
        list_header.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(list_header, text="ID List",
                     font=("Arial", 15, "bold"), text_color="#111827").pack(side="left")

        self.scroll_list = ctk.CTkScrollableFrame(self.left_side, fg_color="#FFFFFF",
                                                  corner_radius=0)
        self.scroll_list.pack(fill="both", expand=True, padx=5, pady=(0, 10))

        self.right_side = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.right_side.grid(row=0, column=1, sticky="nsew")

        self.refresh_list()

    def toggle_flag(self, uid):
        conn = get_db_connection()
        if not conn:
            return
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM flagged_users WHERE uid = %s", (uid,))
        if cursor.fetchone():
            cursor.execute("DELETE FROM flagged_users WHERE uid = %s", (uid,))
        else:
            cursor.execute("INSERT INTO flagged_users (uid) VALUES (%s)", (uid,))
        conn.commit()
        conn.close()
        self.refresh_list()
        self.display_detail(uid, self.user_type_var.get())

    def toggle_suspend(self, uid):
        conn = get_db_connection()
        if not conn:
            return
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM suspended_users WHERE uid = %s", (uid,))
        if cursor.fetchone():
            cursor.execute("DELETE FROM suspended_users WHERE uid = %s", (uid,))
        else:
            cursor.execute("INSERT INTO suspended_users (uid) VALUES (%s)", (uid,))
        conn.commit()
        conn.close()
        self.refresh_list()
        self.display_detail(uid, self.user_type_var.get())

    def clear_filters(self):
        self.rating_filter.set("All Ratings")
        self.trip_filter.set("All Trips")
        self.risk_filter.set("All Statuses")
        self.search_entry.delete(0, "end")
        self.reset_and_refresh()

    def reset_and_refresh(self, *args):
        if self.user_type_var.get() == "Customers":
            self.risk_filter.set("All Statuses")
            self.risk_filter.configure(state="disabled")
        else:
            self.risk_filter.configure(state="readonly")

        self.current_limit = 30
        self.refresh_list()

    def load_more(self):
        self.current_limit += 30
        if self.current_limit > self.max_display_limit:
            self.current_limit = self.max_display_limit
        self.refresh_list()

    def refresh_list(self):
        user_type = self.user_type_var.get()
        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        conn = get_db_connection()
        if not conn:
            return
        cursor = conn.cursor(dictionary=True)

        id_col = "Driver ID" if user_type == "Drivers" else "Customer ID"
        rate_col = "Driver Ratings" if user_type == "Drivers" else "Customer Rating"
        cancel_col = ("Cancelled Rides by Driver" if user_type == "Drivers"
                      else "Cancelled Rides by Customer")

        cancel_rate_expr = (
            f"COALESCE((SUM(`{cancel_col}`) / NULLIF(SUM(CASE WHEN "
            f"`Booking Status` != 'No Driver Found' THEN 1 ELSE 0 END), 0)) * 100, 0)"
        )

        cursor.execute("SELECT uid FROM flagged_users")
        flagged_set = {row['uid'] for row in cursor.fetchall()}

        cursor.execute("SELECT uid FROM suspended_users")
        suspended_set = {row['uid'] for row in cursor.fetchall()}

        where_clauses = [
            f"`{id_col}` IS NOT NULL",
            f"`{id_col}` NOT IN ('', 'None', 'NaN', '0', 'Unassigned')",
        ]
        params = []
        if self.search_entry.get().strip():
            where_clauses.append(f"`{id_col}` LIKE %s")
            params.append(f"%{self.search_entry.get().strip()}%")
        if "Flagged" in self.risk_filter.get():
            where_clauses.append(f"`{id_col}` IN (SELECT uid FROM flagged_users)")

        query = (
            f"SELECT `{id_col}` as uid, AVG(`{rate_col}`) as avg_rate, "
            f"COUNT(*) as total_trips, {cancel_rate_expr} as cancel_rate "
            f"FROM rides WHERE {' AND '.join(where_clauses)} GROUP BY `{id_col}`"
        )

        having_clauses = []
        if "4.8" in self.rating_filter.get():
            having_clauses.append(f"AVG(`{rate_col}`) >= 4.8")
        elif "4.5" in self.rating_filter.get():
            having_clauses.append(f"AVG(`{rate_col}`) >= 4.5")
        elif "4.0" in self.rating_filter.get():
            having_clauses.append(f"AVG(`{rate_col}`) >= 4.0")

        if "10" in self.trip_filter.get():
            having_clauses.append("COUNT(*) > 10")
        elif "5" in self.trip_filter.get():
            having_clauses.append("COUNT(*) > 5")
        elif "3" in self.trip_filter.get():
            having_clauses.append("COUNT(*) > 3")

        if user_type == "Drivers":
            risk = self.risk_filter.get()
            if "High Risk" in risk:
                having_clauses.append(f"{cancel_rate_expr} >= 40")
            elif "Warning" in risk:
                having_clauses.append(
                    f"{cancel_rate_expr} >= 20 AND {cancel_rate_expr} < 40")
            elif "Safe" in risk:
                having_clauses.append(f"{cancel_rate_expr} < 20")

        if having_clauses:
            query += " HAVING " + " AND ".join(having_clauses)
        query += f" ORDER BY total_trips DESC LIMIT {self.current_limit + 1}"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        has_more_in_db = len(rows) > self.current_limit
        display_rows = rows[:self.current_limit]

        if not display_rows:
            ctk.CTkLabel(self.scroll_list, text="Empty",
                         text_color="#9CA3AF").pack(pady=20)
        else:
            for user in display_rows:
                uid = user['uid']
                stars = user['avg_rate'] or 0
                trips = user['total_trips']
                c_rate = float(user['cancel_rate'])
                is_flagged = uid in flagged_set
                is_suspended = uid in suspended_set

                item_frame = ctk.CTkFrame(self.scroll_list, fg_color="#F9FAFB",
                                          corner_radius=8, height=65)
                item_frame.pack(fill="x", pady=4, padx=5)
                item_frame.pack_propagate(False)

                if user_type == "Drivers":
                    alert_text = "🔴" if c_rate >= 40 else ("🟠" if c_rate >= 20 else "👤")
                    val_color = ("#EF4444" if c_rate >= 40
                                 else ("#F59E0B" if c_rate >= 20 else "#111827"))
                    stats_text = f"⭐ {stars:.1f}  |  🏁 {trips}  |  🚫 {c_rate:.0f}%"
                else:
                    alert_text = "👤"
                    val_color = "#111827"
                    stats_text = f"⭐ {stars:.1f}  |  🏁 {trips} Trips"

                ctk.CTkLabel(item_frame, text=alert_text,
                             font=("Arial", 18)).place(x=15, y=18)
                ctk.CTkLabel(item_frame, text=uid,
                             font=("Arial", 13, "bold"),
                             text_color=val_color).place(x=50, y=10)
                ctk.CTkLabel(item_frame, text=stats_text,
                             font=("Arial", 11), text_color="#6B7280").place(x=50, y=32)

                icon_x = 0.88
                if is_suspended:
                    ctk.CTkLabel(item_frame, text="⛔",
                                 font=("Arial", 14)).place(relx=icon_x, y=10)
                    icon_x -= 0.1
                if is_flagged:
                    ctk.CTkLabel(item_frame, text="📌",
                                 font=("Arial", 14)).place(relx=icon_x, y=10)

                for w in [item_frame] + item_frame.winfo_children():
                    w.bind("<Button-1>",
                           lambda e, u=uid: self.display_detail(u, user_type))

            if has_more_in_db:
                if self.current_limit < self.max_display_limit:
                    ctk.CTkButton(self.scroll_list, text="Show More",
                                  fg_color="#EEF2FF", text_color="#4F46E5",
                                  hover_color="#E0E7FF", corner_radius=8,
                                  command=self.load_more).pack(pady=10, fill="x")
                else:
                    ctk.CTkButton(self.scroll_list, text="Limit Reached (100)",
                                  fg_color="#FEE2E2", text_color="#EF4444",
                                  hover_color="#FECACA", corner_radius=8,
                                  command=lambda: messagebox.showinfo(
                                      "Info", "Use filters to narrow down.")
                                  ).pack(pady=10, fill="x")

            self.display_detail(display_rows[0]['uid'], user_type)

    def display_detail(self, uid, user_type):
        for widget in self.right_side.winfo_children():
            widget.destroy()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        id_col = "Driver ID" if user_type == "Drivers" else "Customer ID"
        rate_col = "Driver Ratings" if user_type == "Drivers" else "Customer Rating"
        cancel_col = ("Cancelled Rides by Driver" if user_type == "Drivers"
                      else "Cancelled Rides by Customer")

        history_rating_col = ("Customer Rating" if user_type == "Drivers"
                              else "Driver Ratings")

        cancel_rate_expr = (
            f"COALESCE((SUM(`{cancel_col}`) / NULLIF(SUM(CASE WHEN "
            f"`Booking Status` != 'No Driver Found' THEN 1 ELSE 0 END), 0)) * 100, 0)"
        )
        cursor.execute(
            f"SELECT AVG(`{rate_col}`) as avg_rate, COUNT(*) as total_trips, "
            f"SUM(`Booking Value`) as total_val, {cancel_rate_expr} as cancel_rate "
            f"FROM rides WHERE `{id_col}` = %s", (uid,))
        stats = cursor.fetchone()

        cursor.execute(
            f"SELECT `Booking ID`, `Date`, `Booking Value`, `Booking Status`, "
            f"`{history_rating_col}` as trip_rating FROM rides "
            f"WHERE `{id_col}` = %s ORDER BY `Date` DESC LIMIT 5", (uid,))
        history = cursor.fetchall()

        cursor.execute("SELECT * FROM flagged_users WHERE uid = %s", (uid,))
        is_flagged = cursor.fetchone() is not None

        cursor.execute("SELECT * FROM suspended_users WHERE uid = %s", (uid,))
        is_suspended = cursor.fetchone() is not None

        conn.close()

        c_rate = float(stats['cancel_rate'])

        bg_color = "#56B6C6" if user_type == "Drivers" else "#285A48"
        header_card = ctk.CTkFrame(self.right_side, fg_color=bg_color,
                                   corner_radius=16, height=160)
        header_card.pack(fill="x", pady=(0, 20))
        header_card.pack_propagate(False)

        ctk.CTkLabel(header_card, text="👤", font=("Arial", 60),
                     fg_color="transparent", width=90, height=90).place(x=20, y=30)

        info_x = 120
        ctk.CTkLabel(header_card, text=uid,
                     font=("Arial", 28, "bold"), text_color="#FFFFFF").place(
            x=info_x, y=25)

        badge_container = ctk.CTkFrame(header_card, fg_color="transparent")
        badge_container.place(x=info_x, y=68)

        status_text = "Suspended" if is_suspended else "Active"
        status_color = "#EF4444" if is_suspended else "#34D399"
        ctk.CTkLabel(badge_container, text=f"● {status_text}",
                     font=("Arial", 11, "bold"), text_color="#FFFFFF",
                     fg_color=status_color, corner_radius=10,
                     padx=10, pady=3).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(badge_container, text=user_type[:-1],
                     font=("Arial", 11, "bold"), text_color=bg_color,
                     fg_color="#FFFFFF", corner_radius=10,
                     padx=10, pady=3).pack(side="left", padx=(0, 10))

        if is_flagged:
            ctk.CTkLabel(badge_container, text="📌 Flagged",
                         font=("Arial", 11, "bold"), text_color="#FFFFFF",
                         fg_color="#F59E0B", corner_radius=10,
                         padx=10, pady=3).pack(side="left")

        if user_type == "Drivers":
            risk_text = ("🚨 High Cancel Rate!" if c_rate >= 40
                         else ("⚠️ Needs Monitoring" if c_rate >= 20
                               else "✅ Safe Profile"))
            ctk.CTkLabel(header_card, text=f"Status: {risk_text}",
                         font=("Arial", 13), text_color="#E0E7FF").place(
                x=info_x, y=105)

        btn_flag = ctk.CTkButton(
            header_card, text="Unflag" if is_flagged else "📌 Flag",
            fg_color="#FFFFFF", text_color="#F59E0B" if is_flagged else bg_color,
            hover_color="#F3F4F6", font=("Arial", 12, "bold"), width=110,
            command=lambda u=uid: self.toggle_flag(u))
        btn_flag.place(relx=0.96, rely=0.3, anchor="e")

        if user_type == "Drivers":
            btn_suspend = ctk.CTkButton(
                header_card, text="Unsuspend" if is_suspended else "⛔ Suspend",
                fg_color="#EF4444" if not is_suspended else "#FFFFFF",
                text_color="#FFFFFF" if not is_suspended else "#EF4444",
                hover_color="#DC2626", font=("Arial", 12, "bold"), width=110,
                command=lambda u=uid: self.toggle_suspend(u))
            btn_suspend.place(relx=0.96, rely=0.7, anchor="e")

        stats_frame = ctk.CTkFrame(self.right_side, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 20))
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.create_stat_card(stats_frame, "Total Trips",
                              f"{stats['total_trips']}", "🚗", 0)
        self.create_stat_card(stats_frame,
                              "Total Spent" if user_type == "Customers" else "Revenue",
                              f"${stats['total_val'] or 0:,.0f}", "💰", 1)
        self.create_stat_card(stats_frame, "Avg Rating",
                              f"{stats['avg_rate']:.1f} ⭐" if stats['avg_rate']
                              else "N/A", "⭐", 2)

        if user_type == "Drivers":
            self.create_stat_card(stats_frame, "Cancel Rate",
                                  f"{c_rate:.1f}%", "🚫", 3,
                                  is_danger=(c_rate >= 20))

        table_container = ctk.CTkFrame(self.right_side, fg_color="#FFFFFF",
                                       corner_radius=12, border_width=1,
                                       border_color="#E5E7EB")
        table_container.pack(fill="both", expand=True)

        ctk.CTkLabel(table_container, text="Ride History (5 Recent)",
                     font=("Arial", 16, "bold"), text_color="#111827").pack(
            anchor="w", padx=20, pady=(15, 5))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#FFFFFF", fieldbackground="#FFFFFF",
                        foreground="#111827", borderwidth=0, rowheight=40,
                        font=("Arial", 12))
        style.configure("Treeview.Heading", background="#F9FAFB",
                        foreground="#6B7280", borderwidth=0,
                        font=('Arial', 11, 'bold'))
        style.map("Treeview", background=[("selected", "#EEF2FF")],
                  foreground=[("selected", "#4F46E5")])

        table = ttk.Treeview(table_container, columns=(
            "ID", "Date", "Price", "Status", "Rating"), show="headings", height=5)
        for col in table["columns"]:
            table.heading(col, text=col.upper())
            table.column(col, width=150 if col == "ID" else 100, anchor="center")
        table.pack(fill="both", expand=True, padx=2, pady=(0, 10))

        for trip in history:
            r_str = f"{trip['trip_rating']} ⭐" if trip['trip_rating'] else "N/A"
            table.insert("", "end", values=(
                trip['Booking ID'], trip['Date'],
                f"${trip['Booking Value']}", trip['Booking Status'], r_str))

    def create_stat_card(self, parent, title, val, icon, col, is_danger=False):
        card = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=12,
                            border_width=1, border_color="#E5E7EB", height=100)
        card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 15, 0))
        card.grid_propagate(False)

        icon_bg = "#FEE2E2" if is_danger else "#EEF2FF"
        icon_fg = "#EF4444" if is_danger else "#4F46E5"

        ctk.CTkLabel(card, text=icon, font=("Arial", 22),
                     fg_color=icon_bg, text_color=icon_fg,
                     width=46, height=46, corner_radius=12).place(
            relx=0.15, rely=0.5, anchor="w")

        text_frame = ctk.CTkFrame(card, fg_color="transparent")
        text_frame.place(relx=0.45, rely=0.5, anchor="w")

        ctk.CTkLabel(text_frame, text=title,
                     font=("Arial", 12), text_color="#6B7280").pack(anchor="w")
        val_color = "#EF4444" if is_danger else "#111827"
        ctk.CTkLabel(text_frame, text=val,
                     font=("Arial", 22, "bold"), text_color=val_color).pack(
            anchor="w", pady=(2, 0))
