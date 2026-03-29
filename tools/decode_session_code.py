#!/usr/bin/env python3
"""
Teacher decoder for session completion codes.

Usage:
    python tools/decode_session_code.py L3-AB3KQ7-F4A91C-3ZXQM2 \\
        [--students students.csv] \\
        [--secret SECRET_KEY]

If --secret is not provided, reads SESSION_CODE_SECRET from the environment
(or from a .env file in the current directory).

The optional students CSV must have at minimum an 'email' column.
A 'name' column is displayed if present.

Example students.csv:
    name,email
    Jane Smith,jane.smith@school.edu
    John Doe,john.doe@school.edu
"""

import argparse
import base64
import csv
import hashlib
import hmac
import os
import sys


LEVEL_LABELS = {
    1: "Needs Support  (mastery < 55%)",
    2: "Satisfactory   (mastery 55-69%)",
    3: "Good           (mastery 70-84%)",
    4: "Excellent      (mastery ≥ 85%)",
}


def _email_hash(email: str) -> str:
    digest = hashlib.sha256(email.lower().encode()).digest()
    return base64.b32encode(digest).decode()[:6]


def _compute_hmac(level: int, nonce: str, email: str, secret: str) -> str:
    payload = f"{level}{nonce}{email.lower()}"
    mac = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    return base64.b32encode(mac).decode()[:6]


def load_students(csv_path: str) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return []
    if "email" not in rows[0]:
        print("ERROR: students CSV must have an 'email' column.", file=sys.stderr)
        sys.exit(1)
    return rows


def decode(code: str, secret: str, students: list[dict]) -> None:
    parts = code.upper().strip().split("-")
    if len(parts) != 4:
        print(f"INVALID: expected 4 dash-separated segments, got {len(parts)}")
        return

    level_seg, email_hash_seg, nonce_seg, mac_seg = parts

    if len(level_seg) != 2 or level_seg[0] != "L" or level_seg[1] not in "1234":
        print(f"INVALID: bad level segment '{level_seg}' (expected L1–L4)")
        return

    if len(email_hash_seg) != 6:
        print(f"INVALID: email hash segment must be 6 chars, got {len(email_hash_seg)}")
        return

    if len(nonce_seg) != 6:
        print(f"INVALID: nonce segment must be 6 chars, got {len(nonce_seg)}")
        return

    if len(mac_seg) != 6:
        print(f"INVALID: MAC segment must be 6 chars, got {len(mac_seg)}")
        return

    level = int(level_seg[1])

    # Find matching student(s) via email hash
    hash_matched = []
    for row in students:
        email = row["email"].strip()
        if _email_hash(email) == email_hash_seg:
            hash_matched.append(row)

    # Verify HMAC for each hash-matched student
    hmac_valid = False
    verified_students = []
    if hash_matched:
        for row in hash_matched:
            email = row["email"].strip()
            expected_mac = _compute_hmac(level, nonce_seg, email, secret)
            if mac_seg == expected_mac:
                hmac_valid = True
                verified_students.append(row)
    elif not students:
        hmac_valid = None  # Can't verify without a roster

    # Output
    print(f"\nCode:    {code.upper()}")

    if hmac_valid is True:
        print("Valid:   YES")
    elif hmac_valid is False:
        if hash_matched:
            print("Valid:   NO — HMAC verification failed (code may be tampered or wrong secret)")
        else:
            print("Valid:   NO — student not found in roster (HMAC unverified)")
    else:
        print("Valid:   UNVERIFIED (no students roster provided)")

    print(f"Level:   {level} — {LEVEL_LABELS.get(level, '?')}")

    if not students:
        print("Student: UNKNOWN (no --students file provided)")
    elif verified_students:
        for row in verified_students:
            name = row.get("name", "").strip()
            email = row["email"].strip()
            display = f"{name} ({email})" if name else email
            print(f"Student: {display}")
    elif hash_matched:
        # Hash matched but HMAC failed — show candidate with warning
        for row in hash_matched:
            name = row.get("name", "").strip()
            email = row["email"].strip()
            display = f"{name} ({email})" if name else email
            print(f"Student: {display} [HMAC FAILED — possible tampered code]")
    else:
        print("Student: UNKNOWN (email not found in roster)")

    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Decode and verify a session completion code."
    )
    parser.add_argument("code", help="The completion code (e.g. L3-AB3KQ7-F4A91C-3ZXQM2)")
    parser.add_argument("--students", metavar="CSV", help="Path to students CSV file")
    parser.add_argument("--secret", help="SESSION_CODE_SECRET (defaults to env var)")
    args = parser.parse_args()

    # Resolve secret
    secret = args.secret
    if not secret:
        # Try loading from .env in cwd
        env_path = os.path.join(os.getcwd(), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("SESSION_CODE_SECRET="):
                        secret = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        if not secret:
            secret = os.environ.get("SESSION_CODE_SECRET")
    if not secret:
        print(
            "ERROR: SESSION_CODE_SECRET not found. "
            "Provide --secret or set the environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    students = []
    if args.students:
        students = load_students(args.students)

    decode(args.code, secret, students)


if __name__ == "__main__":
    main()
