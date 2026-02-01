"""
notifier.py

Desktop notification system for scam detection alerts.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from typing import Optional

def notify_risk(risk_score: float, risk_level: str, summary: str = "") -> bool:
    """Send desktop notification for scam detection results."""
    
    if risk_level in ['LOW', 'UNKNOWN']:
        return True  # No notification for low risk
    
    title = f"Scam Alert: {risk_level}"
    message = f"Risk Score: {risk_score:.0f}\n{summary}"
    
    system = platform.system()
    
    try:
        if system == "Windows":
            # Windows toast notification
            from toast import toast
            toast(title, message)
            return True
        elif system == "Darwin":  # macOS
            subprocess.run([
                "osascript", "-e",
                f'display notification "{message}" with title "{title}"'
            ])
            return True
        elif system == "Linux":
            subprocess.run([
                "notify-send", title, message
            ])
            return True
        else:
            print(f"NOTIFICATION: {title} - {message}")
            return True
    
    except Exception:
        # Fallback to console notification
        print(f"NOTIFICATION: {title} - {message}")
        return False

if __name__ == "__main__":
    # Test notification
    notify_risk(85.0, "HIGH", "Test notification for scam detection")
