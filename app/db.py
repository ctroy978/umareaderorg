import sqlite3
import pathlib
import datetime

_SCHEMA = pathlib.Path(__file__).parent.parent / "db" / "schema.sql"

_db_path: str = "reader.db"
_initialized = False


def configure(db_path: str) -> None:
    global _db_path, _initialized
    _db_path = db_path
    _initialized = False


def get_conn() -> sqlite3.Connection:
    global _initialized
    conn = sqlite3.connect(_db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    if not _initialized:
        _init_schema(conn)
        _initialized = True
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    sql = _SCHEMA.read_text()
    conn.executescript(sql)
    conn.commit()


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
