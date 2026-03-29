"""
Session completion code generation and verification.

Code format: L3-AB3KQ7-F4A91C-3ZXQM2  (22 chars total)
  L3      — 'L' + success level digit (1-4)
  AB3KQ7  — first 6 chars of base32(SHA-256(email.lower()))
  F4A91C  — random nonce (3 bytes as 6 uppercase hex chars)
  3ZXQM2  — first 6 chars of base32(HMAC-SHA256(secret, level+nonce+email))
"""

import base64
import hashlib
import hmac
import secrets
from typing import Optional


LEVEL_THRESHOLDS = [
    (0.85, 4),
    (0.70, 3),
    (0.55, 2),
]
DEFAULT_LEVEL = 2

LEVEL_LABELS = {
    1: "Needs Support (mastery < 55%)",
    2: "Satisfactory (mastery 55-69%)",
    3: "Good (mastery 70-84%)",
    4: "Excellent (mastery ≥ 85%)",
}

RANK_TITLES = {1: "Ashigaru", 2: "Samurai", 3: "Hatamoto", 4: "Daimyo"}

RANK_FEEDBACK = {
    1: "There is room to improve. Keep practicing.",
    2: "Good effort today. You are making progress.",
    3: "Strong performance. Well done.",
    4: "Excellent work today.",
}


def score_to_level(mastery_score: Optional[float]) -> int:
    if mastery_score is None:
        return DEFAULT_LEVEL
    for threshold, level in LEVEL_THRESHOLDS:
        if mastery_score >= threshold:
            return level
    return 1


def _email_hash(email: str) -> str:
    digest = hashlib.sha256(email.lower().encode()).digest()
    return base64.b32encode(digest).decode()[:6]


def _make_nonce() -> str:
    return secrets.token_bytes(3).hex().upper()


def _compute_hmac(level: int, nonce: str, email: str, secret: str) -> str:
    payload = f"{level}{nonce}{email.lower()}"
    mac = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    return base64.b32encode(mac).decode()[:6]


def generate_completion_code(email: str, mastery_score: Optional[float]) -> str:
    from utils.config import SESSION_CODE_SECRET
    level = score_to_level(mastery_score)
    email_hash = _email_hash(email)
    nonce = _make_nonce()
    mac = _compute_hmac(level, nonce, email, SESSION_CODE_SECRET)
    return f"L{level}-{email_hash}-{nonce}-{mac}"


def verify_completion_code(code: str, email: str, secret: str) -> dict:
    """
    Verify a completion code against a known email and secret.
    Returns dict with keys: valid (bool), level (int), error (str or None).
    """
    parts = code.upper().split("-")
    if len(parts) != 4:
        return {"valid": False, "level": None, "error": "Wrong number of segments"}

    level_seg, email_hash_seg, nonce_seg, mac_seg = parts

    if len(level_seg) != 2 or level_seg[0] != "L" or level_seg[1] not in "1234":
        return {"valid": False, "level": None, "error": "Invalid level segment"}
    if len(email_hash_seg) != 6 or len(nonce_seg) != 6 or len(mac_seg) != 6:
        return {"valid": False, "level": None, "error": "Invalid segment lengths"}

    level = int(level_seg[1])

    expected_hash = _email_hash(email)
    if email_hash_seg != expected_hash:
        return {"valid": False, "level": level, "error": "Email hash mismatch"}

    expected_mac = _compute_hmac(level, nonce_seg, email, secret)
    if mac_seg != expected_mac:
        return {"valid": False, "level": level, "error": "HMAC verification failed"}

    return {"valid": True, "level": level, "error": None}


def decode_completion_code(code: str, secret: str) -> dict:
    """
    Parse and HMAC-verify a code without knowing the student email.
    Returns parsed segments; email must be looked up externally via email_hash.
    """
    parts = code.upper().split("-")
    if len(parts) != 4:
        return {"valid": False, "error": "Wrong number of segments"}

    level_seg, email_hash_seg, nonce_seg, mac_seg = parts

    if len(level_seg) != 2 or level_seg[0] != "L" or level_seg[1] not in "1234":
        return {"valid": False, "error": "Invalid level segment"}
    if len(email_hash_seg) != 6 or len(nonce_seg) != 6 or len(mac_seg) != 6:
        return {"valid": False, "error": "Invalid segment lengths"}

    level = int(level_seg[1])

    # HMAC cannot be verified without the email — return parsed data for roster lookup
    return {
        "valid": None,  # None = not yet verified (need email)
        "level": level,
        "email_hash": email_hash_seg,
        "nonce": nonce_seg,
        "mac": mac_seg,
        "secret": secret,
        "error": None,
    }
