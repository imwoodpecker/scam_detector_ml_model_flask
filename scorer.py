"""
scorer.py

Heuristic risk scoring logic for scam detection.
Offline + deterministic + explainable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from matcher import fuzzy_phrase_match, tokenize
from phrase_bank import RULE_PHRASES, SCAM_PHRASES, SUSPICIOUS_KEYWORDS
from timeline import Timeline


@dataclass
class RiskReport:
    risk_score: int
    risk_level: str
    matched_phrases: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)


@dataclass
class Evidence:
    rule_id: str
    weight: int
    description: str
    matches: list[str] = field(default_factory=list)


@dataclass
class Assessment:
    """
    Structured risk assessment suitable for Android consumption.
    """

    risk_score: int
    risk_level: str
    evidences: list[Evidence] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    chunk_index: int | None = None
    is_final: bool = False


_URL_RE = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
_PHONE_RE = re.compile(r"\b(?:\+?\d[\d\-\s]{7,}\d)\b")
_MONEY_RE = re.compile(r"\b(?:₹|\$|€|£)\s*\d+(?:[.,]\d+)?\b")
_ALL_CAPS_RE = re.compile(r"\b[A-Z]{4,}\b")


def _clamp(n: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, n))


def _level(score: int) -> str:
    """
    Internal risk banding for streaming/UI flows.
    Audio JSON mapping in audio_risk_pipeline.py normalizes to
    LOW / MEDIUM / HIGH / CRITICAL for external consumers.
    """
    if score >= 90:
        return "high"  # treated as CRITICAL in audio_risk_pipeline
    if score >= 70:
        return "high"
    if score >= 50:
        return "medium"
    if score >= 25:
        return "low"
    return "minimal"


def _add_evidence(evidences: list[Evidence], rule_id: str, weight: int, description: str, matches: Iterable[str]) -> int:
    m = [x for x in matches if x]
    if not m:
        return 0
    evidences.append(Evidence(rule_id=rule_id, weight=weight, description=description, matches=sorted(set(m))))
    return weight


def assess_text(
    text: str,
    *,
    timeline: Timeline | None = None,
    chunk_index: int | None = None,
    is_final: bool = False,
) -> Assessment:
    """
    Deterministically assess the current transcript and return explainable evidence.
    """

    t = (text or "").strip()
    t_low = t.lower()

    score = 0
    evidences: list[Evidence] = []
    signals: list[str] = []

    # --- Core rule groups (explainable) ---
    score += _add_evidence(
        evidences,
        "PRESSURE_URGENCY",
        10,
        "Pressure/urgency language detected.",
        (p for p in RULE_PHRASES.get("PRESSURE_URGENCY", []) if p in t_low),
    )
    score += _add_evidence(
        evidences,
        "CREDENTIAL_OTP",
        20,
        "Credential/OTP solicitation language detected.",
        (p for p in RULE_PHRASES.get("CREDENTIAL_OTP", []) if p in t_low),
    )
    score += _add_evidence(
        evidences,
        "PAYMENT_METHOD_RISK",
        20,
        "High-risk payment method language detected (gift cards/crypto/wire).",
        (p for p in RULE_PHRASES.get("PAYMENT_METHOD_RISK", []) if p in t_low),
    )
    score += _add_evidence(
        evidences,
        "OFF_PLATFORM",
        8,
        "Attempts to move conversation off-platform detected.",
        (p for p in RULE_PHRASES.get("OFF_PLATFORM", []) if p in t_low),
    )
    score += _add_evidence(
        evidences,
        "SECRECY",
        12,
        "Secrecy/manipulation language detected.",
        (p for p in RULE_PHRASES.get("SECRECY", []) if p in t_low),
    )
    score += _add_evidence(
        evidences,
        "AUTHORITY_IMPERSONATION",
        12,
        "Authority/customer-support impersonation language detected.",
        (p for p in RULE_PHRASES.get("AUTHORITY_IMPERSONATION", []) if p in t_low),
    )

    # --- Phrase bank (back-compat + extra evidence) ---
    phrase_hits = [phrase for phrase in SCAM_PHRASES if phrase in t_low]
    if phrase_hits:
        # Keep weight modest since rule groups already cover many phrases.
        score += _add_evidence(
            evidences,
            "PHRASE_BANK_HIT",
            min(25, 3 * len(set(phrase_hits))),
            "Known scam phrase(s) detected from phrase bank.",
            phrase_hits,
        )

    # --- Keyword density (signal-level) ---
    kw_hits = sorted({kw for kw in SUSPICIOUS_KEYWORDS if kw in t_low})
    if kw_hits:
        signals.append(f"keywords:{','.join(kw_hits[:10])}" + ("..." if len(kw_hits) > 10 else ""))
        score += min(20, 2 * len(kw_hits))

    # --- Regex-based signals ---
    if _URL_RE.search(t):
        signals.append("contains_url")
        score += 12
    if _PHONE_RE.search(t):
        signals.append("contains_phone_number")
        score += 6
    if _MONEY_RE.search(t):
        signals.append("mentions_money_amount")
        score += 6

    caps_words = _ALL_CAPS_RE.findall(t)
    if len(caps_words) >= 3:
        signals.append("excessive_caps")
        score += 6
    if t.count("!") >= 3:
        signals.append("excessive_exclamation")
        score += 4

    # --- Sequence/behavioral logic (session-scoped) ---
    if timeline is not None:
        timeline.add("assessed_transcript", detail=f"len={len(t)}")

        # Mark events based on evidence presence (deterministic).
        eids = {e.rule_id for e in evidences}
        if "AUTHORITY_IMPERSONATION" in eids:
            timeline.add("authority_signal")
        if "PRESSURE_URGENCY" in eids:
            timeline.add("urgency_signal")
        if "CREDENTIAL_OTP" in eids or "PAYMENT_METHOD_RISK" in eids:
            timeline.add("action_signal")

        # Bonus when attacker pattern emerges: authority -> urgency -> action across chunks.
        has_auth = timeline.count("authority_signal") > 0
        has_urg = timeline.count("urgency_signal") > 0
        has_act = timeline.count("action_signal") > 0
        if has_auth and has_urg and has_act:
            signals.append("dangerous_sequence:authority_urgency_action")
            score += 10

        # Repeated pressure tactics in a session
        pressure_count = timeline.count("urgency_signal")
        if pressure_count >= 3:
            signals.append("repeated_pressure_tactics_in_session")
            score += 10

    score = _clamp(score)
    return Assessment(
        risk_score=score,
        risk_level=_level(score),
        evidences=evidences,
        signals=signals,
        chunk_index=chunk_index,
        is_final=is_final,
    )


@dataclass
class TraceEntry:
    chunk_index: int
    change: int
    rule_id: str
    why: str
    contributed: int


@dataclass
class StreamingSnapshot:
    chunk_index: int
    risk_score: int
    risk_level: str
    newly_detected_signals: list[str] = field(default_factory=list)
    score_delta: int = 0


@dataclass
class FinalReport:
    risk_score: int
    risk_level: str
    signals: list[str]
    trace: list[TraceEntry]


class StreamingScorer:
    """
    Deterministic streaming scorer with:
    - confidence decay over chunk order
    - escalation gradient multipliers
    - false-positive suppression cues
    - traceability for every score change
    """

    def __init__(self, *, session_id: str = "default") -> None:
        self.session_id = session_id
        self.timeline = Timeline(session_id=session_id)
        self.tokens: list[str] = []
        self.chunk_index = 0

        # Active signal strengths [0..1], decayed each chunk unless reinforced.
        self._strengths: dict[str, float] = {}
        self._emitted_signals: set[str] = set()

        # Escalation stage tracking (0 normal, 1 warning, 2 threat)
        self._escalation_stage = 0

        # Score + trace
        self._score = 0
        self._trace: list[TraceEntry] = []

    def _decay(self) -> None:
        # Deterministic per-chunk exponential-ish decay.
        decay = 0.90
        for k in list(self._strengths.keys()):
            self._strengths[k] *= decay
            if self._strengths[k] < 0.05:
                del self._strengths[k]

    def _reinforce(self, signal_id: str, *, add: float = 0.5) -> None:
        cur = self._strengths.get(signal_id, 0.0)
        self._strengths[signal_id] = min(1.0, cur + add)

    def _match_any(self, rule_id: str, *, max_dist: int = 1) -> list[str]:
        hits: list[str] = []
        for phr in RULE_PHRASES.get(rule_id, []):
            if fuzzy_phrase_match(self.tokens, phr, max_dist=max_dist):
                hits.append(phr)
        return hits

    def _has_high_risk_asks(self) -> bool:
        """
        True when transcript involves clear scam asks:
        - OTP / payment / off-platform
        - credential harvesting / financial account discussion
        - explicit action requests
        - authority impersonation framing
        Used to *disable* false-positive suppression.
        """

        return bool(
            self._match_any("CREDENTIAL_OTP")
            or self._match_any("PAYMENT_METHOD_RISK")
            or self._match_any("OFF_PLATFORM")
            or self._match_any("CREDENTIAL_HARVESTING")
            or self._match_any("FINANCIAL_ACCOUNT")
            or self._match_any("ACTION_REQUEST")
            or self._match_any("AUTHORITY_IMPERSONATION")
        )

    def ingest_chunk(self, chunk: str) -> StreamingSnapshot:
        self.chunk_index += 1
        self.timeline.add("chunk_ingested", detail=f"i={self.chunk_index},len={len(chunk or '')}")

        # Update tokens (streaming-friendly; tokenization is deterministic)
        self.tokens.extend(tokenize(chunk))

        # Apply decay before evaluating this chunk (signals weaken if not reinforced)
        self._decay()

        newly: list[str] = []
        score_before = self._score

        def add_signal(signal_id: str, base_points: int, why: str, *, reinforce: float = 0.6) -> None:
            nonlocal newly
            prev_strength = self._strengths.get(signal_id, 0.0)
            self._reinforce(signal_id, add=reinforce)
            strength = self._strengths.get(signal_id, 0.0)

            # Points are proportional to strength; only the delta contributes this chunk.
            prev_pts = int(round(base_points * prev_strength))
            cur_pts = int(round(base_points * strength))
            delta = cur_pts - prev_pts
            if delta != 0:
                self._score = _clamp(self._score + delta)
                self._trace.append(
                    TraceEntry(
                        chunk_index=self.chunk_index,
                        change=delta,
                        rule_id=signal_id,
                        why=why,
                        contributed=delta,
                    )
                )

            if signal_id not in self._emitted_signals:
                newly.append(signal_id)
                self._emitted_signals.add(signal_id)

        # --- Core detections (fuzzy, reorder-tolerant) ---
        if self._match_any("PRESSURE_URGENCY"):
            add_signal("PRESSURE_URGENCY", 20, "Pressure/urgency language increases scam likelihood.")
        if self._match_any("CREDENTIAL_OTP"):
            add_signal("CREDENTIAL_OTP", 35, "OTP/credential solicitation is a high-confidence scam intent.")
        if self._match_any("CREDENTIAL_HARVESTING"):
            add_signal("CREDENTIAL_HARVESTING", 35, "Requests for card/account numbers are high-risk credential harvesting.")
        if self._match_any("PAYMENT_METHOD_RISK"):
            add_signal("PAYMENT_METHOD_RISK", 30, "High-risk payment methods (gift card/crypto/wire) are common in scams.")
        if self._match_any("OFF_PLATFORM"):
            add_signal("OFF_PLATFORM", 12, "Moving off-platform reduces safeguards; common in scams.")
        if self._match_any("SECRECY"):
            add_signal("SECRECY", 18, "Secrecy/manipulation language is a scam signal.")
        if self._match_any("AUTHORITY_IMPERSONATION"):
            add_signal("AUTHORITY_IMPERSONATION", 18, "Authority/support impersonation elevates risk.")

        # --- Escalation gradient (multiplier, not flat bonus) ---
        warning = bool(self._match_any("ESCALATION_WARNING"))
        threat = bool(self._match_any("ESCALATION_THREAT"))
        stage = 2 if threat else 1 if warning else 0
        if stage > self._escalation_stage:
            # Multiplier applied to current score (bounded), recorded as trace.
            mult = 1.10 if stage == 1 else 1.25
            new_score = _clamp(int(round(self._score * mult)))
            delta = new_score - self._score
            if delta != 0:
                self._score = new_score
                self._trace.append(
                    TraceEntry(
                        chunk_index=self.chunk_index,
                        change=delta,
                        rule_id="ESCALATION_MULTIPLIER",
                        why=f"Language escalation stage increased to {stage}; applying multiplier {mult:.2f}.",
                        contributed=delta,
                    )
                )
            self._escalation_stage = stage
            if "ESCALATION_MULTIPLIER" not in self._emitted_signals:
                newly.append("ESCALATION_MULTIPLIER")
                self._emitted_signals.add("ESCALATION_MULTIPLIER")

        # --- Lightweight non-regex signals (kept conservative) ---
        # URL/phone/money still ok via small regexes (already in codebase).
        joined = " ".join(self.tokens)
        if _URL_RE.search(joined):
            add_signal("CONTAINS_URL", 10, "Links are often used to phish credentials/payments.", reinforce=0.4)
        if _PHONE_RE.search(joined):
            add_signal("CONTAINS_PHONE", 6, "Phone numbers can be used to move off-platform.", reinforce=0.3)
        if _MONEY_RE.search(joined):
            add_signal("MENTIONS_MONEY", 6, "Money amounts can indicate payment pressure.", reinforce=0.3)

        # --- False-positive suppression (reduce without resetting) ---
        benign_identity = bool(self._match_any("BENIGN_IDENTITY", max_dist=0))
        benign_ref = bool(self._match_any("BENIGN_REFERENCE", max_dist=0)) or any(w.isdigit() and len(w) >= 6 for w in self.tokens)
        benign_callback = bool(self._match_any("BENIGN_CALLBACK", max_dist=0))
        has_risky_asks = self._has_high_risk_asks()

        # Suppression is *disabled* whenever risky asks / financial accounts /
        # explicit actions / authority framing are present.
        if (benign_identity or benign_ref or benign_callback) and not has_risky_asks:
            # Suppress a bit, but never below 0, and never erase prior risk.
            suppress = -min(15, max(5, int(round(self._score * 0.20))))
            if suppress != 0:
                new_score = _clamp(self._score + suppress)
                delta = new_score - self._score
                if delta != 0:
                    self._score = new_score
                    self._trace.append(
                        TraceEntry(
                            chunk_index=self.chunk_index,
                            change=delta,
                            rule_id="FALSE_POSITIVE_SUPPRESSION",
                            why="Benign caller cues (identity/reference/callback) present without scam asks (OTP/link/immediate action).",
                            contributed=delta,
                        )
                    )
                if "FALSE_POSITIVE_SUPPRESSION" not in self._emitted_signals:
                    newly.append("FALSE_POSITIVE_SUPPRESSION")
                    self._emitted_signals.add("FALSE_POSITIVE_SUPPRESSION")

        delta_total = self._score - score_before
        return StreamingSnapshot(
            chunk_index=self.chunk_index,
            risk_score=self._score,
            risk_level=_level(self._score),
            newly_detected_signals=newly,
            score_delta=delta_total,
        )

    def finalize(self) -> FinalReport:
        """
        Freeze the streaming score and apply hard, explainable overrides:
        - Credential harvesting escalation (min HIGH / CRITICAL)
        - Composite multi-signal escalation (many weak cues together)
        """

        # --- Hard credential-harvesting rule (cannot be suppressed) ---
        has_otp = bool(self._match_any("CREDENTIAL_OTP"))
        has_cred_harvest = bool(self._match_any("CREDENTIAL_HARVESTING"))
        has_financial_acct = bool(self._match_any("FINANCIAL_ACCOUNT"))
        has_authority = bool(self._match_any("AUTHORITY_IMPERSONATION"))
        has_action = bool(self._match_any("ACTION_REQUEST"))

        # Treat any combination of these as strong credential harvesting.
        credential_risk = has_otp or has_cred_harvest or has_financial_acct
        if credential_risk and has_action:
            # At least HIGH; if combined with authority, treat as CRITICAL band.
            target = 90 if has_authority else 75
            if self._score < target:
                delta = target - self._score
                self._score = target
                self._trace.append(
                    TraceEntry(
                        chunk_index=self.chunk_index,
                        change=delta,
                        rule_id="HARD_RULE_CREDENTIAL_HARVEST",
                        why="Transcript includes requests for financial credentials (card/account/code). Escalating minimum risk.",
                        contributed=delta,
                    )
                )

        # --- Composite escalation: many "medium" indicators together ---
        medium_indicators = 0
        if self._match_any("PRESSURE_URGENCY"):
            medium_indicators += 1
        if self._match_any("PAYMENT_METHOD_RISK"):
            medium_indicators += 1
        if self._match_any("SECRECY"):
            medium_indicators += 1
        if self._match_any("OFF_PLATFORM"):
            medium_indicators += 1
        if self._match_any("ESCALATION_WARNING"):
            medium_indicators += 1

        if medium_indicators >= 3 and self._score < 70:
            target = 70
            delta = target - self._score
            self._score = target
            self._trace.append(
                TraceEntry(
                    chunk_index=self.chunk_index,
                    change=delta,
                    rule_id="CONTEXT_MULTI_MEDIUM",
                    why="Multiple medium-strength scam indicators co-occur (pressure/payment/secrecy/off-platform/escalation).",
                    contributed=delta,
                )
            )

        # Final signals are whatever we have ever emitted, sorted.
        return FinalReport(
            risk_score=self._score,
            risk_level=_level(self._score),
            signals=sorted(self._emitted_signals),
            trace=self._trace,
        )


def score_text(text: str, timeline: Timeline | None = None) -> RiskReport:
    # Backwards-compatible wrapper around the newer explainable assessment.
    a = assess_text(text, timeline=timeline)

    matched_phrases: list[str] = []
    for ev in a.evidences:
        if ev.rule_id in ("PHRASE_BANK_HIT",):
            matched_phrases.extend(ev.matches)

    return RiskReport(
        risk_score=a.risk_score,
        risk_level=a.risk_level,
        matched_phrases=sorted(set(matched_phrases)),
        signals=a.signals,
    )

