"""
notifier.py

Small desktop popup helper to show risk results when an audio file
has been analyzed. Uses only the Python standard library (tkinter).

If tkinter is not available (e.g., headless environment), calls are
safe no-ops.
"""

from __future__ import annotations

import threading
import time


def _show_popup(title: str, message: str, timeout_s: float = 6.0) -> None:
    """
    Show a small always-on-top popup window with the given title/message.
    Auto-closes after timeout_s seconds.
    """

    try:
        import tkinter as tk
    except Exception:
        # In environments without a GUI, silently skip.
        return

    def _worker() -> None:
        root = tk.Tk()
        root.title(title)
        root.attributes("-topmost", True)
        root.resizable(False, False)

        # Simple, compact layout.
        frame = tk.Frame(root, padx=12, pady=10)
        frame.pack(fill="both", expand=True)

        label = tk.Label(frame, text=message, justify="left")
        label.pack()

        # Center-ish on screen.
        root.update_idletasks()
        w = root.winfo_width() or 260
        h = root.winfo_height() or 80
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = int((sw - w) / 2)
        y = int(sh * 0.15)
        root.geometry(f"{w}x{h}+{x}+{y}")

        # Auto-close after timeout.
        def _close_later() -> None:
            time.sleep(timeout_s)
            try:
                root.destroy()
            except Exception:
                pass

        threading.Thread(target=_close_later, daemon=True).start()
        try:
            root.mainloop()
        except Exception:
            pass

    # Run the popup in a background thread so callers are non-blocking.
    threading.Thread(target=_worker, daemon=True).start()


def notify_risk(risk_score: float, risk_level: str, summary: str | None = None) -> None:
    """
    Public helper: show a small popup with risk level/score and
    a short human-readable reason/summary.
    """

    lvl = (risk_level or "").upper()
    title = f"Scam Shield: {lvl or 'RISK'}"
    score_txt = f"Risk score: {int(round(risk_score))}/100"
    msg_lines = [score_txt]
    if lvl:
        msg_lines.append(f"Risk level: {lvl}")
    if summary:
        msg_lines.append("")
        msg_lines.append(summary.strip())
    message = "\n".join(msg_lines)
    _show_popup(title, message)

