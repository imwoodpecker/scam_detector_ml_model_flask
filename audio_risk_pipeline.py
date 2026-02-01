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

import os
from dataclasses import asdict
from typing import Any

from analysis.conversation_analyzer import analyze_conversation
from audio_preprocess import preprocess_audio, get_audio_metrics, cleanup_processed_audio
from matcher import tokenize
from phrase_bank import RULE_PHRASES, SUSPICIOUS_KEYWORDS
from simple_advanced_scorer import SimpleAdvancedScorer
from scorer import StreamingScorer, FinalReport
from stt.diarizer import diarize_segments
from stt.transcriber import TranscriberConfig, transcribe_file_with_meta
from transcript_quality import assess_transcript_quality


_LANG_NAMES: dict[str, str] = {
    "hi": "Hindi",
    "ta": "Tamil",
    "ml": "Malayalam",
    "te": "Telugu",
}


def _normalize_lang(code: str | None) -> str | None:
    if not code:
        return None
    c = str(code).strip().lower()
    # common aliases / misspellings
    if c in {"telgu", "telugu"}:
        return "te"
    if c in {"tamil"}:
        return "ta"
    if c in {"hindi"}:
        return "hi"
    if c in {"malayalam"}:
        return "ml"
    return c


def _guess_language_from_filename(audio_path: str) -> str | None:
    """
    Best-effort language guess from filename script.
    Helps prevent cases where STT auto-detect misclassifies Hindi as zh.
    """

    name = os.path.basename(audio_path or "")
    if not name:
        return None
    # Unicode block heuristics (very lightweight)
    for ch in name:
        o = ord(ch)
        # Devanagari
        if 0x0900 <= o <= 0x097F:
            return "hi"
        # Tamil
        if 0x0B80 <= o <= 0x0BFF:
            return "ta"
        # Telugu
        if 0x0C00 <= o <= 0x0C7F:
            return "te"
        # Malayalam
        if 0x0D00 <= o <= 0x0D7F:
            return "ml"
    return None


def _text_unicode_stats(text: str) -> dict[str, float]:
    """
    Rough unicode script ratios to detect wrong-script output
    (e.g. Hindi audio getting decoded into Chinese characters).
    """

    t = text or ""
    if not t:
        return {"cjk": 0.0, "devanagari": 0.0, "tamil": 0.0, "telugu": 0.0, "malayalam": 0.0, "latin": 0.0}

    total = 0
    counts = {"cjk": 0, "devanagari": 0, "tamil": 0, "telugu": 0, "malayalam": 0, "latin": 0}
    for ch in t:
        if ch.isspace():
            continue
        total += 1
        o = ord(ch)
        if 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF:
            counts["cjk"] += 1
        elif 0x0900 <= o <= 0x097F:
            counts["devanagari"] += 1
        elif 0x0B80 <= o <= 0x0BFF:
            counts["tamil"] += 1
        elif 0x0C00 <= o <= 0x0C7F:
            counts["telugu"] += 1
        elif 0x0D00 <= o <= 0x0D7F:
            counts["malayalam"] += 1
        elif (0x0041 <= o <= 0x005A) or (0x0061 <= o <= 0x007A):
            counts["latin"] += 1

    if total <= 0:
        return {"cjk": 0.0, "devanagari": 0.0, "tamil": 0.0, "telugu": 0.0, "malayalam": 0.0, "latin": 0.0}
    return {k: (v / total) for k, v in counts.items()}


def _keyword_rule_score(text: str) -> int:
    toks = tokenize(text or "")
    if not toks:
        return 0
    joined = " ".join(toks)
    kw_hits = sum(1 for kw in SUSPICIOUS_KEYWORDS if kw and kw in joined)
    rule_hits = 0
    for rid in ("CREDENTIAL_OTP", "CREDENTIAL_HARVESTING", "PAYMENT_METHOD_RISK", "SECRECY", "AUTHORITY_IMPERSONATION", "PRESSURE_URGENCY"):
        for phr in RULE_PHRASES.get(rid, []):
            if phr and phr.lower() in joined:
                rule_hits += 1
    return kw_hits + (2 * rule_hits)


def _transcript_quality(text: str, *, target_lang: str | None) -> float:
    stats = _text_unicode_stats(text)
    score = float(_keyword_rule_score(text))
    score -= 100.0 * float(stats.get("cjk", 0.0) or 0.0)
    if target_lang == "hi":
        score += 20.0 * float(stats.get("devanagari", 0.0) or 0.0) + 5.0 * float(stats.get("latin", 0.0) or 0.0)
    elif target_lang == "ta":
        score += 20.0 * float(stats.get("tamil", 0.0) or 0.0) + 5.0 * float(stats.get("latin", 0.0) or 0.0)
    elif target_lang == "te":
        score += 20.0 * float(stats.get("telugu", 0.0) or 0.0) + 5.0 * float(stats.get("latin", 0.0) or 0.0)
    elif target_lang == "ml":
        score += 20.0 * float(stats.get("malayalam", 0.0) or 0.0) + 5.0 * float(stats.get("latin", 0.0) or 0.0)
    else:
        score += 2.0 * float(stats.get("latin", 0.0) or 0.0)
    return score


