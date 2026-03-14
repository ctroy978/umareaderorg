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
    response = client.table("profiles").select("*").eq("user_id", user_id).single().execute()
    return response.data
