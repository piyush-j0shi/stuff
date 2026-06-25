import threading

from . import store
from .sources import jikan, thesportsdb, tmdb

STATUS = {"running": False, "lines": [], "done": False}


def _log(msg):
    STATUS["lines"].append(msg)
    STATUS["lines"] = STATUS["lines"][-50:]


def _run(counts):
    STATUS.update(running=True, done=False, lines=[])
    jobs = [
        ("anime", counts.get("anime", 0), jikan.top_anime),
        ("manga", counts.get("manga", 0), jikan.top_manga),
        ("manhwa", counts.get("manhwa", 0), jikan.top_manhwa),
        ("hentai", counts.get("hentai", 0), jikan.top_hentai),
        ("movies", counts.get("movies", 0), tmdb.popular_movies),
        ("dramas", counts.get("dramas", 0), tmdb.popular_dramas),
        ("webseries", counts.get("webseries", 0), tmdb.popular_webseries),
    ]
    try:
        for label, pages, fn in jobs:
            if pages and pages > 0:
                _log(f"{label}: pulling {pages} pages...")
                items = fn(pages)
                res = store.import_many(items)
                _log(f"{label}: +{res['created']} new, {res['updated']} updated "
                     f"({len(items)} fetched)")
        if counts.get("sports", 0):
            _log("sports: pulling major leagues...")
            items = thesportsdb.all_teams()
            res = store.import_many(items)
            _log(f"sports: +{res['created']} new, {res['updated']} updated ({len(items)})")
        _log("Done.")
    except Exception as e:
        _log(f"Error: {e}")
    finally:
        STATUS.update(running=False, done=True)


def start(counts):
    if STATUS["running"]:
        return False
    threading.Thread(target=_run, args=(counts,), daemon=True).start()
    return True
