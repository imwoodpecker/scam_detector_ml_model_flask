"""
text_normalizer.py

Text normalization module for multi-language scam detection.
Handles Devanagari, Tamil, Telugu, Malayalam scripts and Romanized variants.
"""

from __future__ import annotations

import re
from typing import Dict, Set


def _normalize_common_asr_errors(text: str) -> str:
    """
    Fix common ASR transcription errors.
    """
    # Common ASR spacing errors
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single space
    text = re.sub(r'(\w)\s+(\d)', r'\1\2', text)  # Remove space between word and number
    text = re.sub(r'(\d)\s+(\w)', r'\1\2', text)  # Remove space between number and word
    
    # Common ASR character errors
    text = text.replace('o t p', 'otp')
    text = text.replace('o t p', 'otp')
    text = text.replace('o t p', 'otp')
    text = text.replace('u p i', 'upi')
    text = text.replace('k y c', 'kyc')
    
    # Fix common number-word separations
    text = re.sub(r'(\d+)\s+(digit|number)', r'\1\2', text, flags=re.IGNORECASE)
    text = re.sub(r'(pin|code)\s+(\d+)', r'\1\2', text, flags=re.IGNORECASE)
    
    return text.strip()


def _normalize_hinglish_variants(text: str) -> str:
    """
    Normalize common Hinglish (Romanized Hindi) variants.
    """
    # OTP variations
    otp_variants = {
        'otp bataye': 'otp bataye',
        'otp bataiye': 'otp bataiye', 
        'otp bhejo': 'otp bhejo',
        'otp bhejiye': 'otp bhejiye',
        'code bataye': 'code bataye',
        'verification code bataye': 'verification code bataye',
    }
    
    # Urgency variations
    urgency_variants = {
        'abhi': 'abhi',
        'abhi ke abhi': 'abhi ke abhi',
        'turant': 'turant',
        'jaldi': 'jaldi',
        'immediately': 'immediately',
    }
    
    # Account/security variations
    account_variants = {
        'account block': 'account block',
        'account band': 'account block',
        'kyc update': 'kyc update',
        'kyc update karna': 'kyc update karna',
        'kyc update kijiye': 'kyc update kijiye',
    }
    
    # Apply normalizations
    normalized = text.lower()
    for variant, standard in {**otp_variants, **urgency_variants, **account_variants}.items():
        normalized = normalized.replace(variant, standard)
    
    return normalized


def _normalize_tamil_variants(text: str) -> str:
    """
    Normalize common Tamil (Romanized) variants.
    """
    # OTP variations
    otp_variants = {
        'otp sollunga': 'otp sollunga',
        'otp sollu': 'otp sollu',
        'otp anuppu': 'otp anuppu',
        'code sollunga': 'code sollunga',
        'verification code sollunga': 'verification code sollunga',
    }
    
    # Urgency variations
    urgency_variants = {
        'udane': 'udane',
        'ippove': 'ippove',
        'seekiram': 'seekiram',
        'immediately': 'immediately',
    }
    
    # Account variations
    account_variants = {
        'unga account': 'unga account',
        'account block': 'account block',
        'account close': 'account block',
        'kyc update': 'kyc update',
        'kyc update pannunga': 'kyc update pannunga',
    }
    
    # Apply normalizations
    normalized = text.lower()
    for variant, standard in {**otp_variants, **urgency_variants, **account_variants}.items():
        normalized = normalized.replace(variant, standard)
    
    return normalized


def _normalize_telugu_variants(text: str) -> str:
    """
    Normalize common Telugu (Romanized) variants.
    """
    # OTP variations
    otp_variants = {
        'otp cheppandi': 'otp cheppandi',
        'otp cheppu': 'otp cheppu',
        'code cheppandi': 'code cheppandi',
        'verification code cheppandi': 'verification code cheppandi',
    }
    
    # Urgency variations
    urgency_variants = {
        'ventane': 'ventane',
        'ippude': 'ippude',
        'twaraga': 'twaraga',
        'immediately': 'immediately',
    }
    
    # Account variations
    account_variants = {
        'mee account': 'mee account',
        'account block': 'account block',
        'account close': 'account block',
        'kyc update': 'kyc update',
        'kyc update cheyandi': 'kyc update cheyandi',
    }
    
    # Apply normalizations
    normalized = text.lower()
    for variant, standard in {**otp_variants, **urgency_variants, **account_variants}.items():
        normalized = normalized.replace(variant, standard)
    
    return normalized


