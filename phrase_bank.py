"""
phrase_bank.py

Lightweight "data" module containing known scam phrases/patterns.
You can expand these lists over time.
"""

from __future__ import annotations

# Optional external dataset loader:
# If `./data/keyword_phrase_dataset.json` exists, we merge it into the in-code banks.
import json
import os

# High-signal phrases commonly used in scams (email/SMS/DM).
SCAM_PHRASES: list[str] = [
    "verify your account",
    "your account will be suspended",
    "unusual activity",
    "confirm your identity",
    "reset your password",
    "limited time offer",
    "act now",
    "urgent",
    "click the link",
    "login to continue",
    "payment failed",
    "invoice attached",
    "you have won",
    "congratulations you won",
    "claim your prize",
    "free gift",
    "wire transfer",
    "gift card",
    "send bitcoin",
    "crypto wallet",
    "bank details",
    "otp",
    "one time password",
    "share the code",
    "do not share this code",  # used in impersonation contexts
    "remote access",
    "teamviewer",
    "anydesk",
    "refund",
    "tech support",
    "your subscription",
    # Known phone scam script fragments (partial matches allowed)
    "due to increase in computer related fraud",
    "card holders are held responsible",
    "we underwrite all fraud charges",
    "you will receive a package",
    # Off-platform / isolation
    "move to whatsapp",
    "move to telegram",
    "continue on whatsapp",
    "continue on telegram",
    "message me on whatsapp",
    "message me on telegram",
    # Secrecy / manipulation
    "keep this confidential",
    "do not tell anyone",
    "don't tell anyone",
    "keep it secret",
    "between you and me",
    # Impersonation / authority / fear
    "police case",
    "legal action",
    "court notice",
    "income tax",
    "customs",
    "bank officer",
    "customer support",
    "security team",
    "kyc update",
    "update your kyc",

    # --- Hindi / Hinglish (common India scam call patterns) ---
    "otp bataye",
    "otp bataiye",
    "otp bhejo",
    "otp bhejiye",
    "code bataye",
    "verification code bataye",
    "aapko otp aaya hoga",
    "aapke phone par otp aaya hoga",
    "kisi ko mat batana",
    "kisi ko mat batao",
    "kisi ko nahi batana",
    "sirf mujhe bataye",
    "abhi ke abhi",
    "turant",
    "jaldi",
    "abhi",
    "aapka account block ho jayega",
    "aapka account band ho jayega",
    "kyc update karna hai",
    "kyc update kijiye",
    "aapka kyc pending hai",
    "upi",
    "upi pin",
    "pin bataye",
    "card number bataye",
    "cvv bataye",
    "expiry date bataye",
    "bank se bol raha hoon",
    "bank se baat kar raha hoon",
    "customer care se bol raha hoon",
    "cyber crime",
    "police complaint",
    "fir darj",
    "legal notice",

    # Devanagari (Hindi)
    "ओटीपी बताइए",
    "ओटीपी बताओ",
    "ओटीपी भेजो",
    "कोड बताइए",
    "किसी को मत बताना",
    "तुरंत",
    "जल्दी",
    "अभी",
    "आपका अकाउंट ब्लॉक हो जाएगा",
    "आपका खाता बंद हो जाएगा",
    "केवाईसी अपडेट",
    "यूपीआई",
    "यूपीआई पिन",
    "पिन बताइए",
    "कार्ड नंबर बताइए",
    "सीवीवी बताइए",
    "एक्सपायरी डेट",
    "बैंक से बोल रहा हूँ",
    "कस्टमर केयर",
    "साइबर क्राइम",
    "पुलिस",
    "कानूनी कार्रवाई",

    # --- Tamil (India scam call patterns) ---
    "otp sollunga",
    "otp sollu",
    "otp anuppu",
    "code sollunga",
    "verification code sollunga",
    "yaarukkum sollaadhe",
    "yaarukkum solla vendam",
    "udane",
    "ippove",
    "seekiram",
    "unga account block aagum",
    "unga account close aagum",
    "kyc update pannunga",
    "upi",
    "upi pin",
    "pin sollunga",
    "card number sollunga",
    "cvv sollunga",
    "bank la irundhu pesuren",
    "customer care",

    # தமிழ்
    "ஓடிபி சொல்லுங்க",
    "கோடு சொல்லுங்க",
    "யாருக்கும் சொல்லாதே",
    "உடனே",
    "இப்போவே",
    "சீக்கிரம்",
    "உங்க அக்கவுண்ட் ப்ளாக் ஆகும்",
    "கேவைசி அப்டேட்",
    "யூபிஐ",
    "யூபிஐ பின்",
    "பின் சொல்லுங்க",
    "கார்டு நம்பர் சொல்லுங்க",
    "சிவிவி சொல்லுங்க",

    # --- Malayalam ---
    "otp parayu",
    "otp parayuka",
    "code parayu",
    "verification code parayu",
    "aarodum parayaruthu",
    "udane",
    "ippo",
    "pettannu",
    "ningalude account block aakum",
    "kyc update cheyyanam",
    "upi",
    "upi pin",
    "pin parayu",
    "card number parayu",
    "cvv parayu",
    "bankil ninnanu vilikkunnathu",
    "customer care",

    # മലയാളം
    "ഓടിപി പറയൂ",
    "കോഡ് പറയൂ",
    "ആരോടും പറയരുത്",
    "ഉടനെ",
    "ഇപ്പോൾ",
    "നിങ്ങളുടെ അക്കൗണ്ട് ബ്ലോക്ക് ആക്കും",
    "കെവൈസി അപ്ഡേറ്റ്",
    "യുപിഐ",
    "യുപിഐ പിൻ",
    "പിൻ പറയൂ",

    # --- Telugu ---
    "otp cheppandi",
    "otp cheppu",
    "code cheppandi",
    "verification code cheppandi",
    "evvariki cheppakandi",
    "ventane",
    "ippude",
    "twaraga",
    "mee account block avutundi",
    "mee account close avutundi",
    "kyc update cheyandi",
    "upi",
    "upi pin",
    "pin cheppandi",
    "card number cheppandi",
    "cvv cheppandi",
    "bank nundi matladutunnanu",
    "customer care",

    # తెలుగు
    "ఓటిపి చెప్పండి",
    "కోడ్ చెప్పండి",
    "ఎవ్వరికీ చెప్పకండి",
    "వెంటనే",
    "ఇప్పుడే",
    "త్వరగా",
    "మీ అకౌంట్ బ్లాక్ అవుతుంది",
    "కేవైసీ అప్డేట్",
    "యూపీఐ",
    "యూపీఐ పిన్",
    "పిన్ చెప్పండి",
]


