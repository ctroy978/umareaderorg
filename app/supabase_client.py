"""
SQLite-backed replacement for the Supabase client.
All public function signatures are identical to the original.
"""
import hashlib
import hmac
import json
import os
import random
import uuid
from dataclasses import dataclass
from typing import Any

from app.db import get_conn, now
from utils.config import DB_PATH
import app.db as _db

# Configure db path at import time
_db.configure(DB_PATH)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row(cursor_or_conn, sql: str, params: tuple = ()) -> dict | None:
    conn = get_conn()
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def _rows(sql: str, params: tuple = ()) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def _exec(sql: str, params: tuple = ()) -> None:
    conn = get_conn()
    conn.execute(sql, params)
    conn.commit()


def _jdump(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value)


def _jload(value: str | None) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _decode_json_fields(row: dict | None, *fields: str) -> dict | None:
    if row is None:
        return None
    for f in fields:
        if f in row:
            row[f] = _jload(row[f])
    return row


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Auth stubs
# ---------------------------------------------------------------------------

@dataclass
class _FakeSessionInner:
    access_token: str
    refresh_token: str


@dataclass
class _FakeUserInner:
    id: str
    email: str


@dataclass
class _FakeAuthResult:
    session: _FakeSessionInner
    user: _FakeUserInner


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

def get_profile(user_id: str, access_token: str | None = None) -> dict | None:
    row = _row(None, "SELECT * FROM profiles WHERE user_id=?", (user_id,))
    return _decode_json_fields(row, "interests")


def upsert_profile(user_id: str, data: dict, access_token: str | None = None) -> None:
    existing = _row(None, "SELECT * FROM profiles WHERE user_id=?", (user_id,))
    interests = data.get("interests")
    if isinstance(interests, (list, dict)):
        data = {**data, "interests": _jdump(interests)}

    if existing:
        sets = ", ".join(f"{k}=?" for k in data)
        vals = list(data.values()) + [user_id]
        _exec(f"UPDATE profiles SET {sets} WHERE user_id=?", tuple(vals))
    else:
        fields = ["user_id"] + list(data.keys())
        placeholders = ", ".join("?" for _ in fields)
        vals = [user_id] + list(data.values())
        _exec(
            f"INSERT INTO profiles ({', '.join(fields)}) VALUES ({placeholders})",
            tuple(vals),
        )


def list_all_users() -> list[dict]:
    return _rows("SELECT id, email, full_name FROM users")


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------

def get_placement_progress(user_id: str, access_token: str | None = None) -> dict | None:
    row = _row(None, "SELECT * FROM placement_progress WHERE user_id=?", (user_id,))
    return _decode_json_fields(row, "answers")


