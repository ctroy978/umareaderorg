import os
from dotenv import load_dotenv

load_dotenv()

STORAGE_SECRET = os.environ["STORAGE_SECRET"]
SESSION_CODE_SECRET = os.environ["SESSION_CODE_SECRET"]
TEACHER_EMAILS = [e.strip().lower() for e in os.environ.get("TEACHER_EMAILS", "").split(",") if e.strip()]
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8080")
DEFAULT_STRATEGY = os.environ.get("DEFAULT_STRATEGY")
DB_PATH = os.environ.get("DB_PATH", "reader.db")
