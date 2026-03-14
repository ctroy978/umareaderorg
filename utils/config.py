import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
STORAGE_SECRET = os.environ["STORAGE_SECRET"]
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8080")
