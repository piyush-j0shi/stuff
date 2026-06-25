import os

import httpx

KEY = os.environ.get("THESPORTSDB_KEY", "3")
BASE = f"https://www.thesportsdb.com/api/v1/json/{KEY}"

def _map_event(d):
    date = d.get("dateEvent") or ""
    return {
        "type": "sports",
        "title": d.get("strEvent") or d.get("strEventAlternate"),
        "image_url": d.get("strThumb") or d.get("strPoster") or d.get("strSquare"),
        "synopsis": d.get("strDescriptionEN") or
                    f"{d.get('strLeague','')} — {d.get('strSeason','')}".strip(" —"),
        "year": int(date[:4]) if date[:4].isdigit() else None,
        "season": d.get("strSeason"),
        "air_status": "finished",
        "score": 0, "members": 0,
        "source": "thesportsdb", "source_id": d.get("idEvent"),
        "is_adult": 0,
    }

def _map_team(d):
    return {
        "type": "sports",
        "title": d.get("strTeam"),
        "image_url": d.get("strBadge") or d.get("strLogo") or d.get("strFanart1"),
        "synopsis": d.get("strDescriptionEN") or
                    f"{d.get('strLeague','')} · {d.get('strStadium','')}".strip(" ·"),
        "year": int(d["intFormedYear"]) if (d.get("intFormedYear") or "").isdigit() else None,
        "air_status": "airing",
        "score": 0, "members": 0,
        "source": "thesportsdb", "source_id": "team-" + str(d.get("idTeam")),
        "is_adult": 0,
    }

def search(term, limit=12):
    with httpx.Client(timeout=15) as c:
        ev = c.get(f"{BASE}/searchevents.php", params={"e": term})
        events = (ev.json().get("event") or []) if ev.status_code == 200 else []
        if events:
            return [_map_event(d) for d in events[:limit]]
        tm = c.get(f"{BASE}/searchteams.php", params={"t": term})
        teams = (tm.json().get("teams") or []) if tm.status_code == 200 else []
        return [_map_team(d) for d in teams[:limit]]

POPULAR_LEAGUES = {
    "4328": "English Premier League", "4335": "Spanish La Liga",
    "4331": "German Bundesliga", "4332": "Italian Serie A",
    "4334": "French Ligue 1", "4480": "UEFA Champions League",
    "4387": "NBA", "4391": "NFL", "4380": "NHL", "4424": "MLB",
    "4346": "MLS", "4337": "Dutch Eredivisie",
}

def all_teams(leagues=None, on_progress=None):
    leagues = leagues or list(POPULAR_LEAGUES)
    out = []
    with httpx.Client(timeout=25) as c:
        for lid in leagues:
            try:
                r = c.get(f"{BASE}/lookup_all_teams.php", params={"id": lid})
                teams = (r.json().get("teams") or []) if r.status_code == 200 else []
            except Exception:
                continue
            out += [_map_team(d) for d in teams]
            if on_progress:
                on_progress("sports", lid, len(out))
    return out
