"""
matcher.py

Deterministic, language-agnostic-ish fuzzy matching helpers.

Constraints:
- No external libraries
- Avoid regex-heavy approaches
- Support minor spelling errors, word reordering, and spoken/hinglish forms
"""

from __future__ import annotations

import string


def normalize_text(text: str) -> str:
    """
    Lowercase, strip punctuation, normalize whitespace.
    Keep digits (useful for reference numbers).
    """

    t = (text or "").lower()
    # Replace punctuation with spaces to preserve token boundaries.
    table = str.maketrans({c: " " for c in string.punctuation})
    t = t.translate(table)
    return " ".join(t.split())


def tokenize(text: str) -> list[str]:
    t = normalize_text(text)
    return [w for w in t.split(" ") if w]


def _levenshtein_leq(a: str, b: str, max_dist: int) -> bool:
    """
    Returns True if Levenshtein distance(a,b) <= max_dist.
    Deterministic and fast for small max_dist (1-2).
    """

    if a == b:
        return True
    if max_dist <= 0:
        return False
    la, lb = len(a), len(b)
    if abs(la - lb) > max_dist:
        return False
    if la == 0 or lb == 0:
        return max(la, lb) <= max_dist

    # DP row, optimized for small max_dist.
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        ai = a[i - 1]
        row_min = cur[0]
        for j in range(1, lb + 1):
            cost = 0 if ai == b[j - 1] else 1
            cur[j] = min(
                prev[j] + 1,      # delete
                cur[j - 1] + 1,   # insert
                prev[j - 1] + cost,  # substitute
            )
            row_min = min(row_min, cur[j])
        if row_min > max_dist:
            return False
        prev = cur
    return prev[lb] <= max_dist


def fuzzy_token_in(tokens: list[str], target: str, *, max_dist: int = 1) -> bool:
    """
    True if target is present in tokens with minor spelling tolerance.
    """

    if not target:
        return False
    t = target.lower()
    for w in tokens:
        if w == t:
            return True
        if max_dist > 0 and len(w) >= 3 and len(t) >= 3 and _levenshtein_leq(w, t, max_dist):
            return True
    return False


def fuzzy_phrase_match(tokens: list[str], phrase: str, *, max_dist: int = 1, window_slack: int = 2) -> bool:
    """
    Fuzzy phrase match that allows:
    - word reordering (bag-of-words containment)
    - minor typos per token (levenshtein <= max_dist)
    - slight extra/missing filler words (window_slack affects early exit only)

    Implementation: phrase tokens must each appear somewhere in tokens fuzzily.
    This intentionally favors recall; scoring rules should be conservative.
    """

    p_toks = tokenize(phrase)
    if not p_toks:
        return False
    if len(p_toks) == 1:
        return fuzzy_token_in(tokens, p_toks[0], max_dist=max_dist)

    # Quick pruning: if transcript is very short vs phrase, skip.
    if len(tokens) + window_slack < len(p_toks):
        return False

    # Bag-of-words containment with fuzzy token match.
    for pt in p_toks:
        if not fuzzy_token_in(tokens, pt, max_dist=max_dist):
            return False
    return True

