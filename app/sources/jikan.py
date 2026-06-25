import time

import httpx

BASE = "https://api.jikan.moe/v4"
PAGE_DELAY = 1.0

def names(d, key):
    return [g.get("name") for g in (d.get(key) or []) if g.get("name")]

def map_anime(d, type_="anime"):
    genres = names(d, "genres") + names(d, "themes") + names(d, "demographics")
    extra = {
        "subtype": d.get("type"),
        "rating": d.get("rating"),
        "origin": d.get("source"),
        "studios": ", ".join(names(d, "studios")) or None,
        "authors": ", ".join(names(d, "authors")) or None,
        "demographics": ", ".join(names(d, "demographics")) or None,
        "chapters": d.get("chapters"),
        "volumes": d.get("volumes"),
        "duration": d.get("duration"),
        "aired": (d.get("aired") or {}).get("string"),
        "published": (d.get("published") or {}).get("string"),
        "trailer": (d.get("trailer") or {}).get("url"),
        "mal_url": d.get("url"),
    }
    return {
        "type": type_,
        "title": d.get("title"),
        "image_url": (d.get("images", {}).get("jpg", {}) or {}).get("large_image_url"),
        "synopsis": d.get("synopsis"),
        "year": d.get("year"),
        "season": (f"{d.get('season','').title()} {d.get('year')}"
                   if d.get("season") and d.get("year") else None),
        "air_status": status(d.get("status")),
        "units_total": d.get("episodes") or d.get("chapters") or 0,
        "score": d.get("score") or 0,
        "members": d.get("members") or 0,
        "source": "jikan",
        "source_id": str(d.get("mal_id")),
        "is_adult": 1 if type_ == "hentai" else 0,
        "genres": genres,
        "extra": {k: v for k, v in extra.items() if v not in (None, "", [])},
    }

def status(s):
    s = (s or "").lower()
    if "airing" in s and "not" not in s:
        return "airing"
    if "not yet" in s or "upcoming" in s:
        return "upcoming"
    return "finished"

def search_anime(term, limit=10, sfw=True):
    params = {"q": term, "limit": limit}
    if sfw:
        params["sfw"] = "true"
    with httpx.Client(timeout=15) as c:
        r = c.get(f"{BASE}/anime", params=params)
        r.raise_for_status()
        return [map_anime(d) for d in r.json().get("data", [])]

def search_manga(term, limit=10):
    with httpx.Client(timeout=15) as c:
        r = c.get(f"{BASE}/manga", params={"q": term, "limit": limit})
        r.raise_for_status()
        return [map_anime(d, type_="manga") for d in r.json().get("data", [])]

def search_hentai(term, limit=10):
    params = {"q": term, "limit": limit, "genres": "12", "sfw": "false", "rating": "rx"}
    with httpx.Client(timeout=15) as c:
        r = c.get(f"{BASE}/anime", params=params)
        r.raise_for_status()
        return [map_anime(d, type_="hentai") for d in r.json().get("data", [])]

def paged(path, params, pages, type_, on_progress=None):
    out = []
    with httpx.Client(timeout=25) as c:
        for p in range(1, pages + 1):
            try:
                r = c.get(f"{BASE}/{path}", params={**params, "page": p})
                if r.status_code == 429:
                    time.sleep(2)
                    r = c.get(f"{BASE}/{path}", params={**params, "page": p})
                if r.status_code != 200:
                    break
                data = r.json().get("data", [])
            except Exception:
                break
            if not data:
                break
            out += [map_anime(d, type_) for d in data]
            if on_progress:
                on_progress(type_, p, len(out))
            time.sleep(PAGE_DELAY)
    return out

def top_anime(pages=5, on_progress=None):
    return paged("top/anime", {}, pages, "anime", on_progress)

def top_manga(pages=5, on_progress=None):
    return paged("top/manga", {}, pages, "manga", on_progress)

def top_hentai(pages=3, on_progress=None):
    params = {"genres": "12", "sfw": "false", "order_by": "members", "sort": "desc"}
    return paged("anime", params, pages, "hentai", on_progress)

def top_manhwa(pages=5, on_progress=None):
    params = {"type": "manhwa", "order_by": "members", "sort": "desc"}
    return paged("manga", params, pages, "manhwa", on_progress)

def anime_credits(sid, limit=15):
    cast, director = [], None
    with httpx.Client(timeout=20) as c:
        try:
            rc = c.get(f"{BASE}/anime/{sid}/characters")
            if rc.status_code == 200:
                for x in (rc.json().get("data") or [])[:limit]:
                    char = (x.get("character") or {}).get("name")
                    vas = x.get("voice_actors") or []
                    va = vas[0]["person"]["name"] if vas else None
                    if char:
                        cast.append((va or char, char))
            time.sleep(0.4)
            rs = c.get(f"{BASE}/anime/{sid}/staff")
            if rs.status_code == 200:
                for x in (rs.json().get("data") or []):
                    if any("Director" in p for p in (x.get("positions") or [])):
                        director = (x.get("person") or {}).get("name")
                        break
        except Exception:
            pass
    return {"cast": cast, "director": director}

def manga_credits(sid, limit=15):
    cast = []
    with httpx.Client(timeout=20) as c:
        try:
            rc = c.get(f"{BASE}/manga/{sid}/characters")
            if rc.status_code == 200:
                for x in (rc.json().get("data") or [])[:limit]:
                    char = (x.get("character") or {}).get("name")
                    if char:
                        cast.append((char, x.get("role") or "Character"))
        except Exception:
            pass
    return {"cast": cast, "director": None}

def is_hentai_anime(d):
    if (d.get("rating") or "").startswith("Rx"):
        return True
    return any(g.get("mal_id") == 12 for g in (d.get("genres") or []))

def has_adult_genre(d):
    return any(g.get("mal_id") == 12 for g in (d.get("genres") or []))

def map_full_anime(d):
    return map_anime(d, "hentai" if is_hentai_anime(d) else "anime")

def map_full_manga(d):
    m = map_anime(d, "manga")
    m["is_adult"] = 1 if has_adult_genre(d) else 0
    return m

def map_full_manhwa(d):
    m = map_anime(d, "manhwa")
    m["is_adult"] = 1 if has_adult_genre(d) else 0
    return m

def walk(path, params, start_page=1, hard_max=100000):
    with httpx.Client(timeout=30) as c:
        page = start_page
        while page <= hard_max:
            try:
                r = c.get(f"{BASE}/{path}", params={**params, "page": page})
            except Exception:
                time.sleep(3)
                continue
            if r.status_code == 429:
                time.sleep(4)
                continue
            if r.status_code != 200:
                break
            j = r.json()
            data = j.get("data", [])
            has_next = bool(j.get("pagination", {}).get("has_next_page"))
            yield page, data, has_next
            if not has_next:
                break
            page += 1
            time.sleep(PAGE_DELAY)
