"""
hud.py

Non-intrusive desktop HUD popup for PC testing (tkinter, stdlib).

Safety/UX goals:
- Never steals focus (best-effort on Windows)
- Small, always-on-top overlay in corner
- Updates text/color as risk changes
- Auto-hides when risk decays below threshold
- Avoids duplicate alerts (rate-limited)
"""

from __future__ import annotations

import threading
import time
import tkinter as tk
from dataclasses import dataclass
from queue import Empty, Queue


@dataclass(frozen=True)
class HudState:
    risk_score: int
    risk_level: str  # "minimal" | "low" | "medium" | "high"
    reason: str


class HudController:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_show_t = 0.0
        self._last_level = "minimal"
        self._visible = False

        self._root = tk.Tk()
        self._root.withdraw()
        self._root.overrideredirect(True)  # no window chrome
        self._root.attributes("-topmost", True)
        self._root.configure(bg="#111111")

        self._frame = tk.Frame(self._root, bg="#111111", highlightthickness=1, highlightbackground="#333333")
        self._frame.pack(fill="both", expand=True)

        self._title = tk.Label(self._frame, text="Safety Monitor", fg="#EEEEEE", bg="#111111", font=("Segoe UI", 10, "bold"))
        self._title.pack(anchor="w", padx=10, pady=(8, 0))

        self._body = tk.Label(self._frame, text="", fg="#DDDDDD", bg="#111111", font=("Segoe UI", 10), wraplength=260, justify="left")
        self._body.pack(anchor="w", padx=10, pady=(4, 8))

        self._place_bottom_right()

    def _place_bottom_right(self) -> None:
        self._root.update_idletasks()
        w = 290
        h = 86
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        x = max(10, sw - w - 20)
        y = max(10, sh - h - 60)
        self._root.geometry(f"{w}x{h}+{x}+{y}")

    def _style_for_level(self, level: str) -> tuple[str, str]:
        # (border, text accent)
        if level == "high":
            return ("#D64545", "#FFB3B3")
        if level == "medium":
            return ("#C29B2A", "#FFE29A")
        return ("#333333", "#DDDDDD")

    def _should_show(self, level: str) -> bool:
        return level in ("medium", "high")

    def _rate_limit_ok(self, new_level: str) -> bool:
        # Prevent alert spam; allow immediate upgrades.
        now = time.time()
        if new_level == "high" and self._last_level != "high":
            return True
        return (now - self._last_show_t) >= 3.0

    def update(self, state: HudState) -> None:
        with self._lock:
            show = self._should_show(state.risk_level)

            # Dismiss if risk drops.
            if not show:
                if self._visible:
                    self._root.withdraw()
                    self._visible = False
                self._last_level = state.risk_level
                return

            # Avoid duplicates / overwhelm.
            if not self._rate_limit_ok(state.risk_level) and state.risk_level == self._last_level:
                return

            border, accent = self._style_for_level(state.risk_level)
            self._frame.configure(highlightbackground=border)
            self._title.configure(fg=accent)
            label = f"{state.risk_level.upper()} risk · {state.risk_score}/100"
            self._title.configure(text=label)
            self._body.configure(text=state.reason)

            self._place_bottom_right()
            self._root.deiconify()
            self._visible = True
            self._last_show_t = time.time()
            self._last_level = state.risk_level

    def poll_queue(self, q: Queue[HudState], *, interval_ms: int = 100) -> None:
        """
        Tkinter MUST run on the main thread. Use this poller to apply updates
        sent from worker threads via a queue.
        """

        try:
            while True:
                state = q.get_nowait()
                self.update(state)
        except Empty:
            pass
        self._root.after(interval_ms, lambda: self.poll_queue(q, interval_ms=interval_ms))

    def loop(self) -> None:
        self._root.mainloop()

