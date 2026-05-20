import sys
import customtkinter as ctk

from ui.theme import UI_FONT, shared_font
from ui.widgets.modern_table import ModernTable
from ui.widgets.date_range_picker import DateRangePicker
from ui.widgets.sortable_tree import SortableTree

# Re-export for backward compatibility
__all__ = ["App", "ModernTable", "DateRangePicker", "SortableTree", "shared_font"]


class App(ctk.CTk):
    def __init__(self, frames_config=None, user=None):
        super().__init__()
        self.current_user = user
        self.title("RideHub Admin — Enterprise Edition")
        self.configure(fg_color="#F3F4F6")
        self.geometry(self._center_window(1280, 800))
        self.after(200, lambda: self.state("zoomed"))
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # ── Sidebar ──
        self.sidebar = ctk.CTkFrame(self, width=240, fg_color="#111827", corner_radius=0,
                                    border_width=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(8, weight=1)

        logo = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo.grid(row=0, column=0, pady=(25, 30), padx=20, sticky="w")
        ctk.CTkLabel(logo, text="🚕", font=(UI_FONT, 28)).pack(side="left")
        ctk.CTkLabel(logo, text=" RideHub", font=(UI_FONT, 22, "bold"),
                     text_color="#FFFFFF").pack(side="left", padx=5)

        self.nav_btns = {}
        nav_items = [
            ("📊", "Dashboard",       "Dashboard", 18),
            ("🚕", "Ride Management",  "Rides",    20),
            ("👤", "User Profiles",    "Users",    18),
            ("📈", "Risk Analysis",    "Risk",     18),
            ("🤖", "RideGuard AI",     "AI",       18),
            ("⚙️", "Settings",         "Settings", 18),
        ]
        for i, (icon, text, key, icon_size) in enumerate(nav_items, start=1):
            row_f = ctk.CTkFrame(self.sidebar, fg_color="transparent")
            row_f.grid(row=i, column=0, sticky="ew", padx=10, pady=6)
            row_f.grid_columnconfigure(1, weight=1)

            icon_box = ctk.CTkFrame(row_f, width=40, height=40,
                                    fg_color="transparent")
            icon_box.grid(row=0, column=0, padx=(2, 0))
            icon_box.grid_propagate(False)
            ctk.CTkLabel(icon_box, text=icon, font=(UI_FONT, icon_size),
                         text_color="#9CA3AF").place(relx=0.5, rely=0.5,
                                                     anchor="center")

            btn = ctk.CTkButton(
                row_f, text=text, anchor="w",
                fg_color="transparent", text_color="#9CA3AF",
                font=(UI_FONT, 14, "bold"), height=40, corner_radius=10,
                hover_color="#1F2937", command=lambda k=key: self.show_frame(k)
            )
            btn.grid(row=0, column=1, sticky="ew")
            self.nav_btns[key] = btn

        # ── Right area ──
        self.right_area = ctk.CTkFrame(self, fg_color="transparent")
        self.right_area.grid(row=0, column=1, sticky="nsew")
        self.right_area.grid_rowconfigure(1, weight=1)
        self.right_area.grid_columnconfigure(0, weight=1)

        # ── Topbar ──
        topbar = ctk.CTkFrame(self.right_area, height=70, fg_color="#FFFFFF",
                              corner_radius=0, border_width=1, border_color="#E5E7EB")
        topbar.grid(row=0, column=0, sticky="ew")
        uf = ctk.CTkFrame(topbar, fg_color="transparent")
        uf.pack(side="right", padx=30, pady=15)

        if self.current_user:
            display_name = self.current_user.get("full_name", "Admin System")
        else:
            display_name = "Admin System"

        self._user_btn_frame = ctk.CTkFrame(uf, fg_color="transparent", cursor="hand2")
        self._user_btn_frame.pack(side="left", padx=10)
        ctk.CTkLabel(self._user_btn_frame, text=display_name, font=(UI_FONT, 14, "bold"),
                     text_color="#111827").pack(side="left")
        ctk.CTkLabel(self._user_btn_frame, text="👨‍💻", font=(UI_FONT, 24)).pack(side="left")
        self._user_btn_frame.bind("<Button-1>", lambda e: self._show_user_menu())
        for child in self._user_btn_frame.winfo_children():
            child.bind("<Button-1>", lambda e: self._show_user_menu())

        self._user_menu = None

        # ── Main container for module frames ──
        self.main_container = ctk.CTkFrame(self.right_area, fg_color="transparent")
        self.main_container.grid(row=1, column=0, sticky="nsew", padx=30, pady=25)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # ── Build frames from config ──
        self.frames = {}
        if frames_config:
            for key, FrameClass in frames_config.items():
                if key == "Settings" and self.current_user:
                    self.frames[key] = FrameClass(self.main_container, self.current_user)
                else:
                    self.frames[key] = FrameClass(self.main_container)

        if self.frames:
            first_key = list(self.frames.keys())[0]
            self.show_frame(first_key)

    @staticmethod
    def _center_window(w, h):
        screen_w = 1920
        screen_h = 1080
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            screen_w = root.winfo_screenwidth()
            screen_h = root.winfo_screenheight()
            root.destroy()
        except Exception:
            pass
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        return f"{w}x{h}+{x}+{y}"

    def _show_user_menu(self):
        if self._user_menu and self._user_menu.winfo_exists():
            self._close_user_menu()
            return
        x = self._user_btn_frame.winfo_rootx() - 60
        y = self._user_btn_frame.winfo_rooty() + self._user_btn_frame.winfo_height() + 4
        self._user_menu = ctk.CTkToplevel(self)
        self._user_menu.wm_overrideredirect(True)
        self._user_menu.geometry(f"160x95+{x}+{y}")
        self._user_menu.attributes("-topmost", True)

        menu_frame = ctk.CTkFrame(self._user_menu, fg_color="#FFFFFF", border_width=1,
                                  border_color="#E5E7EB", corner_radius=8)
        menu_frame.pack(fill="both", expand=True)

        ctk.CTkButton(menu_frame, text="👤 My Profile", font=(UI_FONT, 13, "bold"),
                      fg_color="transparent", text_color="#111827", hover_color="#F3F4F6",
                      anchor="w", command=self._go_to_profile).pack(
            fill="x", padx=5, pady=(5, 2))

        ctk.CTkButton(menu_frame, text="🚪 Logout", font=(UI_FONT, 13, "bold"),
                      fg_color="transparent", text_color="#EF4444", hover_color="#FEE2E2",
                      anchor="w", command=self._logout).pack(
            fill="x", padx=5, pady=(2, 5))

        self._user_menu.bind("<FocusOut>", lambda e: self._close_user_menu())
        self._user_menu.focus_set()

    def _close_user_menu(self):
        if self._user_menu and self._user_menu.winfo_exists():
            self._user_menu.destroy()
            self._user_menu = None

    def _go_to_profile(self):
        self._close_user_menu()
        self.show_frame("Settings")

    def _logout(self):
        self._close_user_menu()
        from modules.logout import perform_logout
        perform_logout(self)

    def show_frame(self, key):
        for k, btn in self.nav_btns.items():
            if k == key:
                btn.configure(fg_color="#4F46E5", text_color="#FFFFFF", hover=False)
            else:
                btn.configure(fg_color="transparent", text_color="#9CA3AF", hover_color="#1F2937")
        for frame in self.frames.values():
            frame.grid_forget()
        if key in self.frames:
            self.frames[key].grid(row=0, column=0, sticky="nsew")

    def on_closing(self):
        self.quit()
        self.destroy()
        sys.exit(0)
