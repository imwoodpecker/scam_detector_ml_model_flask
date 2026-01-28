import sys

PHRASES = {
    "verify your account": 15,
    "urgent": 10,
    "do not disconnect": 15,
    "account may be blocked": 20,
    "click the link": 15,
    "otp": 25,
    "legal action": 20,
}

AUTHORITY = ["bank", "police", "rbi", "officer"]
URGENCY = ["urgent", "immediately", "now"]

score = 0
matched_phrases = set()
signals = set()
timeline = []

def contains_url(text):
    return "http://" in text or "https://" in text or "www." in text

# Read streaming input
conversation = sys.stdin.read().lower().splitlines()

for line in conversation:
    # Phrase matching
    for phrase, weight in PHRASES.items():
        if phrase in line:
            score += weight
            matched_phrases.add(phrase)
            timeline.append(phrase)

    # Authority
    for word in AUTHORITY:
        if word in line:
            signals.add(f"authority_impersonation:{word}")
            timeline.append("authority")

    # Urgency
    for word in URGENCY:
        if word in line:
            signals.add("urgency_detected")
            timeline.append("urgency")

    # URL
    if contains_url(line):
        score += 5
        signals.add("contains_url")

# Sequence bonus: authority → urgency → action
if "authority" in timeline and "urgency" in timeline and ("otp" in timeline or "click the link" in timeline):
    score += 10
    signals.add("dangerous_sequence:authority_urgency_action")

# Clamp score
score = min(score, 100)

# Risk level
if score >= 70:
    level = "high"
elif score >= 40:
    level = "medium"
else:
    level = "low"

# ---- FINAL OUTPUT ----
print(f"risk_score: {score}/100")
print(f"risk_level: {level}")
print("matched_phrases:")
for p in sorted(matched_phrases):
    print(f"  - {p}")
print("signals:")
for s in sorted(signals):
    print(f"  - {s}")
print("explanation:")
print("  - Risk calculated using phrase detection, urgency, authority impersonation, and sequence analysis")