def save_placement_progress(
    user_id: str,
    passage_idx: int,
    q_idx: int,
    answers: list,
    access_token: str | None = None,
) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO placement_progress (user_id, current_passage_index, current_question_index, answers, updated_at)
           VALUES (?,?,?,?,?)
           ON CONFLICT(user_id) DO UPDATE SET
               current_passage_index=excluded.current_passage_index,
               current_question_index=excluded.current_question_index,
               answers=excluded.answers,
               updated_at=excluded.updated_at""",
        (user_id, passage_idx, q_idx, _jdump(answers), now()),
    )
    conn.commit()


def save_placement_response(
    user_id: str,
    passage_id: str,
    q_id: str,
    answer: str,
    is_correct,
    access_token: str | None = None,
) -> None:
    _exec(
        "INSERT INTO placement_responses (id, user_id, passage_id, question_id, answer, is_correct) VALUES (?,?,?,?,?,?)",
        (_new_id(), user_id, passage_id, q_id, answer, int(bool(is_correct)) if is_correct is not None else None),
    )


def delete_placement_progress(user_id: str, access_token: str | None = None) -> None:
    _exec("DELETE FROM placement_progress WHERE user_id=?", (user_id,))


# ---------------------------------------------------------------------------
# Session bundles
# ---------------------------------------------------------------------------

def create_session_bundle(user_id: str, topic: str) -> str:
    bundle_id = _new_id()
    _exec(
        "INSERT INTO session_bundles (id, user_id, topic, status) VALUES (?,?,?,?)",
        (bundle_id, user_id, topic, "generating"),
    )
    return bundle_id


_BUNDLE_JSON_FIELDS = (
    "passage_sections", "vocab_questions", "comprehension_questions",
    "mastery_questions",
)


def _decode_bundle(row: dict | None) -> dict | None:
    return _decode_json_fields(row, *_BUNDLE_JSON_FIELDS)


def update_session_bundle(bundle_id: str, **fields) -> None:
    fields["status"] = fields.get("status", "ready")
    for f in _BUNDLE_JSON_FIELDS:
        if f in fields and not isinstance(fields[f], str):
            fields[f] = _jdump(fields[f])
    sets = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [bundle_id]
    _exec(f"UPDATE session_bundles SET {sets} WHERE id=?", tuple(vals))


def fail_session_bundle(bundle_id: str, error_message: str) -> None:
    _exec(
        "UPDATE session_bundles SET status='error', error_message=? WHERE id=?",
        (error_message, bundle_id),
    )


def get_session_bundle(bundle_id: str) -> dict | None:
    row = _row(None, "SELECT * FROM session_bundles WHERE id=?", (bundle_id,))
    return _decode_bundle(row)


def get_active_bundle(user_id: str) -> dict | None:
    row = _row(
        None,
        "SELECT * FROM session_bundles WHERE user_id=? AND status IN ('generating','ready') ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    )
    return _decode_bundle(row)


def get_topic_from_bank(category: str, user_id: str) -> dict | None:
    conn = get_conn()
    used_rows = conn.execute(
        "SELECT topic_bank_id FROM session_bundles WHERE user_id=? AND topic_bank_id IS NOT NULL",
        (user_id,),
    ).fetchall()
    used_ids = [r["topic_bank_id"] for r in used_rows]

    if used_ids:
        placeholders = ",".join("?" * len(used_ids))
        rows = conn.execute(
            f"SELECT * FROM topic_bank WHERE category=? AND id NOT IN ({placeholders})",
            (category, *used_ids),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM topic_bank WHERE category=?", (category,)
        ).fetchall()

    if not rows:
        return None
    row = dict(random.choice(rows))
    row["key_facts"] = _jload(row.get("key_facts"))
    return row


# ---------------------------------------------------------------------------
# Passage library
# ---------------------------------------------------------------------------

def get_library_entry(topic_bank_id: str, lexile_level: str) -> dict | None:
    row = _row(
        None,
        "SELECT * FROM passage_library WHERE topic_bank_id=? AND lexile_level=? LIMIT 1",
        (topic_bank_id, lexile_level),
    )
    return _decode_json_fields(row, "passage_sections", "vocab_questions", "mastery_questions")


def save_library_entry(
    topic_bank_id: str,
    lexile_level: str,
    passage_title: str,
    passage_sections: list,
    vocab_questions: list,
    mastery_questions: list,
) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO passage_library
               (topic_bank_id, lexile_level, passage_title, passage_sections, vocab_questions, mastery_questions)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT(topic_bank_id, lexile_level) DO UPDATE SET
               passage_title=excluded.passage_title,
               passage_sections=excluded.passage_sections,
               vocab_questions=excluded.vocab_questions,
               mastery_questions=excluded.mastery_questions""",
        (
            topic_bank_id,
            lexile_level,
            passage_title,
            _jdump(passage_sections),
            _jdump(vocab_questions),
            _jdump(mastery_questions),
        ),
    )
    conn.commit()


def increment_library_use_count(topic_bank_id: str, lexile_level: str) -> None:
    try:
        _exec(
            "UPDATE passage_library SET use_count = use_count + 1 WHERE topic_bank_id=? AND lexile_level=?",
            (topic_bank_id, lexile_level),
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

def create_session(student_id: str, bundle_id: str | None = None, strategy: str | None = None) -> str:
    session_id = _new_id()
    _exec(
        "INSERT INTO sessions (id, student_id, bundle_id, strategy_of_session) VALUES (?,?,?,?)",
        (session_id, student_id, bundle_id, strategy),
    )
    return session_id


def update_session_step(session_id: str, step: int, responses_json: dict) -> None:
    _exec(
        "UPDATE sessions SET current_step=?, responses_json=? WHERE id=?",
        (step, _jdump(responses_json), session_id),
    )


def complete_session(session_id: str, responses_json: dict) -> None:
    _exec(
        "UPDATE sessions SET status='completed', completed_at=?, responses_json=? WHERE id=?",
        (now(), _jdump(responses_json), session_id),
    )


def soft_delete_session(session_id: str, student_id: str) -> None:
    _exec(
        "UPDATE sessions SET deleted_at=? WHERE id=? AND student_id=?",
        (now(), session_id, student_id),
    )


def get_today_skip_count(student_id: str) -> int:
    import datetime as _dt
    today = _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM sessions WHERE student_id=? AND deleted_at IS NOT NULL AND deleted_at >= ?",
        (student_id, today),
    ).fetchone()
    return row["cnt"] if row else 0


def get_active_session(student_id: str) -> dict | None:
    row = _row(
        None,
        "SELECT * FROM sessions WHERE student_id=? AND status='in_progress' AND deleted_at IS NULL ORDER BY started_at DESC LIMIT 1",
        (student_id,),
    )
    return _decode_json_fields(row, "responses_json")


