import sys

from . import store
from .db import init_db
from .sources import tmdb


def _p(label, page, total):
    print(f"{label}: page {page}, {total} fetched", flush=True)


def run(movies=100, dramas=100, webseries=100):
    init_db()
    if not tmdb.enabled():
        print("No TMDB key found in .env. Add TMDB_API_KEY and try again.")
        return
    total = 0

    def imp(label, items):
        nonlocal total
        if not items:
            print(f"Got nothing for {label}.")
            return
        res = store.import_many(items)
        total += len(items)
        print(f"{label}: added {res['created']} new and updated {res['updated']} "
              f"(out of {len(items)} fetched)", flush=True)

    imp("movies", tmdb.popular_movies(movies, _p))
    imp("dramas", tmdb.popular_dramas(dramas, _p))
    imp("webseries", tmdb.popular_webseries(webseries, _p))
    print(f"\nAll done. {total} items fetched and stored.", flush=True)
    return total


if __name__ == "__main__":
    nums = [int(a) for a in sys.argv[1:] if a.isdigit()]
    run(*nums) if nums else run()
