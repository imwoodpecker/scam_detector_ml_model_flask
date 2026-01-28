"""
hud_messages.py

Calm, non-accusatory message selection for HUD.
We intentionally avoid panic language and legal threats.
"""

from __future__ import annotations


def pick_reason(new_signals: list[str], risk_level: str) -> str:
    # Prefer newly detected signals to explain why the popup changed *now*.
    for s in new_signals:
        if s == "CREDENTIAL_OTP":
            return "Possible scam. Do NOT share OTP, PIN, or verification codes."
        if s in ("CONTAINS_URL", "OFF_PLATFORM"):
            return "Be cautious with links or requests to move to other apps."
        if s == "PRESSURE_URGENCY":
            return "Caller is creating urgency. Take a moment and verify."
        if s == "AUTHORITY_IMPERSONATION":
            return "Be cautious: caller may be impersonating an authority or support."
        if s == "SECRECY":
            return "Caution: secrecy pressure is a common scam tactic."
        if s == "PAYMENT_METHOD_RISK":
            return "Caution: requests for gift cards/crypto/wire transfers are high-risk."
        if s == "ESCALATION_MULTIPLIER":
            return "Tone is escalating. Slow down and independently verify."

    # Fallback by risk level.
    if risk_level == "high":
        return "High risk indicators detected. Avoid sharing sensitive info."
    if risk_level == "medium":
        return "Some risk indicators detected. Stay cautious and verify."
    return "Monitoring for scam indicators."