def _normalize_malayalam_variants(text: str) -> str:
    """
    Normalize common Malayalam (Romanized) variants.
    """
    # OTP variations
    otp_variants = {
        'otp parayu': 'otp parayu',
        'otp parayuka': 'otp parayuka',
        'code parayu': 'code parayu',
        'verification code parayu': 'verification code parayu',
    }
    
    # Urgency variations
    urgency_variants = {
        'udane': 'udane',
        'ippo': 'ippo',
        'pettannu': 'pettannu',
        'immediately': 'immediately',
    }
    
    # Account variations
    account_variants = {
        'ningalude account': 'ningalude account',
        'account block': 'account block',
        'kyc update': 'kyc update',
        'kyc update cheyyanam': 'kyc update cheyyanam',
    }
    
    # Apply normalizations
    normalized = text.lower()
    for variant, standard in {**otp_variants, **urgency_variants, **account_variants}.items():
        normalized = normalized.replace(variant, standard)
    
    return normalized


def _detect_script_family(text: str) -> str:
    """
    Detect the primary script family in the text.
    Returns: 'devanagari', 'tamil', 'telugu', 'malayalam', 'latin', or 'mixed'
    """
    devanagari_count = sum(1 for c in text if 0x0900 <= ord(c) <= 0x097F)
    tamil_count = sum(1 for c in text if 0x0B80 <= ord(c) <= 0x0BFF)
    telugu_count = sum(1 for c in text if 0x0C00 <= ord(c) <= 0x0C7F)
    malayalam_count = sum(1 for c in text if 0x0D00 <= ord(c) <= 0x0D7F)
    latin_count = sum(1 for c in text if (0x0041 <= ord(c) <= 0x005A) or (0x0061 <= ord(c) <= 0x007A))
    
    counts = {
        'devanagari': devanagari_count,
        'tamil': tamil_count,
        'telugu': telugu_count,
        'malayalam': malayalam_count,
        'latin': latin_count
    }
    
    max_count = max(counts.values())
    if max_count == 0:
        return 'unknown'
    
    # Check if it's predominantly one script or mixed
    dominant_scripts = [script for script, count in counts.items() if count >= max_count * 0.3]
    
    if len(dominant_scripts) == 1:
        return dominant_scripts[0]
    else:
        return 'mixed'


def normalize_text_for_scoring(text: str, detected_language: str | None = None) -> str:
    """
    Normalize text for scam scoring across multiple languages and scripts.
    
    Args:
        text: Input transcript text
        detected_language: Optional detected language code ('hi', 'ta', 'te', 'ml')
        
    Returns:
        Normalized text suitable for scam scoring
    """
    if not text:
        return ""
    
    # Step 1: Basic cleanup
    normalized = text.strip()
    normalized = _normalize_common_asr_errors(normalized)
    
    # Step 2: Convert to lowercase for consistent matching
    normalized = normalized.lower()
    
    # Step 3: Detect script family
    script_family = _detect_script_family(text)
    
    # Step 4: Apply language-specific normalizations
    if detected_language == 'hi' or script_family == 'devanagari':
        normalized = _normalize_hinglish_variants(normalized)
    elif detected_language == 'ta' or script_family == 'tamil':
        normalized = _normalize_tamil_variants(normalized)
    elif detected_language == 'te' or script_family == 'telugu':
        normalized = _normalize_telugu_variants(normalized)
    elif detected_language == 'ml' or script_family == 'malayalam':
        normalized = _normalize_malayalam_variants(normalized)
    elif script_family == 'latin' or script_family == 'mixed':
        # For Romanized text, try all normalizations
        normalized = _normalize_hinglish_variants(normalized)
        normalized = _normalize_tamil_variants(normalized)
        normalized = _normalize_telugu_variants(normalized)
        normalized = _normalize_malayalam_variants(normalized)
    
    # Step 5: Final cleanup
    normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
    normalized = normalized.strip()
    
    return normalized


