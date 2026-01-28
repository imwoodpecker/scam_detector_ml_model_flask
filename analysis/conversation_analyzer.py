"""
analysis/conversation_analyzer.py

Consume a diarized transcript and extract conversation-level scam-relevant features.

This module reuses:
- matcher.py (tokenization + fuzzy phrase match)
- phrase_bank.py (RULE_PHRASES + SCAM_PHRASES)

No phrase logic is duplicated; we only count occurrences via existing banks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from matcher import fuzzy_phrase_match, tokenize
from phrase_bank import RULE_PHRASES, SCAM_PHRASES


class DiarizedSegment(TypedDict):
    start: float
    end: float
    speaker: str  # "SPEAKER_1" | "SPEAKER_2"
    text: str


@dataclass(frozen=True)
class AnalyzerConfig:
    fuzzy_max_dist: int = 1


def _count_rule_hits(tokens: list[str], rule_id: str, *, max_dist: int) -> int:
    phrases = RULE_PHRASES.get(rule_id, [])
    return sum(1 for p in phrases if fuzzy_phrase_match(tokens, p, max_dist=max_dist))


def _list_phrase_hits(tokens: list[str], phrases: list[str], *, max_dist: int) -> list[str]:
    hits: list[str] = []
    for p in phrases:
        if fuzzy_phrase_match(tokens, p, max_dist=max_dist):
            hits.append(p)
    return hits


def analyze_conversation(diarized: list[DiarizedSegment], config: AnalyzerConfig | None = None) -> dict[str, Any]:
    """
    Returns a structured feature dictionary for downstream decisioning/scoring.
    """

    cfg = config or AnalyzerConfig()
    full_text = " ".join((d.get("text") or "") for d in diarized).strip()
    tokens = tokenize(full_text)

    urgency = _count_rule_hits(tokens, "PRESSURE_URGENCY", max_dist=cfg.fuzzy_max_dist)
    otp = _count_rule_hits(tokens, "CREDENTIAL_OTP", max_dist=cfg.fuzzy_max_dist)
    money = _count_rule_hits(tokens, "PAYMENT_METHOD_RISK", max_dist=cfg.fuzzy_max_dist)
    authority = _count_rule_hits(tokens, "AUTHORITY_IMPERSONATION", max_dist=cfg.fuzzy_max_dist)
    off_platform = _count_rule_hits(tokens, "OFF_PLATFORM", max_dist=cfg.fuzzy_max_dist)
    secrecy = _count_rule_hits(tokens, "SECRECY", max_dist=cfg.fuzzy_max_dist)
    credential_harvest = _count_rule_hits(tokens, "CREDENTIAL_HARVESTING", max_dist=cfg.fuzzy_max_dist)
    action_request = _count_rule_hits(tokens, "ACTION_REQUEST", max_dist=cfg.fuzzy_max_dist)
    financial_accounts = _count_rule_hits(tokens, "FINANCIAL_ACCOUNT", max_dist=cfg.fuzzy_max_dist)

    scam_phrase_hits = _list_phrase_hits(tokens, SCAM_PHRASES, max_dist=cfg.fuzzy_max_dist)
    known_script_hits = _count_rule_hits(tokens, "KNOWN_SCAM_SCRIPT", max_dist=cfg.fuzzy_max_dist)

    # Speaker dominance ratio (by speaking time; deterministic from timestamps)
    dur = {"SPEAKER_1": 0.0, "SPEAKER_2": 0.0}
    for s in diarized:
        spk = str(s.get("speaker") or "")
        d = max(0.0, float(s["end"]) - float(s["start"]))
        if spk in dur:
            dur[spk] += d
    total = dur["SPEAKER_1"] + dur["SPEAKER_2"]
    dominance = (dur["SPEAKER_1"] / total) if total > 0 else 0.5

    return {
        "urgency_phrase_count": urgency,
        "otp_credential_mentions": otp,
        "money_payment_mentions": money,
        "authority_impersonation_signals": authority,
        "off_platform_mentions": off_platform,
        "secrecy_mentions": secrecy,
        # New semantic signals for richer downstream decisioning.
        "credential_harvest_signals": credential_harvest,
        "action_request_mentions": action_request,
        "financial_account_mentions": financial_accounts,
        "known_scam_script_hits": known_script_hits,
        "caller_dominance_ratio_speaker1": dominance,
        "known_scam_phrase_hits": sorted(set(scam_phrase_hits)),
        "transcript_text": full_text,
    }