# Extra patterns that are not exact phrases but are useful "signals"
# handled by scorer.py (kept here to centralize the "data knobs").
SUSPICIOUS_KEYWORDS: list[str] = [
    "urgent",
    "immediately",
    "asap",
    "final notice",
    "suspended",
    "locked",
    "verify",
    "confirm",
    "password",
    "otp",
    "code",
    "gift card",
    "bitcoin",
    "crypto",
    "wallet",
    "wire",
    "transfer",
    "whatsapp",
    "telegram",
    "confidential",
    "secret",
    "police",
    "legal",
    "court",
    "kyc",
    "customs",
    "support",

    # Hindi/Tamil/Malayalam/Telugu (plus common romanized forms)
    "upi",
    "upi pin",
    "pin",
    "kyc",
    "kyc update",
    "block",
    "account",
    "turant",
    "jaldi",
    "abhi",
    "udane",
    "ippove",
    "seekiram",
    "ventane",
    "ippude",
    "twaraga",
    "evvariki",
    "aarodum",
    "yaarukkum",
    "kisi ko",
]


# Rule-oriented phrase groups (used by scorer.py for explainable rule hits).
RULE_PHRASES: dict[str, list[str]] = {
    "PRESSURE_URGENCY": [
        "urgent",
        "immediately",
        "act now",
        "asap",
        "final notice",
        "last chance",
        "limited time",

        # Hindi/Hinglish
        "abhi",
        "abhi ke abhi",
        "turant",
        "jaldi",
        "abhi turant",
        "immediately",  # keep

        # Tamil (romanized + Tamil)
        "udane",
        "ippove",
        "seekiram",
        "உடனே",
        "இப்போவே",
        "சீக்கிரம்",

        # Malayalam (romanized + Malayalam)
        "udane",
        "ippo",
        "pettannu",
        "ഉടനെ",
        "ഇപ്പോൾ",

        # Telugu (romanized + Telugu)
        "ventane",
        "ippude",
        "twaraga",
        "వెంటనే",
        "ఇప్పుడే",
        "త్వరగా",
    ],
    # OTP / authentication credentials (semantic equivalents)
    "CREDENTIAL_OTP": [
        "otp",
        "one time password",
        "verification code",
        "security code",
        "new code",
        "share the code",
        "send the code",
        "password",
        "pin",

        # Hindi/Hinglish + Devanagari
        "otp bataye",
        "otp bataiye",
        "code bataye",
        "ओटीपी बताइए",
        "कोड बताइए",
        "यूपीआई पिन",
        "upi pin",

        # Tamil
        "otp sollunga",
        "code sollunga",
        "ஓடிபி சொல்லுங்க",
        "கோடு சொல்லுங்க",
        "யூபிஐ பின்",

        # Malayalam
        "otp parayu",
        "code parayu",
        "ഓടിപി പറയൂ",
        "കോഡ് പറയൂ",
        "യുപിഐ പിൻ",

        # Telugu
        "otp cheppandi",
        "code cheppandi",
        "ఓటిపి చెప్పండి",
        "కోడ్ చెప్పండి",
        "యూపీఐ పిన్",
    ],
    # Broader credential harvesting asks (card/account numbers etc.)
    "CREDENTIAL_HARVESTING": [
        "confirm your card",
        "which card are you using",
        "write down account numbers",
        "card number",
        "account number",
        "debit card number",
        "credit card number",
        "expiry date",
        "cvv",

        # Hindi/Hinglish + Devanagari
        "card number bataye",
        "cvv bataye",
        "expiry date bataye",
        "कार्ड नंबर बताइए",
        "सीवीवी बताइए",
        "एक्सपायरी डेट",

        # Tamil
        "card number sollunga",
        "cvv sollunga",
        "கார்டு நம்பர் சொல்லுங்க",
        "சிவிவி சொல்லுங்க",

        # Malayalam
        "card number parayu",
        "cvv parayu",

        # Telugu
        "card number cheppandi",
        "cvv cheppandi",
    ],
    "PAYMENT_METHOD_RISK": [
        "gift card",
        "wire transfer",
        "bank transfer",
        "send bitcoin",
        "crypto wallet",
        "usdt",

        # India-specific
        "upi",
        "upi pin",
        "upi id",
        "scan qr",
        "qr code",
    ],
    "OFF_PLATFORM": [
        "whatsapp",
        "telegram",
        "dm me",
        "message me",
    ],
    "SECRECY": [
        "keep this confidential",
        "do not tell anyone",
        "don't tell anyone",
        "keep it secret",
        "between you and me",

        # Hindi/Hinglish + Devanagari
        "kisi ko mat batana",
        "kisi ko mat batao",
        "sirf mujhe bataye",
        "किसी को मत बताना",

        # Tamil
        "yaarukkum sollaadhe",
        "யாருக்கும் சொல்லாதே",

        # Malayalam
        "aarodum parayaruthu",
        "ആരോടും പറയരുത്",

        # Telugu
        "evvariki cheppakandi",
        "ఎవ్వరికీ చెప్పకండి",
    ],
    # Authority / fraud-department impersonation and framing
    "AUTHORITY_IMPERSONATION": [
        "bank officer",
        "security team",
        "customer support",
        "police",
        "income tax",
        "customs",
        "court",
        "legal action",
        "fraud division",
        "fraud watch",
        "visa department",
        "mastercard department",
        "visa mastercard department",
        "security department",
        "fraud department",

        # India-specific
        "customer care",
        "customer care se",
        "bank se",
        "cyber crime",
        "cybercrime",
        "upi",
        "police station",
        "fir",

        # Hindi/Devanagari
        "कस्टमर केयर",
        "बैंक",
        "साइबर क्राइम",
        "पुलिस",

        # Tamil
        "customer care",
        "bank la irundhu",
        "கஸ்டமர் கேர்",

        # Malayalam
        "bankil ninnanu",

        # Telugu
        "bank nundi",
    ],
    # Escalation gradients (normal -> warning -> threat)
    "ESCALATION_WARNING": [
        "warning",
        "final warning",
        "last warning",
        "account will be suspended",
        "account may be blocked",
        "account will be blocked",
        "kyc update",
        "update your kyc",
        "unusual activity",

        # Hindi/Hinglish + Devanagari
        "account block ho jayega",
        "account band ho jayega",
        "आपका अकाउंट ब्लॉक हो जाएगा",
        "आपका खाता बंद हो जाएगा",

        # Tamil
        "unga account block aagum",
        "உங்க அக்கவுண்ட் ப்ளாக் ஆகும்",

        # Malayalam
        "ningalude account block aakum",
        "നിങ്ങളുടെ അക്കൗണ്ട് ബ്ലോക്ക് ആക്കും",

        # Telugu
        "mee account block avutundi",
        "మీ అకౌంట్ బ్లాక్ అవుతుంది",
    ],
    "ESCALATION_THREAT": [
        "legal action",
        "police case",
        "court notice",
        "warrant",
        "arrest",
        "freeze your account",
        "you will be arrested",

        # Hindi/Devanagari
        "legal notice",
        "कानूनी कार्रवाई",

        # India common
        "cyber crime",
        "police complaint",
    ],
    # Benign/suppression cues (reduce score if no scam asks present)
    "BENIGN_IDENTITY": [
        "my name is",
        "this is",
        "i am",
        "speaking from",
    ],
    "BENIGN_REFERENCE": [
        "reference number",
        "ref number",
        "ticket number",
        "complaint number",
        "case id",
    ],
    "BENIGN_CALLBACK": [
        "call back",
        "callback",
        "you can call us",
        "our official number",
        "helpline",
    ],
    # Explicit "please do X" style asks used to detect requests for action.
    "ACTION_REQUEST": [
        "confirm your card",
        "confirm your account",
        "confirm these charges",
        "verify this transaction",
        "read me the code",
        "tell me the code",
        "share the code",
        "provide the code",
        "write down account numbers",
        "select option one",
        "press one to",
        "press 1 to",
        "stay on the line",
    ],
    # Financial account discussion (used to disable suppression when money/credentials are in play).
    "FINANCIAL_ACCOUNT": [
        "card number",
        "account number",
        "bank account",
        "checking account",
        "savings account",
        "current account",
        "routing number",
        "iban",
    ],
    # Known scam phone script fragments for explicit pattern hits.
    "KNOWN_SCAM_SCRIPT": [
        "due to increase in computer related fraud",
        "card holders are held responsible",
        "we underwrite all fraud charges",
        "you will receive a package",

        # Hindi/Hinglish fragments (common scam narration)
        "aapke naam par",
        "aapke aadhaar se",
        "aapke pan se",
        "aapke account se",
        "fraud transaction",
        "galat transaction",
    ],
}