def create_multilingual_keyword_map() -> Dict[str, Set[str]]:
    """
    Create a mapping of normalized keywords to their variants across languages.
    This helps the scam scorer recognize concepts regardless of script or language.
    """
    keyword_map = {
        'otp': {
            'otp', 'o t p', 'one time password', 'verification code', 'security code',
            'ओटीपी', 'ஓடிபி', 'ఓటిపి', 'ഓടിപി',
            'otp bataye', 'otp bataiye', 'otp bhejo', 'otp bhejiye',
            'otp sollunga', 'otp sollu', 'otp anuppu',
            'otp cheppandi', 'otp cheppu',
            'otp parayu', 'otp parayuka',
            'code bataye', 'code sollunga', 'code cheppandi', 'code parayu'
        },
        'upi': {
            'upi', 'upi pin', 'upi id', 'यूपीआई', 'யூபிஐ', 'యూపీఐ', 'യുപിഐ',
            'upi pin', 'यूपीआई पिन', 'யூபிஐ பின்', 'యూపీఐ పిన్', 'യുപിഐ പിൻ'
        },
        'kyc': {
            'kyc', 'kyc update', 'know your customer', 'केवाईसी', 'केवाईसी अपडेट',
            'கேவைசி', 'கேவைசி அப்டேட்', 'కేవైసీ', 'కేవైసీ అప్డేట్',
            'കെവൈസി', 'കെവൈസി അപ്ഡേറ്റ്'
        },
        'account_block': {
            'account block', 'account band', 'account close', 'account suspended',
            'अकाउंट ब्लॉक', 'खाता बंद', 'அக்கவுண்ட் ப்ளாக்', 'அக்கவுண்ட் க்ளோஸ்',
            'అకౌంట్ బ్లాక్', 'అకౌంట్ క్లోజ్', 'അക്കൗണ്ട് ബ്ലോക്ക്'
        },
        'urgent': {
            'urgent', 'immediately', 'asap', 'right now', 'अभी', 'तुरंत', 'जल्दी',
            'உடனே', 'இப்போவே', 'சீக்கிரம்', 'వెంటనే', 'ఇప్పుడే', 'త్వరగా',
            'ഉടനെ', 'ഇപ്പോൾ', 'പെട്ടന്ന്'
        },
        'secrecy': {
            'do not tell anyone', 'keep secret', 'confidential', 'किसी को मत बताना',
            'யாருக்கும் சொல்லாதே', 'யாருக்கும் சொல்லாதே', 'ఎవ్వరికీ చెప్పకండి',
            'ആരോടും പറയരുത്'
        },
        'bank': {
            'bank', 'bank officer', 'bank manager', 'बैंक', 'बैंक अधिकारी',
            'வங்கி', 'வங்கி அதிகாரி', 'బ్యాంకు', 'బ్యాంక్ ఆఫీసర్',
            'ബാങ്ക്', 'ബാങ്ക് ഓഫീസർ'
        },
        'card': {
            'card', 'credit card', 'debit card', 'atm card', 'कार्ड', 'क्रेडिट कार्ड',
            'கார்டு', 'கிரெடிட் கார்டு', 'కార్డు', 'క్రెడిట్ కార్డ్',
            'കാർഡ്', 'ക്രെഡിറ്റ് കാർഡ്'
        },
        'pin': {
            'pin', 'pin number', 'पिन', 'पिन नंबर', 'பின்', 'பின் நம்பர்',
            'పిన్', 'పిన్ నంబర్', 'പിൻ', 'പിൻ നമ്പർ'
        },
        'cvv': {
            'cvv', 'cvv number', 'सीवीवी', 'सीवीवी नंबर', 'சிவிவி', 'சிவிவி நம்பர்',
            'సివివి', 'సివివి నంబర్', 'സിവിവി', 'സിവിവി നമ്പർ'
        }
    }
    
    return keyword_map


def expand_keywords_with_variants(keywords: Set[str]) -> Set[str]:
    """
    Expand a set of keywords with their multilingual variants.
    """
    keyword_map = create_multilingual_keyword_map()
    expanded = set(keywords)
    
    for keyword in keywords:
        # Check if this keyword matches any of our standard concepts
        for concept, variants in keyword_map.items():
            if keyword.lower() in variants:
                expanded.update(variants)
                break
    
    return expanded
