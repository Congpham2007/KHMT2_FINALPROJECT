import calendar
from datetime import datetime, date
import customtkinter as ctk
from ui.theme import UI_FONT


class DateRangePicker(ctk.CTkFrame):
    def __init__(self, parent, on_change=None, default_start=None, default_end=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.on_change = on_change
        self.start_date = default_start
        self.end_date = default_end
        self._popup = None
        self._sel_start = default_start
        self._sel_end = default_end
        self._active_field = "start"
        self._view_year = (default_start or date.today()).year
        self._view_month = (default_start or date.today()).month

        # From field
        self.from_frame = ctk.CTkFrame(self, fg_color="white", border_width=1,
                                       border_color="#E2E8F0", corner_radius=8)
        self.from_frame.pack(side="left", fill="x", expand=True, ipady=2)

        self.cal_btn = ctk.CTkButton(
            self.from_frame, text="📅", width=28, height=28,
            fg_color="transparent", hover_color="#F1F5F9",
            text_color="#475569", corner_radius=6,
            command=lambda: self._toggle_popup("start")
        )
        self.cal_btn.pack(side="left", padx=(4, 0))

        self.from_entry = ctk.CTkEntry(
            self.from_frame, font=(UI_FONT, 12), text_color="#64748B",
            fg_color="transparent", border_width=0, width=100, justify="center"
        )
        self.from_entry.pack(side="left", padx=(4, 8))
        self.from_entry.bind("<Return>", lambda e: self._on_entry_commit("start"))
        self.from_entry.bind("<FocusOut>", lambda e: self._on_entry_commit("start"))

        # Separator
        ctk.CTkLabel(self, text="→", font=(UI_FONT, 14),
                      text_color="#94A3B8").pack(side="left", padx=6)

        # To field
        self.to_frame = ctk.CTkFrame(self, fg_color="white", border_width=1,
                                     border_color="#E2E8F0", corner_radius=8)
        self.to_frame.pack(side="left", fill="x", expand=True, ipady=2)

        self.to_cal_btn = ctk.CTkButton(
            self.to_frame, text="📅", width=28, height=28,
            fg_color="transparent", hover_color="#F1F5F9",
            text_color="#475569", corner_radius=6,
            command=lambda: self._toggle_popup("end")
        )
        self.to_cal_btn.pack(side="left", padx=(4, 0))

        self.to_entry = ctk.CTkEntry(
            self.to_frame, font=(UI_FONT, 12), text_color="#64748B",
            fg_color="transparent", border_width=0, width=100, justify="center"
        )
        self.to_entry.pack(side="left", padx=(8, 4))
        self.to_entry.bind("<Return>", lambda e: self._on_entry_commit("end"))
        self.to_entry.bind("<FocusOut>", lambda e: self._on_entry_commit("end"))

        self._update_display()

    def _toggle_popup(self, field):
        if self._popup and self._popup.winfo_exists() and self._active_field == field:
            self._popup.destroy()
            self._popup = None
        else:
            if self._popup and self._popup.winfo_exists():
                self._popup.destroy()
            self._active_field = field
            self._show_popup()

    def _show_popup(self):
        self._popup = ctk.CTkToplevel(self)
        self._popup.overrideredirect(True)
        self._popup.attributes("-topmost", True)
        self._popup.configure(fg_color="white")
        self._popup.update_idletasks()
        
        target_widget = self.from_frame if self._active_field == "start" else self.to_frame
        x = target_widget.winfo_rootx()
        y = target_widget.winfo_rooty() + target_widget.winfo_height() + 2
        self._popup.geometry(f"300x320+{x}+{y}")

        ref = self.start_date if self._active_field == "start" else self.end_date
        if not ref: ref = date.today()
        self._view_year = ref.year
        self._view_month = ref.month
        self._build_calendar()

    def _build_calendar(self):
        for w in self._popup.winfo_children():
            w.destroy()

        nav = ctk.CTkFrame(self._popup, fg_color="transparent")
        nav.pack(fill="x", padx=10, pady=(10, 4))
        
        # Month navigation
        nav_month = ctk.CTkFrame(nav, fg_color="transparent")
        nav_month.pack(side="left")
        ctk.CTkButton(nav_month, text="◀", width=20, height=28, fg_color="transparent",
                      text_color="#475569", hover_color="#F1F5F9", corner_radius=6,
                      command=self._prev_month).pack(side="left")
        ctk.CTkLabel(nav_month, text=f"{calendar.month_name[self._view_month]}",
                     font=(UI_FONT, 13, "bold"), text_color="#1E293B", width=60).pack(side="left")
        ctk.CTkButton(nav_month, text="▶", width=20, height=28, fg_color="transparent",
                      text_color="#475569", hover_color="#F1F5F9", corner_radius=6,
                      command=self._next_month).pack(side="left")

        # Year navigation
        nav_year = ctk.CTkFrame(nav, fg_color="transparent")
        nav_year.pack(side="right")
        ctk.CTkButton(nav_year, text="◀", width=20, height=28, fg_color="transparent",
                      text_color="#475569", hover_color="#F1F5F9", corner_radius=6,
                      command=self._prev_year).pack(side="left")
        ctk.CTkLabel(nav_year, text=f"{self._view_year}",
                     font=(UI_FONT, 13, "bold"), text_color="#1E293B", width=40).pack(side="left")
        ctk.CTkButton(nav_year, text="▶", width=20, height=28, fg_color="transparent",
                      text_color="#475569", hover_color="#F1F5F9", corner_radius=6,
                      command=self._next_year).pack(side="left")

        days_frame = ctk.CTkFrame(self._popup, fg_color="transparent")
        days_frame.pack(fill="x", padx=10, pady=(4, 0))
        for i, d in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
            ctk.CTkLabel(days_frame, text=d, font=(UI_FONT, 10),
                         text_color="#94A3B8", width=36).grid(row=0, column=i, padx=1)

        cal = calendar.monthcalendar(self._view_year, self._view_month)
        grid = ctk.CTkFrame(self._popup, fg_color="transparent")
        grid.pack(fill="x", padx=10, pady=(4, 0))
        today = date.today()
        for r, week in enumerate(cal):
            for c, day_num in enumerate(week):
                if day_num == 0:
                    ctk.CTkLabel(grid, text="", width=36, height=28).grid(row=r, column=c, padx=1)
                    continue
                d = date(self._view_year, self._view_month, day_num)
                is_start = self._sel_start and d == self._sel_start
                is_end = self._sel_end and d == self._sel_end
                in_range = self._sel_start and self._sel_end and self._sel_start <= d <= self._sel_end
                is_today = d == today

                if is_start or is_end:
                    bg, fg = "#3B82F6", "white"
                elif in_range:
                    bg, fg = "#DBEAFE", "#1E293B"
                elif is_today:
                    bg, fg = "#F8FAFC", "#1E293B"
                else:
                    bg, fg = "transparent", "#1E293B"

                btn = ctk.CTkButton(grid, text=str(day_num), width=36, height=28,
                                    fg_color=bg, text_color=fg, hover_color="#E2E8F0",
                                    corner_radius=6, font=(UI_FONT, 11))
                btn.configure(command=lambda dd=d: self._select_date(dd))
                btn.grid(row=r, column=c, padx=1)

        bottom = ctk.CTkFrame(self._popup, fg_color="transparent")
        bottom.pack(fill="x", padx=10, pady=(8, 10))
        ctk.CTkButton(bottom, text="Today", width=60, height=28, fg_color="#F1F5F9",
                      text_color="#475569", hover_color="#E2E8F0", corner_radius=6,
                      command=lambda: self._select_date(today)).pack(side="left", padx=(0, 4))
        ctk.CTkButton(bottom, text="Clear", width=60, height=28, fg_color="#F1F5F9",
                      text_color="#475569", hover_color="#E2E8F0", corner_radius=6,
                      command=self._clear_dates).pack(side="left")
        ctk.CTkButton(bottom, text="Apply", width=60, height=28,
                      fg_color="#3B82F6", text_color="white", hover_color="#2563EB",
                      corner_radius=6, command=self._apply_selection).pack(side="right")

    def _select_date(self, d):
        if self._active_field == "start":
            self._sel_start = d
            self.start_date = d
            if self.end_date and self.start_date > self.end_date:
                self._sel_end = self.end_date = self.start_date
        else:
            self._sel_end = d
            self.end_date = d
            if self.start_date and self.end_date < self.start_date:
                self._sel_start = self.start_date = self.end_date
                
        self._update_display()
        if self._popup:
            self._popup.destroy()
            self._popup = None
            
        if self.on_change:
            self.on_change(self.start_date, self.end_date)

    def _clear_dates(self):
        self._sel_start = self.start_date = date(2024, 1, 1)
        self._sel_end = self.end_date = date(2024, 12, 31)
        self._update_display()
        if self._popup:
            self._popup.destroy()
            self._popup = None
        if self.on_change:
            self.on_change(self.start_date, self.end_date)

    def _apply_selection(self):
        if self._popup:
            self._popup.destroy()
            self._popup = None
        if self.on_change:
            self.on_change(self.start_date, self.end_date)

    def _prev_month(self):
        self._view_month = 12 if self._view_month == 1 else self._view_month - 1
        self._view_year -= 1 if self._view_month == 12 else 0
        self._build_calendar()

    def _next_month(self):
        self._view_month = 1 if self._view_month == 12 else self._view_month + 1
        self._view_year += 1 if self._view_month == 1 else 0
        self._build_calendar()

    def _prev_year(self):
        self._view_year -= 1
        self._build_calendar()

    def _next_year(self):
        self._view_year += 1
        self._build_calendar()

    def _parse_date(self, raw):
        raw = raw.strip()
        if not raw:
            return None
        parts_d = raw.split("/")
        if len(parts_d) != 3:
            return None
        month = parts_d[0].zfill(2)
        day = parts_d[1].zfill(2)
        year = parts_d[2]
        if len(year) == 4:
            year = year[2:]
        elif len(year) == 1:
            year = "0" + year
        normalized = f"{month}/{day}/{year}"
        try:
            return datetime.strptime(normalized, "%m/%d/%y").date()
        except ValueError:
            return None

    def _on_entry_commit(self, field):
        text = self.from_entry.get().strip() if field == "start" else self.to_entry.get().strip()
        
        if not text:
            if field == "start":
                self._sel_start = self.start_date = None
            else:
                self._sel_end = self.end_date = None
            self._update_display()
            return

        new_date = self._parse_date(text)
        if new_date is None:
            self._update_display()
            return
            
        if field == "start":
            self._sel_start = self.start_date = new_date
            if self.end_date and self.start_date > self.end_date:
                self._sel_end = self.end_date = self.start_date
        else:
            self._sel_end = self.end_date = new_date
            if self.start_date and self.end_date < self.start_date:
                self._sel_start = self.start_date = self.end_date
                
        self._update_display()
        if self.on_change:
            self.on_change(self.start_date, self.end_date)

    def _update_display(self):
        self.from_entry.delete(0, "end")
        self.to_entry.delete(0, "end")
        if self.start_date:
            self.from_entry.insert(0, self.start_date.strftime("%m/%d/%y"))
        if self.end_date:
            self.to_entry.insert(0, self.end_date.strftime("%m/%d/%y"))

    def set_range(self, start, end):
        self.start_date = self.end_date = None
        self._sel_start = start
        self._sel_end = end
        self.start_date = start
        self.end_date = end
        self._update_display()

    def get_range_iso(self):
        self._on_entry_commit("start")
        self._on_entry_commit("end")
        
        if not self.start_date or not self.end_date:
            self._sel_start = self.start_date = date(2024, 1, 1)
            self._sel_end = self.end_date = date(2024, 12, 31)
            self._update_display()
        return self.start_date.strftime("%Y-%m-%d"), self.end_date.strftime("%Y-%m-%d")
