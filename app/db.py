import json
import sqlite3
from contextlib import contextmanager

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS media_item (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    type         TEXT NOT NULL,              -- anime, movie, manga, ... (see config.CATEGORIES)
    title        TEXT NOT NULL,
    image_url    TEXT,
    banner_url   TEXT,
    synopsis     TEXT,
    year         INTEGER,
    season       TEXT,                       -- 'Winter 2026', etc. (nullable)
    air_status   TEXT,                       -- airing | finished | upcoming
    units_total  INTEGER,                    -- total eps / chapters / minutes
    score        REAL DEFAULT 0,
    members      INTEGER DEFAULT 0,
    trend_week   INTEGER DEFAULT 0,          -- popularity points this week
    trend_month  INTEGER DEFAULT 0,          -- popularity points this month
    source       TEXT,                       -- 'seed' | 'tmdb' | 'jikan' | 'manual'
    source_id    TEXT,
    where_to_watch TEXT,                     -- JSON list of {name, url}
    extra_json   TEXT,                       -- JSON dict, type-specific fields
    is_adult     INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, source_id)
);

CREATE TABLE IF NOT EXISTS person (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL UNIQUE,
    image_url TEXT
);

CREATE TABLE IF NOT EXISTS media_cast (
    media_item_id INTEGER NOT NULL REFERENCES media_item(id) ON DELETE CASCADE,
    person_id     INTEGER NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    role          TEXT,                      -- character / position
    PRIMARY KEY (media_item_id, person_id, role)
);

CREATE TABLE IF NOT EXISTS user (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    email         TEXT,
    password_hash TEXT NOT NULL,
    adult_enabled INTEGER DEFAULT 0,
    is_admin      INTEGER DEFAULT 0,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS list_entry (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
    media_item_id INTEGER NOT NULL REFERENCES media_item(id) ON DELETE CASCADE,
    status        TEXT NOT NULL,             -- watching|completed|plan|on_hold|dropped
    score         INTEGER,
    progress      INTEGER DEFAULT 0,
    notes         TEXT,
    updated_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, media_item_id)
);

CREATE TABLE IF NOT EXISTS review (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    media_item_id INTEGER NOT NULL REFERENCES media_item(id) ON DELETE CASCADE,
    author        TEXT NOT NULL,
    rating        INTEGER,
    body          TEXT,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS media_tag (
    media_item_id INTEGER NOT NULL REFERENCES media_item(id) ON DELETE CASCADE,
    tag           TEXT NOT NULL,
    PRIMARY KEY (media_item_id, tag)
);
CREATE INDEX IF NOT EXISTS idx_tag ON media_tag(tag);

CREATE TABLE IF NOT EXISTS sync_state (
    job        TEXT PRIMARY KEY,
    last_page  INTEGER DEFAULT 0,
    done       INTEGER DEFAULT 0,
    items      INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_media_type  ON media_item(type);
CREATE INDEX IF NOT EXISTS idx_media_score ON media_item(score);
"""

def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

@contextmanager
def db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def _ensure_column(conn, table, column, decl):
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")

def init_db():
    with db() as conn:
        conn.executescript(SCHEMA)
        _ensure_column(conn, "user", "email", "TEXT")
        _ensure_column(conn, "user", "is_admin", "INTEGER DEFAULT 0")

def row_to_item(row):
    if row is None:
        return None
    d = dict(row)
    d["where_to_watch"] = json.loads(d.get("where_to_watch") or "[]")
    d["extra"] = json.loads(d.get("extra_json") or "{}")
    return d
