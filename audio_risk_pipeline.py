"""
audio_risk_pipeline.py

Single entry point to analyze a 2-person conversation audio file and output a scam risk score.

Pipeline:
audio -> STT -> (heuristic) diarization -> conversation features -> streaming scorer

Notes:
- Fully offline-capable: uses local STT backends (Whisper/Vosk) if installed and model files exist.
- Does not modify existing decision logic modules; it reuses scorer + matcher + phrase_bank.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from analysis.conversation_analyzer import analyze_conversation
from scorer import FinalReport, StreamingScorer
from stt.diarizer import diarize_segments
from stt.transcriber import TranscriberConfig, transcribe_file


def analyze_audio(audio_path: str) -> dict[str, Any]:
    """
    Public API.

    Returns:
      {
        "risk_score": float,
        "risk_level": "LOW" | "MEDIUM" | "HIGH",
        "flags": [str],
        "summary": str
      }
    """

    # Use faster-whisper explicitly to avoid the broken Vosk ZIP
    # and keep behavior stable. This assumes the faster-whisper
    # package is installed in your Python environment.
    stt_cfg = TranscriberConfig(backend="faster_whisper", model="small")
    segments = transcribe_file(audio_path, config=stt_cfg)
    diarized = diarize_segments(segments)
    features = analyze_conversation(diarized)

    # Score by feeding diarized segments as chunks (stream order preserved).
    scorer = StreamingScorer(session_id="audio")
    for s in diarized:
        text = (s.get("text") or "").strip()
        if text:
            scorer.ingest_chunk(text)

    final: FinalReport = scorer.finalize()

    # Start from streaming score, then apply conversation-level context
    # adjustments (caller dominance, multi-speaker reinforcement, etc.).
    score = float(final.risk_score)

    # Feature helpers (all default to 0 if missing for robustness).
    urgency = int(features.get("urgency_phrase_count", 0) or 0)
    otp = int(features.get("otp_credential_mentions", 0) or 0)
    money = int(features.get("money_payment_mentions", 0) or 0)
    authority = int(features.get("authority_impersonation_signals", 0) or 0)
    off_platform = int(features.get("off_platform_mentions", 0) or 0)
    secrecy = int(features.get("secrecy_mentions", 0) or 0)
    cred_harvest = int(features.get("credential_harvest_signals", 0) or 0)
    financial_accounts = int(features.get("financial_account_mentions", 0) or 0)
    known_script_hits = int(features.get("known_scam_script_hits", 0) or 0)
    dominance = float(features.get("caller_dominance_ratio_speaker1", 0.5) or 0.5)

    # --- Composite escalation based on context ---
    medium_indicators = 0
    for v in (urgency, money, off_platform, secrecy, authority, known_script_hits):
        if v > 0:
            medium_indicators += 1

    # 3+ medium indicators -> at least HIGH band.
    if medium_indicators >= 3 and score < 70:
        score = 70.0

    # Authority + any credential/financial request -> CRITICAL band.
    if authority > 0 and (otp > 0 or cred_harvest > 0 or financial_accounts > 0):
        if score < 90:
            score = 90.0

    # Caller dominance heuristic: dominant speaker asking for sensitive info
    # magnifies risk (but never creates risk from 0).
    if dominance >= 0.6 and (otp > 0 or cred_harvest > 0 or financial_accounts > 0):
        if score > 0:
            score = min(100.0, score * 1.15)

    # Ensure we never output 0 when financial credentials are in play.
    if (otp > 0 or cred_harvest > 0 or financial_accounts > 0) and score < 50:
        score = 70.0

    score = float(int(round(score)))

    # Map numeric score to external risk levels: LOW / MEDIUM / HIGH / CRITICAL
    if score >= 90:
        out_level = "CRITICAL"
    elif score >= 70:
        out_level = "HIGH"
    elif score >= 40:
        out_level = "MEDIUM"
    elif score > 0:
        out_level = "LOW"
    else:
        out_level = "LOW"

    flags = sorted(
        set(
            final.signals
            + [
                f"feature:{k}"
                for k, v in features.items()
                if k.endswith("_count") and isinstance(v, int) and v > 0
            ]
        )
    )
    summary = _build_summary(final, features)

    # Build a simple per-speaker transcript view from diarized segments.
    speaker_text: dict[str, str] = {"SPEAKER_1": "", "SPEAKER_2": ""}
    for seg in diarized:
        spk = str(seg.get("speaker") or "")
        txt = (seg.get("text") or "").strip()
        if not txt or spk not in speaker_text:
            continue
        if speaker_text[spk]:
            speaker_text[spk] += " "
        speaker_text[spk] += txt

    return {
        "risk_score": score,
        "risk_level": out_level,
        "flags": flags,
        "summary": summary,
        "transcript": {
            "segments": diarized,
            "speaker_summaries": speaker_text,
        },
        "details": {
            "features": features,
            "final_report": asdict(final),
        },
    }


def _build_summary(final: FinalReport, features: dict[str, Any]) -> str:
    parts: list[str] = []
    if features.get("otp_credential_mentions", 0) or features.get("credential_harvest_signals", 0):
        parts.append("Caller requested sensitive financial credentials (codes/card/account details).")
    if features.get("money_payment_mentions", 0):
        parts.append("High-risk payment or money-related language detected.")
    if features.get("authority_impersonation_signals", 0):
        parts.append("Caller appears to impersonate a bank, card network, or fraud/security department.")
    if features.get("urgency_phrase_count", 0):
        parts.append("Urgency/pressure tactics detected.")
    if features.get("known_scam_script_hits", 0):
        parts.append("Transcript matches known scam script patterns.")

    dominance = float(features.get("caller_dominance_ratio_speaker1", 0.5) or 0.5)
    if dominance >= 0.6 and (features.get("otp_credential_mentions", 0) or features.get("credential_harvest_signals", 0)):
        parts.append("One speaker dominates the conversation while requesting sensitive information.")

    if not parts:
        parts.append("No strong scam intent indicators detected from transcript.")
    parts.append(f"Final risk: {final.risk_level} ({final.risk_score}/100).")
    return " ".join(parts)

