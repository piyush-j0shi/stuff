import json

from .db import db

def upsert_item(d: dict):
    fields = {
        "type": d["type"],
        "title": d["title"],
        "image_url": d.get("image_url"),
        "banner_url": d.get("banner_url"),
        "synopsis": d.get("synopsis"),
        "year": d.get("year"),
        "season": d.get("season"),
        "air_status": d.get("air_status"),
        "units_total": d.get("units_total") or 0,
        "score": d.get("score") or 0,
        "members": d.get("members") or 0,
        "trend_week": d.get("trend_week") or 0,
        "trend_month": d.get("trend_month") or 0,
        "source": d.get("source", "manual"),
        "source_id": d.get("source_id"),
        "where_to_watch": json.dumps(d.get("where_to_watch", [])),
        "extra_json": json.dumps(d.get("extra", {})),
        "is_adult": 1 if d.get("is_adult") else 0,
    }

    genres = [g.strip().lower() for g in (d.get("genres") or []) if g and g.strip()]

    with db() as conn:
        existing = None
        if fields["source_id"]:
            existing = conn.execute(
                "SELECT id FROM media_item WHERE source = ? AND source_id = ?",
                (fields["source"], fields["source_id"]),
            ).fetchone()

        if existing:
            sets = ", ".join(f"{k} = :{k}" for k in fields)
            conn.execute(f"UPDATE media_item SET {sets} WHERE id = :id",
                         {**fields, "id": existing["id"]})
            item_id, created = existing["id"], False
        else:
            cols = ", ".join(fields)
            ph = ", ".join(f":{k}" for k in fields)
            cur = conn.execute(f"INSERT INTO media_item ({cols}) VALUES ({ph})", fields)
            item_id, created = cur.lastrowid, True

        if genres:
            conn.executemany(
                "INSERT OR IGNORE INTO media_tag(media_item_id, tag) VALUES (?, ?)",
                [(item_id, g) for g in genres])
        return item_id, created

def import_many(items: list[dict]):
    created = updated = 0
    ids = []
    for it in items:
        _id, was_new = upsert_item(it)
        ids.append(_id)
        created += was_new
        updated += not was_new
    return {"created": created, "updated": updated, "ids": ids}
