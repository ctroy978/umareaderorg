import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
STORAGE_SECRET = os.environ["STORAGE_SECRET"]
SESSION_CODE_SECRET = os.environ["SESSION_CODE_SECRET"]
TEACHER_EMAILS = [e.strip().lower() for e in os.environ.get("TEACHER_EMAILS", "").split(",") if e.strip()]
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8080")
DEFAULT_STRATEGY = os.environ.get("DEFAULT_STRATEGY")  # e.g. "Summarizing"; None in production