def _merge_external_dataset() -> None:
    """
    Best-effort merge of external dataset file:
      ./data/keyword_phrase_dataset.json

    This lets you add lots of keywords/phrases without editing Python.
    """

    here = os.path.dirname(__file__)
    path = os.path.join(here, "data", "keyword_phrase_dataset.json")
    if not os.path.isfile(path):
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f) or {}
    except Exception:
        # Never break the pipeline if the dataset file is malformed/locked.
        return

    def _as_str_list(v: object) -> list[str]:
        if not isinstance(v, list):
            return []
        out: list[str] = []
        for x in v:
            if isinstance(x, str):
                s = x.strip()
                if s:
                    out.append(s)
        return out

    # Merge simple lists
    SCAM_PHRASES.extend(_as_str_list(obj.get("scam_phrases")))
    SUSPICIOUS_KEYWORDS.extend(_as_str_list(obj.get("suspicious_keywords")))

    # Merge rule phrases by rule_id
    rp = obj.get("rule_phrases")
    if isinstance(rp, dict):
        for rule_id, phrases in rp.items():
            if not isinstance(rule_id, str) or not rule_id.strip():
                continue
            RULE_PHRASES.setdefault(rule_id.strip(), []).extend(_as_str_list(phrases))

    # De-dup deterministically (preserve stable ordering)
    def _dedup(xs: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in xs:
            k = x.lower()
            if k in seen:
                continue
            seen.add(k)
            out.append(x)
        return out

    SCAM_PHRASES[:] = _dedup(SCAM_PHRASES)
    SUSPICIOUS_KEYWORDS[:] = _dedup(SUSPICIOUS_KEYWORDS)
    for k in list(RULE_PHRASES.keys()):
        RULE_PHRASES[k] = _dedup(RULE_PHRASES[k])


# Merge on import so analyzer/scorer see both sources.
_merge_external_dataset()

