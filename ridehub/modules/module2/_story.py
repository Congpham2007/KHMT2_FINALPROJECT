import customtkinter as ctk

from data.uber import get_db_connection


class _StoryMixin:
    """F3 – Trip Story popup."""

    def f3_show_trip_story(self, item_id=None):
        if not item_id:
            return

        item_table = self.table.item(item_id)['values']
        booking_id_raw = str(item_table[1]).replace("#", "")

        conn = get_db_connection()
        row = None
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM rides WHERE `Booking ID` = %s",
                (booking_id_raw,)
            )
            row = cursor.fetchone()
            conn.close()

        if not row:
            return

        win = ctk.CTkToplevel(self)
        win.title(f"Trip Journey - {item_table[1]}")
        win.geometry("550")
        win.configure(fg_color="#f8fafc")
        win.attributes('-topmost', True)

        # Header with risk tags
        header_f = ctk.CTkFrame(win, fg_color="transparent")
        header_f.pack(fill="x", padx=30, pady=(25, 15))

        badge_f = ctk.CTkFrame(header_f, fg_color="transparent")
        badge_f.pack(anchor="w")

        id_tag = ctk.CTkFrame(
            badge_f, fg_color="#eff6ff", corner_radius=6,
            border_width=1, border_color="#bfdbfe"
        )
        id_tag.pack(side="left")
        ctk.CTkLabel(
            id_tag, text=f"#{row.get('Booking ID', '')}",
            font=("Arial", 11, "bold"), text_color="#2563eb"
        ).pack(padx=8, pady=2)

        price_val = float(row.get('Booking Value', 0)) if row.get('Booking Value') else 0.0
        vtat_val = float(row.get('Avg VTAT', 0)) if row.get('Avg VTAT') else 0.0
        status_raw = str(row.get('Booking Status', ''))

        risks = []
        if price_val > 600:
            risks.append((" VIP Trip", "#fef9c3", "#fde047", "#854d0e"))
        if vtat_val > 12 and "Cancel" in status_raw:
            risks.append((" Long Wait", "#fecaca", "#fca5a5", "#b91c1c"))
        if vtat_val > 15:
            risks.append((" High VTAT", "#fed7aa", "#fdba74", "#c2410c"))
        if "Incomplete" in status_raw:
            risks.append((" Incident", "#f1f5f9", "#cbd5e1", "#334155"))

        for text, bg, border, txt_color in risks:
            r_tag = ctk.CTkFrame(
                badge_f, fg_color=bg, corner_radius=12,
                border_width=1, border_color=border
            )
            r_tag.pack(side="left", padx=(10, 0))
            ctk.CTkLabel(
                r_tag, text=text, font=("Arial", 11, "bold"),
                text_color=txt_color
            ).pack(padx=10, pady=2)

        ctk.CTkLabel(
            header_f, text="Trip Story Timeline",
            font=("Arial", 22, "bold"), text_color="#1e293b"
        ).pack(anchor="w", pady=(10, 2))
        subtitle = (
            f"{row.get('Date', '')}    "
            f"{row.get('Pickup Location', '')}  "
            f"{row.get('Drop Location', '')}"
        )
        ctk.CTkLabel(
            header_f, text=subtitle, font=("Arial", 13), text_color="#94a3b8"
        ).pack(anchor="w")

        # Timeline cards
        body_f = ctk.CTkFrame(win, fg_color="transparent")
        body_f.pack(fill="both", expand=True, padx=30)

        time_str = str(row.get('Time', ''))[:5] if row.get('Time') else ""

        steps = [
            {
                "title": "Booking Confirmed",
                "desc": (f"Via app  Payment: {row.get('Payment Method', 'N/A')}  "
                        f"Time: {time_str}"),
                "icon": "✓", "color": "#10b981"
            },
            {
                "title": "Driver Assigned",
                "desc": (f"Driver ID: {str(row.get('Customer ID', ''))}  "
                        f"Vehicle: {row.get('Vehicle Type', '')}"),
                "icon": "🚗", "color": "#3b82f6"
            },
            {
                "title": f"Wait Time  VTAT: {int(vtat_val)} min",
                "desc": "Driver is approaching pickup point.",
                "icon": "⏳",
                "color": "#f59e0b" if vtat_val > 8 else "#3b82f6"
            },
            {
                "title": "Trip Started",
                "desc": (f"{row.get('Pickup Location', '')}  "
                        f"{row.get('Drop Location', '')} "
                        f"({row.get('Ride Distance', 0)} km)"),
                "icon": "📍", "color": "#6366f1"
            },
        ]

        if "Completed" in status_raw:
            steps.append({
                "title": "Trip Finished",
                "desc": (f"Completed {row.get('Ride Distance', 0)}km  "
                        f"Price: ${int(price_val)}  "
                        f"Rating: {row.get('Customer Rating', 0)}"),
                "icon": "✓", "color": "#10b981"
            })
        else:
            steps.append({
                "title": "Trip Interrupted",
                "desc": f"Status: {status_raw}  Distance: {row.get('Ride Distance', 0)}km",
                "icon": "✕", "color": "#ef4444"
            })

        for i, step in enumerate(steps):
            item_f = ctk.CTkFrame(body_f, fg_color="transparent")
            item_f.pack(fill="x", pady=10)

            icon_f = ctk.CTkFrame(item_f, fg_color="transparent", width=40)
            icon_f.pack(side="left", fill="y")

            circle = ctk.CTkFrame(
                icon_f, width=32, height=32, corner_radius=16,
                fg_color="white", border_width=2, border_color=step['color']
            )
            circle.pack()
            circle.pack_propagate(False)
            ctk.CTkLabel(
                circle, text=step['icon'],
                font=("Arial", 14, "bold"), text_color=step['color']
            ).place(relx=0.5, rely=0.5, anchor="center")

            card = ctk.CTkFrame(
                item_f, fg_color="white", corner_radius=10,
                border_width=1, border_color="#e2e8f0"
            )
            card.pack(side="left", fill="x", expand=True, padx=(15, 0))

            if i == 2 and vtat_val > 8:
                card.configure(border_color="#fde68a", fg_color="#fffbeb")
                ctk.CTkLabel(
                    card,
                    text=f" High wait detected! Driver arrived {int(vtat_val)} min after booking.",
                    font=("Arial", 11, "italic"), text_color="#9a3412"
                ).pack(anchor="w", padx=15, pady=(2, 8))

            ctk.CTkLabel(
                card, text=step['title'],
                font=("Arial", 13, "bold"), text_color="#1e293b"
            ).pack(anchor="w", padx=15, pady=(8, 0))
            ctk.CTkLabel(
                card, text=step['desc'],
                font=("Arial", 12), text_color="#64748b"
            ).pack(anchor="w", padx=15, pady=(0, 8))

        # System auto-comment
        comment_f = ctk.CTkFrame(
            win, fg_color="#f4f8ff", corner_radius=12,
            border_width=1, border_color="#dbeafe"
        )
        comment_f.pack(side="top", fill="x", padx=30, pady=(5, 20), ipady=5)

        ctk.CTkLabel(
            comment_f, text=" SYSTEM AUTO-COMMENT",
            font=("Arial", 12, "bold"), text_color="#2563eb"
        ).pack(anchor="w", padx=20, pady=(12, 0))

        avg_sys = 6.0
        if vtat_val > avg_sys * 1.5:
            diff = int(vtat_val - avg_sys)
            analysis = (
                f" Elevated wait time ({int(vtat_val)} min). "
                f"Driver took {diff} min longer than the {int(avg_sys)} min "
                f"zone benchmark. This is a major risk factor."
            )
        else:
            analysis = (
                " Operational metrics are within safe system limits. "
                "No anomalies detected."
            )

        ctk.CTkLabel(
            comment_f, text=analysis, font=("Arial", 13),
            text_color="#475569", wraplength=440, justify="left"
        ).pack(anchor="w", padx=20, pady=(5, 12))
