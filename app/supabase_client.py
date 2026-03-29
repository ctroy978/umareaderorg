from supabase import create_client, Client
from utils.config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY

_client: Client | None = None
_service_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _client


def get_service_client() -> Client:
    """Return a service-role client that bypasses RLS — for trusted server-side writes only."""
    global _service_client
    if _service_client is None:
        _service_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _service_client


def _authed_client(access_token: str) -> Client:
    """Return a client authenticated as the user (satisfies RLS auth.uid() checks)."""
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    client.postgrest.auth(access_token)
    return client


def exchange_code_for_session(code: str):
    client = get_client()
    return client.auth.exchange_code_for_session({"auth_code": code})


def get_profile(user_id: str, access_token: str | None = None):
    client = _authed_client(access_token) if access_token else get_client()
    response = client.table("profiles").select("*").eq("user_id", user_id).maybe_single().execute()
    return response.data


def upsert_profile(user_id: str, data: dict, access_token: str | None = None):
    payload = {"user_id": user_id, **data}
    get_service_client().table("profiles").upsert(payload, on_conflict="user_id").execute()


def list_all_users() -> list[dict]:
    """Return all auth users as list of dicts with 'id', 'email', 'full_name'."""
    client = get_service_client()
    response = client.auth.admin.list_users()
    users = response if isinstance(response, list) else getattr(response, 'users', [])
    result = []
    for u in users:
        email = getattr(u, 'email', None) or ''
        full_name = ''
        meta = getattr(u, 'user_metadata', {}) or {}
        full_name = meta.get('full_name') or meta.get('name') or ''
        result.append({'id': getattr(u, 'id', ''), 'email': email, 'full_name': full_name})
    return result


def get_placement_progress(user_id: str, access_token: str | None = None):
    client = _authed_client(access_token) if access_token else get_client()
    response = client.table("placement_progress").select("*").eq("user_id", user_id).maybe_single().execute()
    return response.data


def save_placement_progress(user_id: str, passage_idx: int, q_idx: int, answers: list, access_token: str | None = None):
    client = _authed_client(access_token) if access_token else get_client()
    client.table("placement_progress").upsert(
        {
            "user_id": user_id,
            "current_passage_index": passage_idx,
            "current_question_index": q_idx,
            "answers": answers,
            "updated_at": "now()",
        },
        on_conflict="user_id",
    ).execute()


def save_placement_response(user_id: str, passage_id: str, q_id: str, answer: str, is_correct, access_token: str | None = None):
    client = _authed_client(access_token) if access_token else get_client()
    client.table("placement_responses").insert(
        {
            "user_id": user_id,
            "passage_id": passage_id,
            "question_id": q_id,
            "answer": answer,
            "is_correct": is_correct,
        }
    ).execute()


def delete_placement_progress(user_id: str, access_token: str | None = None):
    client = _authed_client(access_token) if access_token else get_client()
    client.table("placement_progress").delete().eq("user_id", user_id).execute()


# --- Bundle helpers ---

def create_session_bundle(user_id: str, topic: str) -> str:
    """Insert bundle row with status='generating'. Returns bundle_id."""
    client = get_client()
    resp = client.table("session_bundles").insert(
        {"user_id": user_id, "topic": topic, "status": "generating"}
    ).execute()
    return resp.data[0]["id"]


def update_session_bundle(bundle_id: str, **fields) -> None:
    client = get_client()
    client.table("session_bundles").update(
        {"status": "ready", **fields}
    ).eq("id", bundle_id).execute()


def fail_session_bundle(bundle_id: str, error_message: str) -> None:
    client = get_client()
    client.table("session_bundles").update(
        {"status": "error", "error_message": error_message}
    ).eq("id", bundle_id).execute()


def get_session_bundle(bundle_id: str) -> dict | None:
    client = get_client()
    resp = (client.table("session_bundles").select("*")
            .eq("id", bundle_id).maybe_single().execute())
    return resp.data


def get_active_bundle(user_id: str) -> dict | None:
    client = get_client()
    resp = (client.table("session_bundles").select("*")
            .eq("user_id", user_id)
            .in_("status", ["generating", "ready"])
            .order("created_at", desc=True).limit(1).execute())
    return resp.data[0] if resp.data else None


def get_topic_from_bank(category: str, user_id: str) -> dict | None:
    """Return a random unused topic for this student in the given category, or None."""
    client = get_client()
    used_resp = (client.table("session_bundles")
                 .select("topic_bank_id")
                 .eq("user_id", user_id)
                 .not_.is_("topic_bank_id", "null")
                 .execute())
    used_ids = [r["topic_bank_id"] for r in used_resp.data if r.get("topic_bank_id")]

    query = client.table("topic_bank").select("*").eq("category", category)
    if used_ids:
        query = query.not_.in_("id", used_ids)
    resp = query.execute()

    if not resp.data:
        return None
    import random
    return random.choice(resp.data)


