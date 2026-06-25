import time

import httpx

from ..config import TMDB_API_KEY

BASE = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p/w500"
BACKDROP = "https://image.tmdb.org/t/p/w780"

_GENRE_CACHE = {}


def _genre_names(kind):
    if _GENRE_CACHE.get(kind):
        return _GENRE_CACHE[kind]
    out = {}
    if enabled():
        with httpx.Client(timeout=15) as c:
            r = _get(c, f"{BASE}/genre/{kind}/list", {"api_key": TMDB_API_KEY})
        if r is not None and r.status_code == 200:
            for g in r.json().get("genres", []):
                out[g["id"]] = g["name"]
    if out:
        _GENRE_CACHE[kind] = out
    return out


def _get(client, url, params, tries=4):
    for attempt in range(tries):
        try:
            r = client.get(url, params=params)
            if r.status_code == 429:
                time.sleep(2)
                continue
            return r
        except httpx.HTTPError:
            time.sleep(1.5 * (attempt + 1))
    return None

def enabled() -> bool:
    return bool(TMDB_API_KEY)

def _map(d, type_):
    title = d.get("title") or d.get("name")
    date = d.get("release_date") or d.get("first_air_date") or ""
    kind = "movie" if type_ == "movie" else "tv"
    gmap = _genre_names(kind)
    genres = [gmap[i] for i in (d.get("genre_ids") or []) if i in gmap]
    extra = {
        "original_title": d.get("original_title") or d.get("original_name"),
        "language": d.get("original_language"),
        "popularity": d.get("popularity"),
        "release_date": date or None,
        "origin_country": ", ".join(d.get("origin_country") or []) or None,
        "adult_flag": d.get("adult"),
    }
    return {
        "type": type_,
        "title": title,
        "image_url": IMG + d["poster_path"] if d.get("poster_path") else None,
        "banner_url": BACKDROP + d["backdrop_path"] if d.get("backdrop_path") else None,
        "synopsis": d.get("overview"),
        "year": int(date[:4]) if date[:4].isdigit() else None,
        "score": round((d.get("vote_average") or 0), 2),
        "members": d.get("vote_count") or 0,
        "source": "tmdb",
        "source_id": str(d.get("id")),
        "is_adult": 0,
        "genres": genres,
        "extra": {k: v for k, v in extra.items() if v not in (None, "", [])},
    }

def search(term, type_="movie", limit=10):
    if not enabled():
        return []
    kind = "movie" if type_ == "movie" else "tv"
    with httpx.Client(timeout=15) as c:
        r = c.get(f"{BASE}/search/{kind}",
                  params={"api_key": TMDB_API_KEY, "query": term})
        r.raise_for_status()
        return [_map(d, type_) for d in r.json().get("results", [])[:limit]]

def _discover(kind, type_, pages, extra=None, on_progress=None):
    if not enabled():
        return []
    out = []
    with httpx.Client(timeout=25) as c:
        for p in range(1, pages + 1):
            params = {"api_key": TMDB_API_KEY, "page": p, "sort_by": "popularity.desc",
                      "include_adult": "false"}
            if extra:
                params.update(extra)
            r = _get(c, f"{BASE}/discover/{kind}", params)
            if r is None or r.status_code != 200:
                continue
            res = r.json().get("results", [])
            if not res:
                break
            out += [_map(d, type_) for d in res]
            if on_progress and p % 10 == 0:
                on_progress(type_, p, len(out))
            time.sleep(0.05)
    return out

def credits(type_, sid, limit=15):
    if not enabled():
        return {"cast": [], "director": None}
    kind = "movie" if type_ == "movie" else "tv"
    with httpx.Client(timeout=15) as c:
        r = _get(c, f"{BASE}/{kind}/{sid}/credits", {"api_key": TMDB_API_KEY})
    if r is None or r.status_code != 200:
        return {"cast": [], "director": None}
    j = r.json()
    cast = [(p.get("name"), p.get("character") or "")
            for p in (j.get("cast") or [])[:limit] if p.get("name")]
    director = None
    for p in (j.get("crew") or []):
        if p.get("job") == "Director":
            director = p.get("name")
            break
    return {"cast": cast, "director": director}

def popular_movies(pages=5, on_progress=None):
    return _discover("movie", "movie", pages, on_progress=on_progress)

def popular_webseries(pages=5, on_progress=None):
    return _discover("tv", "webseries", pages, on_progress=on_progress)

def popular_dramas(pages=5, on_progress=None):
    return _discover("tv", "drama", pages, {"with_original_language": "ko"}, on_progress)
