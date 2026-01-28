"""
phrase_bank.py

Lightweight "data" module containing known scam phrases/patterns.
You can expand these lists over time.
"""

from __future__ import annotations

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
    ],
    "PAYMENT_METHOD_RISK": [
        "gift card",
        "wire transfer",
        "bank transfer",
        "send bitcoin",
        "crypto wallet",
        "usdt",
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
    ],
    "ESCALATION_THREAT": [
        "legal action",
        "police case",
        "court notice",
        "warrant",
        "arrest",
        "freeze your account",
        "you will be arrested",
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
    ],
}