def analyze_audio(audio_path: str) -> dict[str, Any]:
    """
    Public API.

    Returns:
      {
        "risk_score": float | null,
        "risk_level": "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN",
        "transcript_quality": dict,
        "audio_quality": dict,
        "stt_backend": dict,
        "flags": [str],
        "summary": str
      }
    """

    # Step 1: Audio preprocessing
    try:
        processed_audio_path = preprocess_audio(audio_path)
        audio_quality = get_audio_metrics(processed_audio_path)
    except Exception as e:
        # If preprocessing fails, we cannot proceed
        return {
            "risk_score": None,
            "risk_level": "UNKNOWN",
            "transcript_quality": {
                "quality_score": 0.0,
                "quality_level": "VERY_LOW",
                "is_sufficient_for_scoring": False,
                "explanation": f"Audio preprocessing failed: {str(e)}",
                "recommendation": "REJECT"
            },
            "audio_quality": {"error": str(e)},
            "stt_backend": {"error": "Audio preprocessing failed"},
            "flags": ["audio_preprocessing_failed"],
            "summary": "Audio could not be processed for scam analysis."
        }

    # Step 2: Speech-to-text with improved configuration
    try:
        # Use faster-whisper with optimized configuration for speed
        # - tiny model for maximum speed (sufficient for scam keyword detection)
        # - beam_size=2 for balanced speed/accuracy
        # - VAD filter to skip silence
        # - int8 compute type for CPU efficiency
        model = os.environ.get("SCAM_SHIELD_STT_MODEL", "tiny").strip() or "tiny"
        max_secs_env = os.environ.get("SCAM_SHIELD_MAX_AUDIO_SECONDS", "30").strip()
        try:
            max_secs = float(max_secs_env) if max_secs_env else None
        except ValueError:
            max_secs = None
        if max_secs is not None and max_secs <= 0:
            max_secs = None

        # Language override / hinting:
        # - If SCAM_SHIELD_LANGUAGE is set (e.g. "hi"), force it.
        # - Otherwise, try to guess from filename script (Devanagari/Tamil/Telugu/Malayalam).
        forced_lang = _normalize_lang(os.environ.get("SCAM_SHIELD_LANGUAGE", "").strip() or None)
        filename_lang = _guess_language_from_filename(audio_path)
        lang_hint = forced_lang or filename_lang

        backend = (os.environ.get("SCAM_SHIELD_STT_BACKEND", "faster_whisper").strip() or "faster_whisper").lower()
        if backend not in ("faster_whisper", "whisper", "vosk"):
            backend = "faster_whisper"

        stt_cfg = TranscriberConfig(
            backend=backend,  # allows pip openai-whisper via backend="whisper"
            model=model,
            language=lang_hint,
            max_audio_seconds=max_secs,
            vad_filter=True,
            beam_size=2,
            best_of=2,
        )
        segments, stt_meta = transcribe_file_with_meta(processed_audio_path, config=stt_cfg)
        detected_lang = _normalize_lang(stt_meta.get("language"))

        # Step 3: Transcript quality assessment
        raw_text = " ".join((s.get("text") or "") for s in segments).strip()
        transcript_quality = assess_transcript_quality(raw_text, segments)
        
        # Step 4: Early rejection if transcript quality is insufficient
        if not transcript_quality["is_sufficient_for_scoring"]:
            # Clean up temporary files
            cleanup_processed_audio(processed_audio_path)
            
            return {
                "risk_score": None,
                "risk_level": "UNKNOWN",
                "transcript_quality": transcript_quality,
                "audio_quality": audio_quality,
                "stt_backend": {
                    "backend": stt_meta.get("backend"),
                    "model": model,
                    "language": stt_meta.get("language"),
                    "language_probability": stt_meta.get("language_probability")
                },
                "flags": ["transcript_quality_insufficient"],
                "summary": "Audio unclear or unintelligible; scam risk cannot be assessed"
            }
        
        # Step 5: Continue with scam scoring only if quality passes
        # Auto-fallback when output is clearly the wrong script (common: Hindi misread as zh -> Chinese chars).
        # Step 6: Language detection and fallback logic
        stats = _text_unicode_stats(raw_text)
        looks_cjk = float(stats.get("cjk", 0.0) or 0.0) >= 0.15
        if looks_cjk and forced_lang is None:
            best_q = _transcript_quality(raw_text, target_lang=detected_lang)
            best = (best_q, detected_lang, segments, stt_meta)
            for lang in ("hi", "ta", "ml", "te"):
                cfg2 = TranscriberConfig(
                    backend="faster_whisper",
                    model=model,
                    language=lang,
                    max_audio_seconds=max_secs,
                    vad_filter=True,
                    beam_size=2,
                    best_of=2,
                )
                seg2, meta2 = transcribe_file_with_meta(processed_audio_path, config=cfg2)
                txt2 = " ".join((s.get("text") or "") for s in seg2).strip()
                q = _transcript_quality(txt2, target_lang=lang)
                if q > best[0] + 5.0:
                    best = (q, lang, seg2, meta2)
            if best[2] is not segments:
                _q, best_lang, best_segs, best_meta = best
                segments, stt_meta = best_segs, best_meta
                detected_lang = best_lang
                raw_text = " ".join((s.get("text") or "") for s in segments).strip()
                # Re-assess quality with improved transcription
                transcript_quality = assess_transcript_quality(raw_text, segments)
                
                # Check quality again after language fallback
                if not transcript_quality["is_sufficient_for_scoring"]:
                    cleanup_processed_audio(processed_audio_path)
                    return {
                        "risk_score": None,
                        "risk_level": "UNKNOWN",
                        "transcript_quality": transcript_quality,
                        "audio_quality": audio_quality,
                        "stt_backend": {
                            "backend": stt_meta.get("backend"),
                            "model": model,
                            "language": stt_meta.get("language"),
                            "language_probability": stt_meta.get("language_probability")
                        },
                        "flags": ["transcript_quality_insufficient_after_fallback"],
                        "summary": "Audio unclear or unintelligible; scam risk cannot be assessed"
                    }

        # Step 7: Proceed with scam scoring
        supported_langs = {"hi", "ta", "ml", "te"}
        is_supported = bool(detected_lang in supported_langs) if detected_lang else False
        diarized = diarize_segments(segments)
        features = analyze_conversation(diarized)

        # Score by feeding diarized segments as chunks (stream order preserved).
        scorer = StreamingScorer(session_id="audio", detected_language=detected_lang)
        for s in diarized:
            text = (s.get("text") or "").strip()
            if text:
                scorer.ingest_chunk(text)

        final: FinalReport = scorer.finalize()

        # Start from streaming score, then apply conversation-level context
        # adjustments (caller dominance, multi-speaker reinforcement, etc.).
        score = float(final.risk_score)

        # Step 8: Enhanced scoring with advanced pattern detection
        advanced_scorer = SimpleAdvancedScorer()
        advanced_result = advanced_scorer.analyze_text(raw_text, detected_lang)
        
        # Combine scores (60% original, 40% advanced)
        combined_score = int(0.6 * score + 0.4 * advanced_result['risk_score'])
        
        # Determine final risk level
        if combined_score >= 85:
            final_risk_level = "CRITICAL"
        elif combined_score >= 70:
            final_risk_level = "HIGH"
        elif combined_score >= 40:
            final_risk_level = "MEDIUM"
        else:
            final_risk_level = "LOW"

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
        # Use combined score and risk level
        out_score = combined_score
        out_level = final_risk_level

        # Add enhanced flags from advanced analysis
        enhanced_flags = []
        if advanced_result['matches']:
            categories = set(m['category'] for m in advanced_result['matches'])
            for cat in categories:
                enhanced_flags.append(f"ADVANCED_{cat}")
        
        flags = sorted(
            set(
                final.signals
                + enhanced_flags
                + [
                    f"feature:{k}"
                    for k, v in features.items()
                    if k.endswith("_count") and isinstance(v, int) and v > 0
                ]
            )
        )
        
        # Enhanced summary with advanced insights
        base_summary = _build_summary(final, features)
        if advanced_result['confidence'] > 0.7:
            summary = f"{base_summary} | Enhanced: {advanced_result['risk_level']} confidence ({advanced_result['confidence']:.2f})"
        else:
            summary = base_summary

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

        # Step 8: Clean up temporary files
        cleanup_processed_audio(processed_audio_path)
        
        # Step 9: Build final response with updated contract
        return {
            "risk_score": out_score,  # Use combined score
            "risk_level": out_level,  # Use combined risk level
            "transcript_quality": transcript_quality,
            "audio_quality": audio_quality,
            "stt_backend": {
                "backend": stt_meta.get("backend"),
                "model": model,
                "language": stt_meta.get("language"),
                "language_probability": stt_meta.get("language_probability")
            },
            "flags": flags,
            "summary": summary,
            "language": {
                "detected": detected_lang,
                "detected_name": _LANG_NAMES.get(detected_lang or "", "Unknown") if detected_lang else None,
                "supported": is_supported,
                "confidence": stt_meta.get("language_probability"),
            },
            "transcript": {
                "segments": diarized,
                "speaker_summaries": speaker_text,
            },
            "details": {
                "features": features,
                "original_score": score,  # Original streaming score
                "advanced_analysis": {
                    "risk_score": advanced_result['risk_score'],
                    "risk_level": advanced_result['risk_level'],
                    "confidence": advanced_result['confidence'],
                    "matches": advanced_result['matches'],
                    "context_analysis": advanced_result['context_analysis']
                }
            },
        }
    except Exception as e:
        # If STT fails, we cannot proceed
        return {
            "risk_score": None,
            "risk_level": "UNKNOWN",
            "transcript_quality": {
                "quality_score": 0.0,
                "quality_level": "VERY_LOW",
                "is_sufficient_for_scoring": False,
                "explanation": f"STT failed: {str(e)}",
                "recommendation": "REJECT"
            },
            "audio_quality": audio_quality,
            "stt_backend": {"error": str(e)},
            "flags": ["stt_failed"],
            "summary": "Audio could not be transcribed for scam analysis."
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

