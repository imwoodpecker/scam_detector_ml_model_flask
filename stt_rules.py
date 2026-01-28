"""
stt_rules.py

Rule-based STT quality tiers (no probabilities).

Input: (text, optional raw metadata from STT)
Output: tier in {"high","medium","low","partial"} plus reasons.

These rules are designed to be:
- deterministic
- auditable
- conservative (avoid over-scoring unclear text)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from matcher import tokenize


@dataclass(frozen=True)
class SttQuality:
    tier: str  # "high" | "medium" | "low" | "partial"
    reasons: list[str] = field(default_factory=list)


def assess_stt_quality(text: str) -> SttQuality:
    t = (text or "").strip()
    if not t:
        return SttQuality(tier="partial", reasons=["empty"])

    toks = tokenize(t)
    if not toks:
        return SttQuality(tier="partial", reasons=["no_tokens"])

    reasons: list[str] = []

    # Partial transcription cues (common STT artifacts)
    if t.endswith(("…", "...")):
        reasons.append("ellipsis_tail")
    if any(x in t for x in ("[inaudible]", "[noise]", "(?)")):
        reasons.append("inaudible_marker")
    if len(toks) <= 2:
        reasons.append("very_short")

    # Boost clarity when numbers/OTP-like sequences appear cleanly.
    digit_tokens = [w for w in toks if w.isdigit()]
    if digit_tokens:
        # "123456" or "12 34 56" style
        if any(len(w) >= 4 for w in digit_tokens):
            reasons.append("clear_number_token")
        if len(digit_tokens) >= 4:
            reasons.append("many_number_tokens")

    # Commands explicitness
    if any(w in toks for w in ("share", "send", "tell", "give", "click", "open", "install")):
        reasons.append("explicit_command_verb")

    # Tiering (deterministic, no probabilities)
    if "inaudible_marker" in reasons:
        return SttQuality(tier="low", reasons=reasons)
    if "very_short" in reasons and not digit_tokens:
        return SttQuality(tier="medium", reasons=reasons)
    if "ellipsis_tail" in reasons:
        return SttQuality(tier="medium", reasons=reasons)
    return SttQuality(tier="high", reasons=reasons)

