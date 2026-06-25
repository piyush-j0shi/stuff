import sys

from . import store
from .db import init_db
from .sources import jikan, thesportsdb, tmdb


def _ask(label, default=0):
    try:
        raw = input(f"{label}: ").strip()
    except EOFError:
        return default
    if not raw:
        return default
    return int(raw) if raw.lstrip("-").isdigit() else default


def _imp(label, items):
    if not items:
        print(f"Got nothing for {label}.")
        return 0
    res = store.import_many(items)
    print(f"{label}: added {res['created']} new and updated {res['updated']} "
          f"(out of {len(items)} fetched)", flush=True)
    return len(items)


def run(counts):
    init_db()
    total = 0
    jobs = [
        ("anime", jikan.top_anime), ("manga", jikan.top_manga),
        ("manhwa", jikan.top_manhwa), ("hentai", jikan.top_hentai),
        ("movies", tmdb.popular_movies), ("dramas", tmdb.popular_dramas),
        ("webseries", tmdb.popular_webseries),
    ]
    for key, fn in jobs:
        n = counts.get(key, 0)
        if n and n > 0:
            print(f"\nPulling {n} pages of {key}...", flush=True)
            total += _imp(key, fn(n))
    if counts.get("sports"):
        print("\nPulling sports teams from the major leagues...", flush=True)
        total += _imp("sports", thesportsdb.all_teams())
    print(f"\nAll done. {total} items fetched and stored.")


def prompt():
    print("How many pages should I pull for each category?")
    print("Each page is about 20 to 25 items. Enter 0 (or just press enter) to skip one.\n")
    counts = {
        "anime": _ask("Anime pages"),
        "manga": _ask("Manga pages"),
        "manhwa": _ask("Manhwa pages"),
        "hentai": _ask("Hentai pages"),
        "movies": _ask("Movies pages"),
        "dramas": _ask("Dramas pages"),
        "webseries": _ask("Web Series pages"),
        "sports": _ask("Sports (1 = pull, 0 = skip)"),
    }
    if not any(counts.values()):
        print("Nothing selected. Exiting.")
        return
    run(counts)


if __name__ == "__main__":
    try:
        prompt()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        sys.exit(1)
