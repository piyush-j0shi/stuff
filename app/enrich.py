import json

from .db import db
from .sources import jikan, tmdb


def store(item_id, data):
    director = data.get("director")
    cast = data.get("cast") or []
    with db() as conn:
        for name, role in cast:
            if not name:
                continue
            conn.execute("INSERT OR IGNORE INTO person(name) VALUES (?)", (name,))
            pid = conn.execute("SELECT id FROM person WHERE name = ?", (name,)).fetchone()[0]
            conn.execute(
                "INSERT OR IGNORE INTO media_cast(media_item_id, person_id, role) VALUES (?,?,?)",
                (item_id, pid, role))
        row = conn.execute("SELECT extra_json FROM media_item WHERE id = ?", (item_id,)).fetchone()
        extra = json.loads(row["extra_json"] or "{}")
        extra["enriched"] = 1
        if director:
            extra["director"] = director
        conn.execute("UPDATE media_item SET extra_json = ? WHERE id = ?",
                     (json.dumps(extra), item_id))


def enrich(item):
    if item.get("extra", {}).get("enriched"):
        return
    src, type_, sid = item.get("source"), item.get("type"), item.get("source_id")
    if not sid:
        return
    data = None
    try:
        if src == "tmdb":
            data = tmdb.credits(type_, sid)
        elif type_ in ("anime", "hentai"):
            data = jikan.anime_credits(sid)
        elif type_ in ("manga", "manhwa"):
            data = jikan.manga_credits(sid)
    except Exception:
        data = None
    if data is not None:
        store(item["id"], data)