# --- Session helpers ---

def create_session(student_id: str, bundle_id: str | None = None, strategy: str | None = None) -> str:
    payload = {"student_id": student_id}
    if bundle_id:
        payload["bundle_id"] = bundle_id
    if strategy:
        payload["strategy_of_session"] = strategy
    response = get_service_client().table("sessions").insert(payload).execute()
    return response.data[0]["id"]


def update_session_step(session_id: str, step: int, responses_json: dict):
    get_service_client().table("sessions").update(
        {"current_step": step, "responses_json": responses_json}
    ).eq("id", session_id).execute()


def complete_session(session_id: str, responses_json: dict):
    get_service_client().table("sessions").update(
        {
            "status": "completed",
            "completed_at": "now()",
            "responses_json": responses_json,
        }
    ).eq("id", session_id).execute()


def soft_delete_session(session_id: str, student_id: str):
    get_service_client().table("sessions").update(
        {"deleted_at": "now()"}
    ).eq("id", session_id).eq("student_id", student_id).execute()


def get_today_skip_count(student_id: str) -> int:
    import datetime as _dt
    today = _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    response = (
        get_client()
        .table("sessions")
        .select("id", count="exact")
        .eq("student_id", student_id)
        .not_.is_("deleted_at", "null")
        .gte("deleted_at", today)
        .execute()
    )
    return response.count or 0


def get_active_session(student_id: str) -> dict | None:
    client = get_client()
    response = (
        client.table("sessions")
        .select("*")
        .eq("student_id", student_id)
        .eq("status", "in_progress")
        .is_("deleted_at", "null")
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def save_session_response(
    session_id: str,
    step: str,
    prompt: str,
    answer: str,
    feedback: str,
    is_correct: bool | None,
):
    get_service_client().table("session_responses").insert(
        {
            "session_id": session_id,
            "step": step,
            "prompt": prompt,
            "student_answer": answer,
            "feedback_text": feedback,
            "is_correct": is_correct,
        }
    ).execute()


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
    """Log an agent run to the agent_runs table. Never raises."""
    try:
        client = get_client()
        client.table("agent_runs").insert(
            {
                "student_id": student_id,
                "tool_name": tool_name,
                "input_json": input_json,
                "output_json": output_json,
                "error_text": error_text,
                "duration_ms": duration_ms,
                "session_id": session_id,
                "iteration_count": iteration_count,
            }
        ).execute()
    except Exception:
        pass


def get_session_responses(session_id: str) -> list[dict]:
    client = get_client()
    resp = client.table("session_responses").select("*").eq("session_id", session_id).execute()
    return resp.data or []


def get_recent_strategies(student_id: str, limit: int = 3) -> list[str]:
    """Return strategy_of_session values from the student's most recent completed sessions."""
    client = get_client()
    resp = (
        client.table("sessions")
        .select("strategy_of_session")
        .eq("student_id", student_id)
        .eq("status", "completed")
        .not_.is_("strategy_of_session", "null")
        .order("completed_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [r["strategy_of_session"] for r in (resp.data or []) if r.get("strategy_of_session")]


def get_available_strategies(reading_level: str) -> list[str]:
    """Return distinct active strategy names available for a given reading level."""
    client = get_client()
    resp = (
        client.table("strategy_lessons")
        .select("strategy")
        .eq("reading_level", reading_level)
        .eq("is_active", True)
        .execute()
    )
    return list({r["strategy"] for r in (resp.data or []) if r.get("strategy")})


def get_strategy_lesson(strategy: str, reading_level: str) -> dict | None:
    """Fetch the active strategy lesson for a given strategy + reading level (variation_id=1)."""
    client = get_client()
    resp = (
        client.table("strategy_lessons")
        .select("*")
        .eq("strategy", strategy)
        .eq("reading_level", reading_level)
        .eq("variation_id", 1)
        .eq("is_active", True)
        .maybe_single()
        .execute()
    )
    return resp.data


def get_session_strategy(session_id: str) -> str | None:
    """Return strategy_of_session for a given session, or None if not set."""
    client = get_client()
    resp = (
        client.table("sessions")
        .select("strategy_of_session")
        .eq("id", session_id)
        .maybe_single()
        .execute()
    )
    if resp.data:
        return resp.data.get("strategy_of_session")
    return None


def get_last_completed_session(student_id: str) -> dict | None:
    client = get_client()
    response = (
        client.table("sessions")
        .select("*")
        .eq("student_id", student_id)
        .eq("status", "completed")
        .is_("deleted_at", "null")
        .order("completed_at", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None