def save_session_response(
    session_id: str,
    step: str,
    prompt: str,
    answer: str,
    feedback: str,
    is_correct: bool | None,
    rubric_score: int | None = None,
) -> None:
    _exec(
        """INSERT INTO session_responses
               (id, session_id, step, prompt, student_answer, feedback_text, is_correct, rubric_score)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            _new_id(),
            session_id,
            step,
            prompt,
            answer,
            feedback,
            int(is_correct) if is_correct is not None else None,
            rubric_score,
        ),
    )


def log_agent_run(
    student_id: str,
    tool_name: str,
    input_json: dict,
    *,
    output_json: dict | None = None,
    error_text: str | None = None,
    duration_ms: int | None = None,
    session_id: str | None = None,
    iteration_count: int | None = None,
) -> None:
    try:
        _exec(
            """INSERT INTO agent_runs
                   (id, student_id, tool_name, input_json, output_json, error_text, duration_ms, session_id, iteration_count)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                _new_id(),
                student_id,
                tool_name,
                _jdump(input_json),
                _jdump(output_json),
                error_text,
                duration_ms,
                session_id,
                iteration_count,
            ),
        )
    except Exception:
        pass


def get_session_responses(session_id: str) -> list[dict]:
    return _rows("SELECT * FROM session_responses WHERE session_id=?", (session_id,))


def get_recent_strategies(student_id: str, limit: int = 3) -> list[str]:
    rows = _rows(
        """SELECT strategy_of_session FROM sessions
           WHERE student_id=? AND status='completed' AND strategy_of_session IS NOT NULL
           ORDER BY completed_at DESC LIMIT ?""",
        (student_id, limit),
    )
    return [r["strategy_of_session"] for r in rows if r.get("strategy_of_session")]


def get_available_strategies(reading_level: str) -> list[str]:
    rows = _rows(
        "SELECT DISTINCT strategy FROM strategy_lessons WHERE reading_level=? AND is_active=1",
        (reading_level,),
    )
    return [r["strategy"] for r in rows if r.get("strategy")]


def get_strategy_lesson(strategy: str, reading_level: str) -> dict | None:
    return _row(
        None,
        "SELECT * FROM strategy_lessons WHERE strategy=? AND reading_level=? AND variation_id=1 AND is_active=1",
        (strategy, reading_level),
    )


def get_session_strategy(session_id: str) -> str | None:
    row = _row(None, "SELECT strategy_of_session FROM sessions WHERE id=?", (session_id,))
    return row.get("strategy_of_session") if row else None


def get_last_completed_session(student_id: str) -> dict | None:
    row = _row(
        None,
        "SELECT * FROM sessions WHERE student_id=? AND status='completed' AND deleted_at IS NULL ORDER BY completed_at DESC LIMIT 1",
        (student_id,),
    )
    return _decode_json_fields(row, "responses_json")


# ---------------------------------------------------------------------------
# Enrollment & password auth
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260_000).hex()
    return f"{salt}${h}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split('$', 1)
        expected = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260_000).hex()
        return hmac.compare_digest(expected, h)
    except Exception:
        return False


def is_enrolled(email: str) -> bool:
    row = _row(None, "SELECT id FROM users WHERE email=?", (email.strip().lower(),))
    return row is not None


def has_password(email: str) -> bool:
    row = _row(None, "SELECT password_hash FROM users WHERE email=?", (email.strip().lower(),))
    return bool(row and row.get("password_hash"))


def enroll_student(email: str, full_name: str) -> str:
    email = email.strip().lower()
    conn = get_conn()
    existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        return existing["id"]
    user_id = _new_id()
    conn.execute(
        "INSERT INTO users (id, email, full_name) VALUES (?,?,?)",
        (user_id, email, full_name.strip() or email.split("@")[0]),
    )
    conn.commit()
    return user_id


def enroll_students_bulk(students: list[dict]) -> dict:
    enrolled = 0
    skipped = 0
    for s in students:
        email = (s.get("email") or "").strip().lower()
        if not email:
            continue
        full_name = (s.get("full_name") or "").strip()
        conn = get_conn()
        existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            skipped += 1
        else:
            conn.execute(
                "INSERT INTO users (id, email, full_name) VALUES (?,?,?)",
                (_new_id(), email, full_name or email.split("@")[0]),
            )
            conn.commit()
            enrolled += 1
    return {"enrolled": enrolled, "skipped": skipped}


def set_password(user_id: str, password: str) -> None:
    _exec(
        "UPDATE users SET password_hash=? WHERE id=?",
        (_hash_password(password), user_id),
    )


def authenticate_user(email: str, password: str) -> _FakeAuthResult | None:
    email = email.strip().lower()
    conn = get_conn()
    row = conn.execute("SELECT id, password_hash FROM users WHERE email=?", (email,)).fetchone()
    if not row or not row["password_hash"]:
        return None
    if not _verify_password(password, row["password_hash"]):
        return None
    user_id = row["id"]
    return _FakeAuthResult(
        session=_FakeSessionInner(
            access_token=f"local-{user_id}",
            refresh_token=f"local-refresh-{user_id}",
        ),
        user=_FakeUserInner(id=user_id, email=email),
    )
