"""
AIChatbotFrame: RideGuard AI chat interface for RideHub analytics.
Features: function calling, streaming responses, quick-action chips, SQL toggle.
"""
import re
import threading

import customtkinter as ctk

from ._gemini import send_message_stream, get_or_create_chat, reset_chat

FONT       = "Arial"
INDIGO     = "#4F46E5"
INDIGO_HVR = "#4338CA"
BG_CHAT    = "#F9FAFB"
BG_BOT     = "#FFFFFF"


def _f(size, weight="normal"):
    return (FONT, size, weight)


PRESET_QUESTIONS = [
    ("Total Revenue",   "What is the total revenue for all time?"),
    ("Top 5 Drivers",   "Show me the top 5 drivers by average rating with at least 10 trips."),
    ("Cancel Rate",     "What is the cancellation rate by vehicle type?"),
    ("Daily Trends",    "Show me daily ride counts for March 2024, limited to 15 days."),
    ("Payment Split",   "What's the payment method distribution?"),
    ("DB Schema",       "List all tables and their columns in this database."),
]


class AIChatbotFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._loading    = False
        self._session_id = "default"
        self._status_lbl = None

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_chat_area()
        self._build_chips_bar()
        self._build_input_bar()

        self._set_busy("Connecting to database & loading schema...")
        threading.Thread(target=self._init_session, daemon=True).start()

    # ── Layout builders ────────────────────────────────────────────────────────

    def _build_header(self):
        bar = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=12,
                           border_width=1, border_color="#E5E7EB")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        bar.grid_columnconfigure(1, weight=1)

        # RH logo badge
        ctk.CTkLabel(bar, text="RH", font=_f(18, "bold"),
                     text_color="#FFFFFF", fg_color=INDIGO,
                     width=42, height=42, corner_radius=10).grid(
            row=0, column=0, padx=(16, 10), pady=12)

        title_box = ctk.CTkFrame(bar, fg_color="transparent")
        title_box.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(title_box, text="RideGuard AI",
                     font=_f(15, "bold"), text_color="#111827").pack(anchor="w")
        ctk.CTkLabel(title_box, text="Powered by Groq · Llama 3.3 70B · live DB",
                     font=_f(10), text_color="#6B7280").pack(anchor="w")

        ctk.CTkButton(bar, text="New Chat", font=_f(11, "bold"),
                      fg_color="#F3F4F6", text_color="#374151",
                      hover_color="#E5E7EB", height=34, width=100,
                      corner_radius=8, command=self._new_chat
                      ).grid(row=0, column=3, padx=(0, 16), pady=12)

    def _build_chat_area(self):
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_CHAT, corner_radius=12,
            border_width=1, border_color="#E5E7EB")
        self._scroll.grid(row=1, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

        self._msgs = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._msgs.pack(fill="both", expand=True, padx=4, pady=8)
        self._msgs.grid_columnconfigure(0, weight=1)

    def _build_chips_bar(self):
        chips_frame = ctk.CTkFrame(self, fg_color="transparent")
        chips_frame.grid(row=2, column=0, sticky="ew", pady=(2, 4))

        ctk.CTkLabel(chips_frame, text="Quick:", font=_f(10, "bold"),
                     text_color="#9CA3AF").pack(side="left", padx=(2, 6))

        for label, question in PRESET_QUESTIONS:
            chip = ctk.CTkButton(
                chips_frame, text=label, font=_f(10),
                fg_color="#EEF2FF", text_color=INDIGO,
                hover_color="#E0E7FF", height=26, width=0,
                corner_radius=13, border_width=1, border_color="#C7D2FE",
                command=lambda q=question: self._send_preset(q))
            chip.pack(side="left", padx=3)

    def _build_input_bar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        bar.grid_columnconfigure(0, weight=1)

        self._entry = ctk.CTkTextbox(
            bar, height=50, fg_color="#FFFFFF",
            border_color="#D1D5DB", border_width=1,
            corner_radius=10, font=_f(13),
            text_color="#111827", wrap="word")
        self._entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self._entry.bind("<Return>",       self._on_enter)
        self._entry.bind("<Shift-Return>", lambda e: None)

        self._send_btn = ctk.CTkButton(
            bar, text=">", font=_f(16, "bold"),
            width=50, height=50, corner_radius=10,
            fg_color=INDIGO, hover_color=INDIGO_HVR,
            command=self._send)
        self._send_btn.grid(row=0, column=1)

        ctk.CTkLabel(bar, text="Enter to send  |  Shift+Enter for new line",
                     font=_f(10), text_color="#9CA3AF").grid(
            row=1, column=0, sticky="w", pady=(2, 0))

    # ── Session lifecycle ──────────────────────────────────────────────────────

    def _init_session(self):
        try:
            get_or_create_chat(self._session_id)
            self.after(0, self._clear_busy)
            self.after(0, lambda: self._bot_msg(
                "Hello! I'm **RideGuard AI**, connected directly to your RideHub operational database.\n\n"
                "I use **native function calling** to query live data — no regex parsing.\n\n"
                "What I can do:\n"
                "  • Query rides, revenue, driver, and customer data\n"
                "  • Analyze trends and KPIs over time\n"
                "  • Explain table structures and data relationships\n"
                "  • Spot patterns and anomalies\n\n"
                "Try the quick-action buttons above, or type a question!"
            ))
        except Exception as exc:
            self.after(0, self._clear_busy)
            self.after(0, lambda: self._bot_msg(
                f"Database connection failed: {exc}\n\n"
                "Please verify MySQL is running, then click **New Chat** to retry."
            ))

    def _new_chat(self):
        if self._loading:
            return
        for w in self._msgs.winfo_children():
            w.destroy()
        self._set_busy("Starting new session...")
        threading.Thread(target=self._reset_session, daemon=True).start()

    def _reset_session(self):
        try:
            reset_chat(self._session_id)
            self.after(0, self._clear_busy)
            self.after(0, lambda: self._bot_msg(
                "New session started. How can I help you with your RideHub data?"))
        except Exception as exc:
            self.after(0, self._clear_busy)
            self.after(0, lambda: self._bot_msg(f"Error: {exc}\n\nPlease try again."))

    # ── Send / receive ─────────────────────────────────────────────────────────

    def _on_enter(self, event):
        if event.state & 1:
            return
        self._send()
        return "break"

    def _send_preset(self, question):
        if self._loading:
            return
        self._user_msg(question)
        tb = self._create_bot_stream_widget()
        self._set_busy("Thinking...")
        threading.Thread(target=self._stream_reply, args=(question, tb), daemon=True).start()

    def _send(self):
        if self._loading:
            return
        text = self._entry.get("0.0", "end").strip()
        if not text:
            return
        self._entry.delete("0.0", "end")
        self._user_msg(text)
        tb = self._create_bot_stream_widget()
        self._set_busy("Thinking...")
        threading.Thread(target=self._stream_reply, args=(text, tb), daemon=True).start()

    # ── Streaming UI ──────────────────────────────────────────────────────────

    def _create_bot_stream_widget(self):
        """Create an empty bot-message row with a live textbox (main thread only)."""
        row = ctk.CTkFrame(self._msgs, fg_color="transparent")
        row.pack(fill="x", pady=(6, 2), padx=4)
        row.grid_columnconfigure(1, weight=1)  # content column expands

        # RH badge
        ctk.CTkLabel(row, text="RH", font=_f(10, "bold"),
                     text_color="#FFFFFF", fg_color=INDIGO,
                     width=30, height=30, corner_radius=8).grid(
            row=0, column=0, sticky="nw", padx=(0, 8), pady=(4, 0))

        content = ctk.CTkFrame(row, fg_color=BG_BOT, corner_radius=14,
                               border_width=1, border_color="#E5E7EB")
        content.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        textbox = ctk.CTkTextbox(
            content, font=_f(13), text_color="#1F2937",
            fg_color="transparent", wrap="word",
            border_width=0, activate_scrollbars=False,
            height=28)
        textbox.pack(fill="x", padx=12, pady=(8, 4))
        textbox.insert("end", " ")

        self._scroll_bottom()
        return textbox

    def _stream_reply(self, user_text, textbox):
        """Background thread: stream tokens from Gemini, push UI updates via after()."""
        buffer = ""
        try:
            for token in send_message_stream(self._session_id, user_text):
                buffer += token
                if len(buffer) % 40 < len(token) + 5:
                    self.after(0, lambda t=buffer, tb=textbox: self._update_stream(tb, t))
        except Exception as gen_exc:
            buffer += f"\n\n[Error: {gen_exc}]"

        self.after(0, lambda t=buffer, tb=textbox: self._finish_stream(tb, t))
        self.after(0, self._clear_busy)

    def _wrap_50(self, text):
        """Insert newline every ~50 words for clean line breaks."""
        words = text.split()
        lines = []
        for i in range(0, len(words), 50):
            lines.append(" ".join(words[i:i+50]))
        return "\n".join(lines)

    def _calc_height(self, text):
        """Calculate textbox height based on wrapped line count."""
        wrapped = self._wrap_50(text)
        lines = wrapped.count("\n") + 1
        # ~24px per line + padding
        return max(40, min(1200, lines * 26 + 36))

    def _update_stream(self, textbox, text):
        """Replace live textbox content with 50-word wrapping (main thread)."""
        try:
            wrapped = self._wrap_50(text)
            textbox.configure(state="normal")
            textbox.delete("0.0", "end")
            textbox.insert("end", wrapped)
            textbox.configure(height=self._calc_height(text))
            self._scroll_bottom()
        except Exception:
            pass

    def _finish_stream(self, textbox, final_text):
        """Lock the textbox, apply 50-word wrapping, final height."""
        try:
            wrapped = self._wrap_50(final_text)
            textbox.configure(state="normal")
            textbox.delete("0.0", "end")
            textbox.insert("end", wrapped)
            textbox.configure(height=self._calc_height(final_text), state="disabled")
            self._scroll_bottom()
        except Exception:
            pass

    # ── Static messages ────────────────────────────────────────────────────────

    def _bot_msg(self, text):
        row = ctk.CTkFrame(self._msgs, fg_color="transparent")
        row.pack(fill="x", pady=(6, 2), padx=4)
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(row, text="RH", font=_f(10, "bold"),
                     text_color="#FFFFFF", fg_color=INDIGO,
                     width=30, height=30, corner_radius=8).grid(
            row=0, column=0, sticky="nw", padx=(0, 8), pady=(4, 0))

        content = ctk.CTkFrame(row, fg_color=BG_BOT, corner_radius=14,
                               border_width=1, border_color="#E5E7EB")
        content.grid(row=0, column=1, sticky="ew", padx=(0, 4))

        chunks = re.split(r"(```[\s\S]*?```)", text)
        for chunk in chunks:
            if chunk.startswith("```") and chunk.endswith("```"):
                code_content = chunk[3:-3].strip()
                code_content = re.sub(r"^\w+\n", "", code_content, count=1)
                code_frame = ctk.CTkFrame(content, fg_color="#1E293B",
                                          corner_radius=8)
                code_frame.pack(fill="x", padx=10, pady=(4, 6))
                ctk.CTkLabel(code_frame, text=code_content,
                             font=("Consolas", 11),
                             text_color="#E2E8F0", justify="left", anchor="w"
                             ).pack(padx=12, pady=10, fill="x")
            elif chunk.strip():
                wrapped = self._wrap_50(chunk.strip())
                tb = ctk.CTkTextbox(
                    content, font=_f(13), text_color="#1F2937",
                    fg_color="transparent", wrap="word",
                    border_width=0, activate_scrollbars=False)
                tb.insert("end", wrapped)
                tb.configure(state="disabled", height=self._calc_height(chunk.strip()))
                tb.pack(fill="x", padx=12, pady=(6, 4))

        self._scroll_bottom()

    def _user_msg(self, text):
        row = ctk.CTkFrame(self._msgs, fg_color="transparent")
        row.pack(fill="x", pady=(6, 2), padx=4)
        row.grid_columnconfigure(0, weight=1)

        bubble = ctk.CTkFrame(row, fg_color=INDIGO, corner_radius=14)
        bubble.grid(row=0, column=1, sticky="e", padx=(40, 0))

        ctk.CTkLabel(bubble, text=text, font=_f(13),
                     text_color="#FFFFFF", justify="left",
                     wraplength=550).pack(padx=14, pady=10)

        self._scroll_bottom()

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _set_busy(self, text):
        self._loading = True
        self._send_btn.configure(state="disabled", fg_color="#9CA3AF")
        self._entry.configure(state="disabled")
        if self._status_lbl and self._status_lbl.winfo_exists():
            self._status_lbl.destroy()
        self._status_lbl = ctk.CTkLabel(
            self._msgs, text=f"  {text}", font=_f(11),
            text_color="#6B7280", fg_color="#E5E7EB",
            corner_radius=10, padx=12, pady=4)
        self._status_lbl.pack(pady=6)
        self._scroll_bottom()

    def _clear_busy(self):
        self._loading = False
        self._send_btn.configure(state="normal", fg_color=INDIGO)
        self._entry.configure(state="normal")
        if self._status_lbl and self._status_lbl.winfo_exists():
            self._status_lbl.destroy()
            self._status_lbl = None

    def _scroll_bottom(self):
        self._scroll._parent_canvas.yview_moveto(1.0)
