from .sources import jikan, thesportsdb, tmdb

ROUTES = {
    "jikan": {
        "anime": jikan.search_anime,
        "manga": jikan.search_manga,
        "manhwa": lambda q, n: jikan.search_manga(q, n),
        "hentai": jikan.search_hentai,
    },
    "tmdb": {
        "movie": lambda q, n: tmdb.search(q, "movie", n),
        "drama": lambda q, n: tmdb.search(q, "drama", n),
        "webseries": lambda q, n: tmdb.search(q, "webseries", n),
    },
    "thesportsdb": {
        "sports": thesportsdb.search,
    },
}

_KEYLESS = {"jikan", "thesportsdb"}

def options():
    out = []
    for source, types in ROUTES.items():
        ready = source in _KEYLESS or tmdb.enabled()
        for t in types:
            out.append({"source": source, "type": t, "ready": ready})
    return out

def fetch(source: str, type_: str, query: str, limit: int = 12):
    fn = ROUTES.get(source, {}).get(type_)
    if not fn:
        raise ValueError(f"No importer for source={source} type={type_}")
    return fn(query, limit)
