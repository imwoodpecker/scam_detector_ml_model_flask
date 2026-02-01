"""
transcript_quality.py

Transcript quality assessment module for scam detection pipeline.
Implements heuristics to detect low-quality or unintelligible transcripts.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


def _count_tokens(text: str) -> int:
    """
    Count meaningful tokens in text.
    Handles multiple scripts and tokenization.
    """
    if not text:
        return 0
    
    # Split on whitespace and filter empty strings
    tokens = [t.strip() for t in text.split() if t.strip()]
    return len(tokens)


def _calculate_short_token_ratio(text: str) -> float:
    """
    Calculate ratio of very short tokens (<= 2 chars).
    High ratio may indicate fragmented speech or poor transcription.
    """
    tokens = text.split()
    if not tokens:
        return 0.0
    
    short_tokens = [t for t in tokens if len(t.strip()) <= 2]
    return len(short_tokens) / len(tokens)


def _has_meaningful_content(text: str) -> bool:
    """
    Check if text contains meaningful content indicators.
    Looks for numerals, verbs, and substantive words.
    """
    if not text:
        return False
    
    text_lower = text.lower()
    
    # Check for numerals (common in scam calls)
    has_numerals = bool(re.search(r'\d', text))
    
    # Common verb indicators (multiple languages)
    verb_patterns = [
        r'\b(otp|code|pin|password|account|card|bank|pay|send|share|tell|give|call|message)\b',
        # Hindi verbs
        r'\b(bata[ie]|bhej[ie]|kar[oe]|di[ie]|bol[oe]|khabar|batana|bhejna)\b',
        # Tamil verbs  
        r'\b(sollu|anuppu|pannu|sol|kodu|tharu|pesu)\b',
        # Telugu verbs
        r'\b(cheppandi|cheppu|iyandi|pettandi|kundandi)\b',
        # Malayalam verbs
        r'\b(parayu|cheyyu|kodu|tharu)\b',
    ]
    
    has_verbs = any(re.search(pattern, text_lower) for pattern in verb_patterns)
    
    # Check for common scam-related keywords
    scam_keywords = [
        'otp', 'pin', 'code', 'account', 'card', 'bank', 'pay', 'upi', 'kyc',
        'urgent', 'immediately', 'block', 'suspend', 'verify', 'confirm'
    ]
    
    has_keywords = any(keyword in text_lower for keyword in scam_keywords)
    
    return has_numerals or has_verbs or has_keywords


def _detect_repetition(text: str) -> float:
    """
    Detect repetitive patterns that may indicate poor transcription.
    Returns repetition score (0.0 = no repetition, 1.0 = high repetition).
    """
    if not text:
        return 0.0
    
    words = text.lower().split()
    if len(words) < 4:
        return 0.0
    
    # Count repeated consecutive words
    consecutive_repeats = 0
    for i in range(1, len(words)):
        if words[i] == words[i-1]:
            consecutive_repeats += 1
    
    # Count repeated words overall
    word_counts = {}
    for word in words:
        word_counts[word] = word_counts.get(word, 0) + 1
    
    # Calculate repetition metrics
    consecutive_ratio = consecutive_repeats / len(words)
    max_repeat_count = max(word_counts.values()) if word_counts else 1
    overall_repeat_ratio = (max_repeat_count - 1) / len(words)
    
    # Combine metrics
    repetition_score = max(consecutive_ratio, overall_repeat_ratio)
    return min(repetition_score * 2, 1.0)  # Scale and cap at 1.0


def _detect_gibberish(text: str) -> float:
    """
    Detect gibberish or nonsensical text.
    Returns gibberish score (0.0 = meaningful, 1.0 = gibberish).
    """
    if not text:
        return 1.0
    
    # Remove non-alphabetic characters for analysis
    clean_text = re.sub(r'[^a-zA-Z\u0900-\u097F\u0B80-\u0BFF\u0C00-\u0C7F\u0D00-\u0D7F]', ' ', text)
    words = clean_text.split()
    
    if not words:
        return 1.0
    
    # Check for very short average word length
    avg_word_length = sum(len(word) for word in words) / len(words)
    short_word_penalty = max(0, (3.0 - avg_word_length) / 3.0)
    
    # Check for high consonant-to-vowel ratio (indicator of gibberish)
    def cv_ratio(word: str) -> float:
        vowels = set('aeiouAEIOU')
        consonant_count = sum(1 for c in word if c.isalpha() and c not in vowels)
        vowel_count = sum(1 for c in word if c.isalpha() and c in vowels)
        return consonant_count / max(vowel_count, 1)
    
    avg_cv_ratio = sum(cv_ratio(word) for word in words) / len(words)
    cv_penalty = max(0, (avg_cv_ratio - 3.0) / 3.0)
    
    # Check for character repetition within words
    char_repeat_penalty = 0
    for word in words:
        if len(word) >= 3:
            repeats = sum(1 for i in range(2, len(word)) if word[i] == word[i-1] == word[i-2])
            char_repeat_penalty += repeats / len(words)
    
    gibberish_score = min(short_word_penalty + cv_penalty + char_repeat_penalty, 1.0)
    return gibberish_score


def _assess_language_consistency(text: str, detected_lang: str | None) -> float:
    """
    Assess if the detected language matches the actual script content.
    Returns consistency score (0.0 = inconsistent, 1.0 = consistent).
    """
    if not text or not detected_lang:
        return 0.5  # Neutral score when can't assess
    
    # Unicode script detection
    devanagari_count = sum(1 for c in text if 0x0900 <= ord(c) <= 0x097F)
    tamil_count = sum(1 for c in text if 0x0B80 <= ord(c) <= 0x0BFF)
    telugu_count = sum(1 for c in text if 0x0C00 <= ord(c) <= 0x0C7F)
    malayalam_count = sum(1 for c in text if 0x0D00 <= ord(c) <= 0x0D7F)
    latin_count = sum(1 for c in text if (0x0041 <= ord(c) <= 0x005A) or (0x0061 <= ord(c) <= 0x007A))
    
    total_chars = devanagari_count + tamil_count + telugu_count + malayalam_count + latin_count
    if total_chars == 0:
        return 0.5
    
    # Calculate script percentages
    script_percentages = {
        'hi': devanagari_count / total_chars,
        'ta': tamil_count / total_chars,
        'te': telugu_count / total_chars,
        'ml': malayalam_count / total_chars,
        'latin': latin_count / total_chars
    }
    
    # Check consistency
    if detected_lang == 'hi' and script_percentages['hi'] > 0.3:
        return 0.8 + script_percentages['hi'] * 0.2
    elif detected_lang == 'ta' and script_percentages['ta'] > 0.3:
        return 0.8 + script_percentages['ta'] * 0.2
    elif detected_lang == 'te' and script_percentages['te'] > 0.3:
        return 0.8 + script_percentages['te'] * 0.2
    elif detected_lang == 'ml' and script_percentages['ml'] > 0.3:
        return 0.8 + script_percentages['ml'] * 0.2
    elif script_percentages['latin'] > 0.7:  # Romanized text
        return 0.7
    
    # Inconsistent language detection
    return 0.3


def assess_transcript_quality(text: str, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Assess transcript quality using multiple heuristics.
    
    Args:
        text: Full transcript text
        segments: List of transcription segments with timestamps
        
    Returns:
        Dictionary with quality assessment results
    """
    # Basic metrics
    token_count = _count_tokens(text)
    short_token_ratio = _calculate_short_token_ratio(text)
    has_meaningful = _has_meaningful_content(text)
    repetition_score = _detect_repetition(text)
    gibberish_score = _detect_gibberish(text)
    
    # Segment-based metrics
    segment_count = len(segments)
    avg_segment_duration = 0.0
    if segment_count > 0:
        durations = [seg.get('end', 0) - seg.get('start', 0) for seg in segments]
        avg_segment_duration = sum(durations) / len(durations)
    
    # Calculate overall quality score (0.0 = poor, 1.0 = excellent)
    quality_score = 1.0
    
    # Penalize short transcripts
    if token_count < 5:
        quality_score -= 0.5
    elif token_count < 10:
        quality_score -= 0.3
    elif token_count < 20:
        quality_score -= 0.1
    
    # Penalize high short token ratio
    if short_token_ratio > 0.7:
        quality_score -= 0.3
    elif short_token_ratio > 0.5:
        quality_score -= 0.1
    
    # Penalize lack of meaningful content
    if not has_meaningful:
        quality_score -= 0.4
    
    # Penalize repetition
    quality_score -= repetition_score * 0.3
    
    # Penalize gibberish
    quality_score -= gibberish_score * 0.5
    
    # Penalize very short average segment duration (may indicate fragmented speech)
    if avg_segment_duration > 0 and avg_segment_duration < 1.0:
        quality_score -= 0.2
    
    # Ensure score is within bounds
    quality_score = max(0.0, min(1.0, quality_score))
    
    # Determine quality level
    if quality_score >= 0.8:
        quality_level = "HIGH"
    elif quality_score >= 0.6:
        quality_level = "MEDIUM"
    elif quality_score >= 0.4:
        quality_level = "LOW"
    else:
        quality_level = "VERY_LOW"
    
    # Generate explanation
    explanations = []
    if token_count < 10:
        explanations.append("Very short transcript")
    if short_token_ratio > 0.6:
        explanations.append("High ratio of short tokens")
    if not has_meaningful:
        explanations.append("Lacks meaningful content (no verbs, numbers, or keywords)")
    if repetition_score > 0.3:
        explanations.append("Significant repetition detected")
    if gibberish_score > 0.3:
        explanations.append("Potential gibberish or fragmented speech")
    if avg_segment_duration > 0 and avg_segment_duration < 1.0:
        explanations.append("Very short speech segments")
    
    if not explanations:
        explanations.append("Transcript appears coherent")
    
    # Determine if quality is sufficient for scam scoring
    is_sufficient = quality_score >= 0.5 and has_meaningful and token_count >= 8
    
    return {
        "quality_score": float(quality_score),
        "quality_level": quality_level,
        "is_sufficient_for_scoring": is_sufficient,
        "explanation": "; ".join(explanations),
        "metrics": {
            "token_count": token_count,
            "segment_count": segment_count,
            "avg_segment_duration": float(avg_segment_duration),
            "short_token_ratio": float(short_token_ratio),
            "has_meaningful_content": has_meaningful,
            "repetition_score": float(repetition_score),
            "gibberish_score": float(gibberish_score),
        },
        "recommendation": "PROCEED" if is_sufficient else "REJECT"
    }
