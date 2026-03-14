from supabase import create_client, Client
from utils.config import SUPABASE_URL, SUPABASE_ANON_KEY

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _client


def exchange_code_for_session(code: str):
    client = get_client()
    return client.auth.exchange_code_for_session({"auth_code": code})


def get_profile(user_id: str):
    client = get_client()
    response = client.table("profiles").select("*").eq("user_id", user_id).maybe_single().execute()
    return response.data


def upsert_profile(user_id: str, data: dict):
    client = get_client()
    payload = {"user_id": user_id, **data}
    client.table("profiles").upsert(payload, on_conflict="user_id").execute()


def get_placement_progress(user_id: str):
    client = get_client()
    response = client.table("placement_progress").select("*").eq("user_id", user_id).maybe_single().execute()
    return response.data


def save_placement_progress(user_id: str, passage_idx: int, q_idx: int, answers: list):
    client = get_client()
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


def save_placement_response(user_id: str, passage_id: str, q_id: str, answer: str, is_correct):
    client = get_client()
    client.table("placement_responses").insert(
        {
            "user_id": user_id,
            "passage_id": passage_id,
            "question_id": q_id,
            "answer": answer,
            "is_correct": is_correct,
        }
    ).execute()


def delete_placement_progress(user_id: str):
    client = get_client()
    client.table("placement_progress").delete().eq("user_id", user_id).execute()
