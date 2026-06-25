from .config import SAFE_MODE
from .db import db, row_to_item

def _adult_filter(show_adult: bool):
    if SAFE_MODE or not show_adult:
        return "is_adult = 0", []
    return "1=1", []

def _query(where, params, order, limit, show_adult):
    gate_sql, gate_params = _adult_filter(show_adult)
    sql = f"SELECT * FROM media_item WHERE ({where}) AND {gate_sql} ORDER BY {order} LIMIT ?"
    with db() as conn:
        rows = conn.execute(sql, [*params, *gate_params, limit]).fetchall()
    return [row_to_item(r) for r in rows]

def top_all_time(limit=10, show_adult=False, type_=None):
    where, params = ("type = ?", [type_]) if type_ else ("1=1", [])
    return _query(where, params, "score DESC, members DESC", limit, show_adult)

def trending_week(limit=10, show_adult=False, type_=None):
    where, params = ("type = ?", [type_]) if type_ else ("1=1", [])
    return _query(where, params, "trend_week DESC", limit, show_adult)

def trending_month(limit=10, show_adult=False, type_=None):
    where, params = ("type = ?", [type_]) if type_ else ("1=1", [])
    return _query(where, params, "trend_month DESC", limit, show_adult)

def top_airing(limit=10, show_adult=False):
    return _query("air_status = 'airing'", [], "score DESC", limit, show_adult)

def top_upcoming(limit=10, show_adult=False):
    return _query("air_status = 'upcoming'", [], "members DESC", limit, show_adult)

def newest(limit=10, show_adult=False, type_=None):
    where, params = ("type = ?", [type_]) if type_ else ("1=1", [])
    return _query(where, params, "year DESC, id DESC", limit, show_adult)

def oldest(limit=10, show_adult=False, type_=None):
    where, params = ("year IS NOT NULL AND type = ?", [type_]) if type_ else ("year IS NOT NULL", [])
    return _query(where, params, "year ASC", limit, show_adult)

def seasonal(season, limit=12, show_adult=False):
    return _query("season = ?", [season], "members DESC", limit, show_adult)

def by_type(type_, limit=24, show_adult=False, order="score DESC"):
    return _query("type = ?", [type_], order, limit, show_adult)

def browse_page(type_, page=1, per_page=30, show_adult=False,
                order="score DESC, members DESC", tag=None):
    conds, params, join = [], [], ""
    if tag:
        join = "JOIN media_tag t ON t.media_item_id = m.id"
        conds.append("t.tag = ?")
        params.append(tag)
    if type_ and type_ != "all":
        conds.append("m.type = ?")
        params.append(type_)
    if SAFE_MODE or not show_adult:
        conds.append("m.is_adult = 0")
    where = " AND ".join(conds) if conds else "1=1"
    page = max(1, page)
    offset = (page - 1) * per_page
    with db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM media_item m {join} WHERE {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT m.* FROM media_item m {join} WHERE {where} "
            f"ORDER BY {order} LIMIT ? OFFSET ?",
            [*params, per_page, offset]).fetchall()
    items = [row_to_item(r) for r in rows]
    total_pages = max(1, -(-total // per_page))
    return items, total, total_pages

def categories_for(type_, show_adult=False, limit=120):
    conds, params = [], []
    if type_ and type_ != "all":
        conds.append("m.type = ?")
        params.append(type_)
    if SAFE_MODE or not show_adult:
        conds.append("m.is_adult = 0")
    where = " AND ".join(conds) if conds else "1=1"
    with db() as conn:
        rows = conn.execute(
            f"SELECT t.tag, COUNT(*) n FROM media_tag t "
            f"JOIN media_item m ON m.id = t.media_item_id "
            f"WHERE {where} GROUP BY t.tag ORDER BY n DESC LIMIT ?",
            [*params, limit]).fetchall()
    return [(r["tag"], r["n"]) for r in rows]

def search(term, limit=30, show_adult=False):
    return _query("title LIKE ?", [f"%{term}%"], "members DESC", limit, show_adult)

def get_item(item_id, show_adult=False):
    gate_sql, gate_params = _adult_filter(show_adult)
    with db() as conn:
        row = conn.execute(
            f"SELECT * FROM media_item WHERE id = ? AND {gate_sql}",
            [item_id, *gate_params],
        ).fetchone()
        item = row_to_item(row)
        if not item:
            return None
        item["cast"] = conn.execute(
            """SELECT p.name, p.image_url, mc.role
                 FROM media_cast mc JOIN person p ON p.id = mc.person_id
                WHERE mc.media_item_id = ?""",
            [item_id],
        ).fetchall()
        item["reviews"] = conn.execute(
            "SELECT * FROM review WHERE media_item_id = ? ORDER BY created_at DESC",
            [item_id],
        ).fetchall()
        item["genres"] = [r["tag"] for r in conn.execute(
            "SELECT tag FROM media_tag WHERE media_item_id = ? ORDER BY tag", [item_id])]
    return item

def latest_season_label():
    with db() as conn:
        row = conn.execute(
            "SELECT season FROM media_item WHERE season IS NOT NULL "
            "ORDER BY year DESC, id DESC LIMIT 1"
        ).fetchone()
    return row["season"] if row else None
