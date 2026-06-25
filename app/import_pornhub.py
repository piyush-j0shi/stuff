import os
import re
import sys

from .db import db, init_db

DEFAULT_FILE = os.environ.get(
    "PORNHUB_DUMP", "/home/boiledpotato/Downloads/pornhub.com-db.csv")
JOB = "pornhub_dump"
FLUSH = 2000

EXCLUDE_TOKENS = {"gay", "solo male", "male masturbation", "male-masturbation"}
KEEP_TOKENS = {"lesbian", "solo female"}

def token_set(tag_str, cat_str):
    blob = (tag_str + ";" + cat_str).lower()
    return {t.strip() for t in blob.replace(",", ";").split(";") if t.strip()}

def excluded(tag_str, cat_str):
    tokens = token_set(tag_str, cat_str)
    if tokens & KEEP_TOKENS:
        return False
    return bool(tokens & EXCLUDE_TOKENS)

def category_tags(cat_str):
    cats = {c.strip().lower() for c in cat_str.split(";") if c.strip()}
    return sorted(cats - EXCLUDE_TOKENS)

IFRAME_SRC = re.compile(rb'src="([^"]+)"')
VIEWKEY = re.compile(r"/embed/([A-Za-z0-9]+)")

INSERT = """INSERT OR IGNORE INTO media_item
    (type, title, image_url, synopsis, units_total, score, members,
     source, source_id, where_to_watch, extra_json, is_adult)
    VALUES ('adultvideo', :title, :image_url, :synopsis, :units, :score,
            :members, 'pornhub_dump', :sid, '[]', :extra, 1)"""

def checkpoint():
    with db() as c:
        r = c.execute("SELECT last_page, done, items FROM sync_state WHERE job=?",
                      (JOB,)).fetchone()
    return (r["last_page"], r["done"], r["items"]) if r else (0, 0, 0)

def save(offset, done, items):
    with db() as c:
        c.execute(
            "INSERT INTO sync_state(job,last_page,done,items,updated_at) "
            "VALUES (?,?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(job) DO UPDATE SET "
            "last_page=excluded.last_page, done=excluded.done, "
            "items=excluded.items, updated_at=CURRENT_TIMESTAMP",
            (JOB, offset, done, items))

def parse(raw):
    parts = raw.rstrip(b"\n").split(b"|")
    if len(parts) < 4:
        return None
    m = IFRAME_SRC.search(parts[0])
    embed = m.group(1).decode("utf-8", "replace") if m else ""
    thumb = parts[1].decode("utf-8", "replace").strip() if len(parts) > 1 else ""
    title = parts[3].decode("utf-8", "replace").strip() if len(parts) > 3 else ""
    if not embed and not thumb:
        return None
    raw_tags = parts[4].decode("utf-8", "replace") if len(parts) > 4 else ""
    raw_cats = parts[5].decode("utf-8", "replace") if len(parts) > 5 else ""
    if excluded(raw_tags, raw_cats):
        return None

    vk = VIEWKEY.search(embed)
    sid = vk.group(1) if vk else (embed or title)[:120]

    tags = raw_tags.replace(";", ", ")
    duration = to_int(parts[7]) if len(parts) > 7 else 0
    views = to_int(parts[8]) if len(parts) > 8 else 0
    up = to_int(parts[9]) if len(parts) > 9 else 0
    down = to_int(parts[10]) if len(parts) > 10 else 0
    score = round(up / (up + down) * 10, 2) if (up + down) else 0

    return {
        "title": (title or "Untitled clip")[:200],
        "image_url": thumb or None,
        "synopsis": ("Tags: " + tags) if tags else None,
        "units": duration,
        "score": score,
        "members": views,
        "sid": sid,
        "extra": '{"embed_url": "%s"}' % embed if embed else "{}",
        "cats": category_tags(raw_cats),
    }

def to_int(b):
    s = b.decode("ascii", "replace").strip()
    return int(s) if s.isdigit() else 0

def write_tags(conn, batch):
    sids = [r["sid"] for r in batch if r.get("cats")]
    if not sids:
        return
    id_by_sid = {}
    for i in range(0, len(sids), 500):
        chunk = sids[i:i + 500]
        ph = ",".join("?" * len(chunk))
        for row in conn.execute(
                f"SELECT id, source_id FROM media_item "
                f"WHERE source='pornhub_dump' AND source_id IN ({ph})", chunk):
            id_by_sid[row["source_id"]] = row["id"]
    pairs = [(id_by_sid[r["sid"]], tag) for r in batch
             if r["sid"] in id_by_sid for tag in r.get("cats", [])]
    if pairs:
        conn.executemany("INSERT OR IGNORE INTO media_tag(media_item_id, tag) VALUES (?,?)", pairs)

def purge_excluded():
    where = ("source='pornhub_dump' AND lower(synopsis) LIKE '%gay%' "
             "AND lower(synopsis) NOT LIKE '%lesbian%'")
    with db() as c:
        n = c.execute(f"SELECT COUNT(*) FROM media_item WHERE {where}").fetchone()[0]
        c.execute(f"DELETE FROM media_item WHERE {where}")
    print(f"Removed {n:,} excluded rows and kept the lesbian ones.")

def status():
    off, done, items = checkpoint()
    size = os.path.getsize(DEFAULT_FILE) if os.path.isfile(DEFAULT_FILE) else 0
    pct = (off / size * 100) if size else 0
    print(f"Imported {items:,} rows so far, about {pct:.2f}% through the file. "
          f"{'Finished.' if done else 'Not finished yet.'}")

def run(count=5000, path=None, reset=False):
    path = path or DEFAULT_FILE
    if not os.path.isfile(path):
        print(f"File not found: {path}")
        return
    init_db()
    offset, done, total = checkpoint()
    if reset:
        offset, total = 0, 0
    if done and not reset:
        print(f"The whole file is already imported ({total:,} rows). "
              f"Pass --reset to start over.")
        return

    imported = 0
    batch = []
    size = os.path.getsize(path)
    with db() as conn, open(path, "rb") as f:
        f.seek(offset)
        while imported < count:
            raw = f.readline()
            if not raw:
                done = 1
                break
            offset = f.tell()
            row = parse(raw)
            if row:
                batch.append(row)
                imported += 1
            if len(batch) >= FLUSH:
                conn.executemany(INSERT, batch)
                write_tags(conn, batch)
                conn.commit()
                batch = []
                print(f"{imported:,} of {count:,} done this run "
                      f"({offset/size*100:.2f}% through the file)", flush=True)
        if batch:
            conn.executemany(INSERT, batch)
            write_tags(conn, batch)
            conn.commit()

    total += imported
    save(offset, done, total)
    print(f"Imported {imported:,} this run, {total:,} in total. "
          f"{'That was the whole file.' if done else 'Run it again to keep going.'}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--status" in args:
        status()
        sys.exit()
    if "--purge" in args:
        purge_excluded()
        sys.exit()
    reset = "--reset" in args
    path = None
    if "--file" in args:
        path = args[args.index("--file") + 1]
    nums = [int(a) for a in args if a.isdigit()]
    if nums:
        count = nums[0]
    else:
        try:
            raw = input("How many rows should I import this run? ").strip()
        except EOFError:
            raw = ""
        count = int(raw) if raw.lstrip("-").isdigit() else 5000
    if count <= 0:
        print("Nothing to import.")
    else:
        run(count, path=path, reset=reset)
