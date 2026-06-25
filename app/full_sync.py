import sys

from . import store
from .db import db, init_db
from .sources import jikan

JOBS = {
    "anime": ("anime", {"order_by": "mal_id", "sort": "asc"}, jikan.map_full_anime),
    "manga": ("manga", {"order_by": "mal_id", "sort": "asc"}, jikan.map_full_manga),
    "manhwa": ("manga", {"type": "manhwa", "order_by": "mal_id", "sort": "asc"},
               jikan.map_full_manhwa),
}

def checkpoint(job):
    with db() as c:
        r = c.execute("SELECT last_page, done, items FROM sync_state WHERE job = ?",
                      (job,)).fetchone()
    return (r["last_page"], r["done"], r["items"]) if r else (0, 0, 0)

def save(job, page, done, items):
    with db() as c:
        c.execute(
            "INSERT INTO sync_state(job, last_page, done, items, updated_at) "
            "VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(job) DO UPDATE SET last_page=excluded.last_page, "
            "done=excluded.done, items=excluded.items, updated_at=CURRENT_TIMESTAMP",
            (job, page, done, items))

def sync(job, restart=False):
    path, params, mapper = JOBS[job]
    last, done, total = checkpoint(job)
    if done and not restart:
        print(f"{job} is already complete with {total} items. "
              f"Pass --restart to pull it again.", flush=True)
        return
    if restart:
        last, total = 0, 0
    start = last + 1
    print(f"Picking up {job} from page {start}, {total} items so far.", flush=True)

    page = last
    for page, data, has_next in jikan.walk(path, params, start):
        if data:
            store.import_many([mapper(d) for d in data])
            total += len(data)
        save(job, page, 0 if has_next else 1, total)
        if page % 10 == 0 or not has_next:
            print(f"{job}: page {page}, {total} items so far", flush=True)
    print(f"Finished {job} with {total} items.", flush=True)

def run(jobs=None, restart=False):
    init_db()
    for job in (jobs or list(JOBS)):
        if job in JOBS:
            sync(job, restart=restart)

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--restart"]
    run(args or None, restart="--restart" in sys.argv)
